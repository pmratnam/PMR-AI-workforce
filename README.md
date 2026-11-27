# PMR AI Workforce Platform

An AI digital marketing workforce for PMR Digital Marketing Agency (Hyderabad): an AI Marketing
Manager plans and reviews work done by 14 specialist AI employees, with a human approval gate in front
of anything public, financial or irreversible.

- Design package (Phase 1): [`docs/design/`](docs/design/00-README.md)
- Backend: [`apps/api/`](apps/api/)

## Status

| Phase | State |
|---|---|
| 1 Architecture & design | Done, approved by founder 2026-11-27 |
| 2 AI employees & prompts | In this branch: registry, versioned prompts, prompt assembler, output validation, model router, runner, DB seed |
| 3+ | Not started |

## Running the backend tests

```bash
cd apps/api
pip install "anthropic>=2.14" "pydantic>=2.13" "psycopg[binary]>=3.3" "pytest>=9"
python -m pytest -q                       # database tests skip without TEST_DATABASE_URL
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres python -m pytest -q
```

The database tests need PostgreSQL 16 with the pgvector extension (e.g. `docker run -p 5432:5432
-e POSTGRES_PASSWORD=postgres pgvector/pgvector:pg16`).

## Seeding the 15 employees

```bash
psql "$DATABASE_URL" -f apps/api/migrations/0001_core_schema.sql
cd apps/api && DATABASE_URL=... python -m app.db.seed
```

## Running the employees against Claude (costs API credits)

```bash
cd apps/api && ANTHROPIC_API_KEY=... python -m scripts.eval_employees        # all 15
python -m scripts.eval_employees E02 E04                                       # some
```
