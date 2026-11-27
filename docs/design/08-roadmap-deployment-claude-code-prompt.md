# 08. Development Roadmap · Deployment Instructions · Claude Code Implementation Prompt

## A. Roadmap (module by module)

Durations are planning estimates for one AI-assisted build track, not commitments.

| Phase | Scope | Exit criteria (must be verified, not claimed) | Est. |
|---|---|---|---|
| 1 Architecture & design | This package | Founder sign-off; schema loads on Postgres (done 2026-11-27) | done, pending sign-off |
| 2 Employees & prompts | Seed 15 employees, prompts into `employee_instructions`, prompt loader, output-schema validation | Unit tests: every employee resolves a prompt + schema; golden-task eval per employee (fixture inputs → schema-valid output) | 1 wk |
| 3 Manager & orchestration | LangGraph Manager + employee template graph, model router, task state machine, Redis worker, tool base + gate | Integration test: founder instruction → plan → 3 tasks executed with mock tools → review → gated task lands in approvals | 2 wk |
| 4 Database & backend | Alembic migrations, all routers, RBAC, RLS, audit chain, cost metering | API tests ≥ 80% coverage on services; RLS cross-tenant test fails closed | 2 wk |
| 5 Dashboard & workspaces | Next.js pages from doc 07 | Playwright e2e: login, view board, approve item, view employee workspace | 2 wk |
| 6 Integrations | In order: Slack/Telegram notify → GA4/GSC read → WordPress draft/publish → Gmail drafts → Zoho/HubSpot → Meta/Google Ads (read, create-paused) → ESP → WhatsApp → Shopify → Canva | Each adapter: contract test against sandbox/test account; gated methods proven blocked | 3–4 wk |
| 7 Approval & QA hardening | MFA step-up, standing approvals, QA rubric, revision loop limits | Test: every gated method refuses without approval; payload tamper rejected | 1 wk |
| 8 Testing, security, deployment | Pen-test checklist, backups, monitoring, prod compose | Restore-from-backup drill succeeds; OWASP top-10 checklist | 1 wk |
| 9 Pilot | 1–2 real clients (founder picks), human reviews everything | Founder-reviewed pilot report with actual metrics only | 4 wk |
| 10 Optimise & scale | Prompt tuning from revision data, cost tuning, more employees/clients | Driven by pilot data | ongoing |

**Recommended first build slice (Phase 2+3 thin vertical):** founder types an instruction → Manager plans → E02 SEO audit + E04 content draft run with real Claude calls and mock tools → Manager reviews → publish step appears in approval inbox. This proves the core loop before any integrations.

## B. Deployment instructions (target: single cloud VPS, v1)

**Server:** Ubuntu 24.04 LTS, 4 vCPU / 8 GB RAM / 100 GB SSD (sizing estimate for pilot), region Mumbai/Bangalore for India data residency preference.

```bash
# 1. Harden
adduser deploy && usermod -aG sudo deploy
# SSH keys only; disable password login; ufw allow 22,80,443; enable fail2ban

# 2. Install Docker
curl -fsSL https://get.docker.com | sh && usermod -aG docker deploy

# 3. Get the code
git clone git@github.com:<owner>/pmr-ai-workforce.git && cd pmr-ai-workforce
cp .env.example .env   # fill: DB password, JWT secret, ENCRYPTION_KEY, ANTHROPIC_API_KEY, etc.

# 4. Start
docker compose -f infra/docker-compose.prod.yml up -d --build
docker compose exec api alembic upgrade head
docker compose exec api python -m app.scripts.seed   # org, founder user, 15 employees

# 5. DNS: app.<domain> and n8n.<domain> → server IP; Caddy fetches TLS automatically
# 6. Backups: infra/backup/pg_backup.sh via cron 02:00 IST → encrypted off-site bucket, 30-day retention
# 7. Monitoring: Sentry DSN in .env; uptime check on /api/v1/health
```

`docker-compose.prod.yml` services: `caddy`, `web`, `api`, `worker`, `scheduler`, `postgres` (pgvector/pgvector:pg16 image), `redis`, `minio`, `n8n` (own Postgres DB, basic auth + behind Caddy).

## C. Comprehensive Claude Code implementation prompt

Use this prompt to start each build session (paste the phase you are on):

```
You are building the PMR AI Digital Marketing Workforce Platform. The design package is in
docs/design/ (01–08) and docs/design/sql/. Read 01, 04, 05, 06, 07 before coding. Treat it as the spec;
if the spec is ambiguous, choose the simplest reading, note it in docs/decisions.md, and continue.

STACK: Next.js 14 (App Router, TypeScript, Tailwind, shadcn/ui, TanStack Query) · FastAPI (Python 3.12,
SQLAlchemy 2, Pydantic v2, Alembic) · PostgreSQL 16 + pgvector · Redis 7 + arq · LangGraph ·
Anthropic SDK (default) behind a model router that also supports OpenAI, Gemini, Ollama · n8n · Docker.

CURRENT PHASE: <N — name>. Build only this phase's scope from docs/design/08 section A.

NON-NEGOTIABLES
1. Task status changes only through services/task_state_machine.py, each writing activity_logs.
2. Every tool adapter method declares gated category or None. Gated methods execute only via the
   approval executor with an approved, unexpired approval whose payload hash matches. Write a test
   that enumerates all gated methods and proves they refuse otherwise.
3. Never put secrets in prompts, logs, or the repo. Use .env + encrypted secrets table.
4. Every metric row stores value_type (actual|target|estimate) and source. UI labels them.
5. Every LLM/API call writes usage_costs. Enforce per-org monthly AI budget hard stop.
6. Multi-tenant: every query scoped by organization_id; add RLS policies.
7. Do not report anything as working unless you ran it. For each task finished, show the command
   you ran and its output (tests, lint, type-check, curl against the running API).

WORKFLOW
- Small commits on a feature branch; open a PR per phase with a checklist of exit criteria and
  evidence (test output).
- Tests: pytest (unit + integration with a real Postgres via docker compose), Playwright for web.
- Run `make lint test` before each commit.

DELIVER at the end of the session: what was built, what was verified (with output), what is not done,
and the next step.
```
