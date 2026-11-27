# 07. Security & Approval Framework · KPI Framework · Dashboard UI Design

## A. Human approval framework

**Gated categories** (DB enum `approval_category`): publish_content · bulk_email · external_communication · launch_ads · change_ad_budget · purchase · modify_live_site · delete_data · financial_commitment · contractual_commitment.

**How it is enforced (defence in depth)**
1. Prompt rule (base prompt) — the model is told not to execute. *Weakest layer; never relied on alone.*
2. Tool registry — every adapter method declares `gated: ApprovalCategory | None`. Gated methods cannot run from an agent context; they only create an `approvals` row.
3. Executor — only the approval executor (system actor) may run a gated method, and only when `approvals.status='approved'`, not expired, and `sha256(payload) == payload_hash`.
4. Database — `conversation_messages` outbound requires `approval_id`; `approvals` constraints.
5. Tests — a CI test enumerates all gated adapter methods and asserts each refuses to run without an approved row.

**Approval card shows:** what will happen (rendered preview), exact target (account/page/URL/recipient list size), money involved, risk summary, requesting employee, linked task & deliverable, Manager review verdict.

**Who can approve**

| Category | founder | admin | manager (human) |
|---|---|---|---|
| publish_content, external_communication | ✓ | ✓ | ✓ |
| bulk_email, modify_live_site | ✓ | ✓ | — |
| launch_ads, change_ad_budget, purchase | ✓ (MFA step-up) | ✓ ≤ per-org limit | — |
| delete_data, financial_commitment, contractual_commitment | ✓ (MFA step-up) | — | — |

Optional L3 "standing approvals": founder can whitelist narrow routines (e.g. "schedule already-approved social posts for client X"), each with expiry and still logged.

## B. Security framework

- **AuthN**: Argon2id password hashing, JWT short-lived access, refresh rotation, TOTP MFA for founder/admin, login rate limiting.
- **AuthZ**: RBAC roles `founder, admin, manager, specialist, client_viewer` + Postgres RLS by `organization_id`; client_viewer limited to own `client_id`.
- **Secrets**: OAuth tokens & API keys encrypted (envelope encryption, key in env/KMS) in a secrets table or Vault; `api_integrations.secret_ref` only. Secrets never enter prompts or logs.
- **AI-specific**: prompt-injection hygiene (external content wrapped as data, tool outputs size-capped), per-employee tool scopes (least privilege), max tool steps, per-org daily/monthly AI cost caps with hard stop at 100%, PII redaction in logs.
- **Audit**: append-only `activity_logs` with hash chain (`row_hash = sha256(prev_hash || row)`); `/activity/verify-chain` endpoint.
- **Data protection**: DPDP Act 2023 (India), UK GDPR, CAN-SPAM, Australian Spam Act, UAE PDPL — consent fields on contacts, DNC, data export/delete requests (delete is gated).
- **Infra**: TLS (Caddy), firewall (only 80/443/SSH-key), fail2ban, daily encrypted backups off-site, dependency scanning in CI, Sentry for errors.

## C. Employee KPI framework

Each KPI has: `metric`, definition, formula, source, value_type, frequency, target (set by founder). **Targets are blank until the founder sets them**, and KPIs computed by the system are labelled `actual` with source `system:tasks`.

Common to all employees (computed from task data):
- Tasks completed · On-time delivery rate = on-time completed / completed · First-pass approval rate = approved without revision / reviewed · Avg revisions per task · Failure rate · AI cost per completed task (USD).

Role-specific (examples; full list in doc 02 per employee):

| Employee | Output KPIs (system) | Outcome KPIs (from connected APIs, actual only) |
|---|---|---|
| E01 Manager | tasks completed, projects on time %, quality approval rate, team throughput | — |
| E02 SEO | keywords researched, pages audited, issues identified by severity, optimisation tasks done | GSC clicks/impressions trend |
| E03 Social | posts prepared, content delivery rate | engagement rate |
| E04 Writer | articles produced, quality score avg (1–5), on-time rate | organic traffic to pieces |
| E06 Performance | campaigns prepared, optimisations done | CPL, ROAS, CTR |
| E07 Lead Gen | prospects researched, qualified leads, valid contact rate | meetings booked |
| E08 Email | campaigns prepared | open/click/unsub/bounce |
| E13 Analyst | reports on time, data freshness | — |
| E15 Client Success | onboarding days, draft SLA | renewal rate, health score |

Agency KPI: MRR (actual, from invoices/CRM) vs USD 10,000 target, shown as two separate bars, never merged.

## D. Dashboard UI design

**Global layout:** left nav (Overview, Tasks, Approvals [badge], Employees, Clients, Projects, Leads, Campaigns, Calendar, Reports, Costs, Activity, Settings) · top bar (org switcher, search, founder inbox, profile).

**Overview page**
```
┌ KPI tiles ─────────────────────────────────────────────────────────────┐
│ AI employees 15 │ Active now │ Pending │ Completed (7d) │ Failed │ Approvals waiting │
└────────────────────────────────────────────────────────────────────────┘
┌ Tasks by status (stacked bar by employee) ┐ ┌ Approvals inbox (top 5) ──┐
└───────────────────────────────────────────┘ └───────────────────────────┘
┌ Projects in progress (progress, due) ─────┐ ┌ Lead pipeline (funnel) ───┐
└───────────────────────────────────────────┘ └───────────────────────────┘
┌ Campaign performance (actual, by source)  ┐ ┌ Content calendar (week) ──┐
└───────────────────────────────────────────┘ └───────────────────────────┘
┌ AI cost this month vs budget (by employee/model) ┐ ┌ Activity feed (live) ┐
└──────────────────────────────────────────────────┘ └──────────────────────┘
┌ MRR actual vs $10k target ┐  ┌ Daily / monthly reports (links) ┐
```

**Employee workspace (`/employees/E02`)**
Header (avatar, name, role, model, autonomy level, status: idle/working/blocked) · tabs: **Tasks** (kanban by status) · **Deliverables** · **Execution history** (task_runs with tool calls, tokens, cost, duration, errors) · **KPIs** (actual vs target sparklines, labelled) · **Instructions** (prompt versions, diff, activate — founder/admin only) · **Tools & scopes**.

**Task detail:** fields (owner, deadline, priority, deliverable, quality criteria checklist) · dependency mini-DAG · timeline (status changes, messages, reviews) · deliverables preview · approval panel.

**Approval inbox:** list with category chips & money badges; detail drawer with rendered preview, diff (for site/store changes), Approve / Reject with note; MFA prompt where required.

Visual: Tailwind + shadcn/ui, light/dark, status colours consistent (New grey, Assigned blue, In Progress indigo, Waiting for Approval amber, Under Review violet, Revision Required orange, Completed green, Failed red). Mobile: approvals and digest fully usable on phone.
