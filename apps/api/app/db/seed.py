"""Idempotent seed: organization, model configs, the 15 AI employees and their prompts.

Prompts are versioned in `employee_instructions`. Re-running the seed after editing a
prompt file inserts a new version and makes it the active one; unchanged prompts are left
alone. Usage:  DATABASE_URL=postgresql://... python -m app.db.seed
"""
from __future__ import annotations

import os
import sys

import psycopg

from app.employees import registry
from app.employees.prompt_builder import PromptSource
from app.llm.router import DEFAULT_MODELS

ORG_SLUG = "pmr"


def seed(conn: psycopg.Connection, source: PromptSource | None = None) -> dict[str, int]:
    src = source or PromptSource()
    stats = {"employees": 0, "new_prompt_versions": 0}
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            """INSERT INTO organizations (name, slug, country, timezone, base_currency)
               VALUES ('PMR Digital Marketing Agency', %s, 'IN', 'Asia/Kolkata', 'INR')
               ON CONFLICT (slug) DO UPDATE SET updated_at = now() RETURNING id""",
            (ORG_SLUG,),
        )
        org_id = cur.fetchone()[0]

        model_ids = {}
        for tier, cfg in DEFAULT_MODELS.items():
            cur.execute(
                """INSERT INTO ai_model_configs (organization_id, name, provider, model_id, max_output_tokens,
                       input_cost_per_mtok_usd, output_cost_per_mtok_usd)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (organization_id, name) DO UPDATE SET
                       provider = EXCLUDED.provider, model_id = EXCLUDED.model_id,
                       max_output_tokens = EXCLUDED.max_output_tokens,
                       input_cost_per_mtok_usd = EXCLUDED.input_cost_per_mtok_usd,
                       output_cost_per_mtok_usd = EXCLUDED.output_cost_per_mtok_usd
                   RETURNING id""",
                (org_id, tier.value, cfg.provider, cfg.model_id, cfg.max_tokens,
                 cfg.input_cost_per_mtok_usd, cfg.output_cost_per_mtok_usd),
            )
            model_ids[tier] = cur.fetchone()[0]

        emp_ids = {}
        for e in registry.EMPLOYEES:
            cur.execute(
                """INSERT INTO ai_employees (organization_id, code, display_name, designation, department,
                       model_config_id, autonomy_level, tool_scopes, max_concurrent_tasks)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (organization_id, code) DO UPDATE SET
                       display_name = EXCLUDED.display_name, designation = EXCLUDED.designation,
                       department = EXCLUDED.department, model_config_id = EXCLUDED.model_config_id,
                       autonomy_level = EXCLUDED.autonomy_level, tool_scopes = EXCLUDED.tool_scopes,
                       max_concurrent_tasks = EXCLUDED.max_concurrent_tasks
                   RETURNING id""",
                (org_id, e.code, e.display_name, e.designation, e.department, model_ids[e.model_tier],
                 e.autonomy_level, list(e.tool_scopes), e.max_concurrent_tasks),
            )
            emp_ids[e.code] = cur.fetchone()[0]
            stats["employees"] += 1
        for e in registry.EMPLOYEES:
            cur.execute("UPDATE ai_employees SET reports_to_id = %s WHERE id = %s",
                        (emp_ids[e.reports_to] if e.reports_to else None, emp_ids[e.code]))

        base = src.get("base")
        for e in registry.EMPLOYEES:
            for name, content in (("base", base), ("role", src.get(e.code))):
                stats["new_prompt_versions"] += _upsert_prompt(cur, emp_ids[e.code], name, content)
    return stats


def _upsert_prompt(cur, employee_id, name: str, content: str) -> int:
    cur.execute(
        """SELECT content, version FROM employee_instructions
           WHERE employee_id = %s AND kind = 'system_prompt' AND name = %s AND is_active""",
        (employee_id, name),
    )
    row = cur.fetchone()
    if row and row[0] == content:
        return 0
    cur.execute(
        """SELECT coalesce(max(version), 0) + 1 FROM employee_instructions
           WHERE employee_id = %s AND kind = 'system_prompt' AND name = %s""",
        (employee_id, name),
    )
    version = cur.fetchone()[0]
    cur.execute(
        """UPDATE employee_instructions SET is_active = false
           WHERE employee_id = %s AND kind = 'system_prompt' AND name = %s AND is_active""",
        (employee_id, name),
    )
    cur.execute(
        """INSERT INTO employee_instructions (employee_id, kind, name, version, content, is_active)
           VALUES (%s, 'system_prompt', %s, %s, %s, true)""",
        (employee_id, name, version, content),
    )
    return 1


def load_active_prompts(conn: psycopg.Connection, org_slug: str = ORG_SLUG) -> dict[str, str]:
    """Active prompts from the DB, keyed the way PromptSource expects ('base', 'E01'..'E15')."""
    out: dict[str, str] = {}
    with conn.cursor() as cur:
        cur.execute(
            """SELECT e.code, i.name, i.content FROM employee_instructions i
               JOIN ai_employees e ON e.id = i.employee_id
               JOIN organizations o ON o.id = e.organization_id
               WHERE o.slug = %s AND i.kind = 'system_prompt' AND i.is_active""",
            (org_slug,),
        )
        for code, name, content in cur.fetchall():
            if name == "role":
                out[code] = content
            elif name == "base":
                out.setdefault("base", content)
    return out


if __name__ == "__main__":
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("set DATABASE_URL")
    with psycopg.connect(url) as c:
        print(seed(c))
