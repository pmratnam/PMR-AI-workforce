"""Seeds a real PostgreSQL database. Skipped unless TEST_DATABASE_URL points at a server
where this test may create and drop a scratch database (needs the pgvector extension)."""
import os
import uuid
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")

from app.db import seed as seed_mod  # noqa: E402
from app.employees import prompt_builder  # noqa: E402
from app.employees.prompt_builder import PromptSource  # noqa: E402
from tests.fixtures.golden import GOLDEN  # noqa: E402

ADMIN_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not ADMIN_URL, reason="TEST_DATABASE_URL not set")
SCHEMA = Path(__file__).resolve().parents[1] / "migrations" / "0001_core_schema.sql"


@pytest.fixture()
def conn():
    name = f"pmr_test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{name}"')
    url = psycopg.conninfo.make_conninfo(ADMIN_URL, dbname=name)
    try:
        with psycopg.connect(url) as c:
            c.execute(SCHEMA.read_text())
            c.commit()
            yield c
    finally:
        with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


def count(c, sql):
    return c.execute(sql).fetchone()[0]


def test_seed_creates_workforce(conn):
    stats = seed_mod.seed(conn)
    assert stats == {"employees": 15, "new_prompt_versions": 30}
    assert count(conn, "SELECT count(*) FROM ai_employees") == 15
    assert count(conn, "SELECT count(*) FROM ai_employees WHERE reports_to_id IS NULL") == 1
    assert count(conn, "SELECT count(*) FROM employee_instructions WHERE is_active") == 30
    assert count(conn, "SELECT count(*) FROM ai_model_configs") == 3


def test_seed_is_idempotent(conn):
    seed_mod.seed(conn)
    assert seed_mod.seed(conn)["new_prompt_versions"] == 0
    assert count(conn, "SELECT count(*) FROM employee_instructions") == 30


def test_edited_prompt_becomes_new_active_version(conn):
    seed_mod.seed(conn)
    src = PromptSource()
    edited = PromptSource(overrides={"E02": src.get("E02") + "\nAlways include hreflang checks.\n"})
    assert seed_mod.seed(conn, edited)["new_prompt_versions"] == 1
    rows = conn.execute(
        """SELECT i.version, i.is_active FROM employee_instructions i JOIN ai_employees e ON e.id = i.employee_id
           WHERE e.code = 'E02' AND i.name = 'role' ORDER BY version""").fetchall()
    assert rows == [(1, False), (2, True)]


def test_prompts_from_db_build_same_requests(conn):
    seed_mod.seed(conn)
    db_src = PromptSource(overrides=seed_mod.load_active_prompts(conn))
    for code, task in GOLDEN:
        assert prompt_builder.build(code, task, source=db_src).system == prompt_builder.build(code, task).system
