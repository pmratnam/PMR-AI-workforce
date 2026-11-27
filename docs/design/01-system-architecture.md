# PMR AI Workforce Platform — 01. System Architecture & Org Chart

Status: **Design (Phase 1)**. Nothing in this document has been built or run yet. All numbers marked *target* are goals, not results.

## 1. What we are building

A multi-tenant web platform where a human founder directs an **AI Marketing Manager**, which plans work and delegates it to **14 specialist AI employees** (15 AI employees in total, including the Manager). Every unit of work is a **Task** with an owner, deadline, deliverable, quality criteria and an execution log. Anything public, financial, external or destructive passes through a **Human Approval Gate** before it touches the outside world.

It is not a chatbot. The chat box is one input; the core is a task/state machine, a tool layer with permissions, and an audit trail.

## 2. Design principles

1. **Human-led, AI-assisted.** AI drafts, prepares and recommends. Humans approve anything irreversible or outward-facing.
2. **Every action is a record.** No AI side effect without a `task`, a `tool_call` log row and (where gated) an `approval` row.
3. **Tools, not freedom.** Employees act only through registered tool adapters with per-employee scopes. No raw credentials ever enter a prompt.
4. **Truth labels on numbers.** Every metric is stored with `value_type ∈ {actual, target, estimate}` and a `source`. The UI never shows an estimate as an actual.
5. **Model-agnostic.** A model router picks Claude / OpenAI / Gemini / Ollama per employee & task type, with cost caps.
6. **Modular monolith first.** One FastAPI service + workers, split later only if load demands it.

## 3. High-level architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│                        FOUNDER / HUMAN STAFF (browser)                    │
└───────────────┬───────────────────────────────────────────┬───────────────┘
                │ HTTPS                                     │ Approvals via
                ▼                                           │ Slack/Telegram/Email
┌───────────────────────────────┐                           │ (links back to app)
│  Next.js 14 Web App (App Rtr) │                           │
│  Dashboard · Workspaces ·     │                           │
│  Approvals · Clients · Leads  │                           │
└───────────────┬───────────────┘                           │
                │ REST + WebSocket (JWT)                    │
                ▼                                           │
┌───────────────────────────────────────────────────────────┴───────────────┐
│                         FastAPI  API Gateway  (/api/v1)                   │
│  Auth & RBAC · Tenancy · Rate limit · Validation · Audit middleware       │
├───────────────────────────────────────────────────────────────────────────┤
│  Domain services                                                          │
│  clients · projects · tasks · approvals · deliverables · leads · campaigns│
│  content_calendar · knowledge · reports · billing/usage · integrations    │
├───────────────────────────────────────────────────────────────────────────┤
│  ORCHESTRATION ENGINE (LangGraph)                                         │
│   Manager graph ── plans ─► Task DAG ─► dispatch ─► Employee graphs (14)  │
│   ▲  review/revise loop        │                    │                     │
│   └──────── QA node ◄──────────┘                    ▼                     │
│                                         TOOL LAYER (adapters + scopes)    │
│                                         ── Approval Gate interceptor ──   │
├───────────────────────────────────────────────────────────────────────────┤
│  Model Router: Claude · OpenAI · Gemini · Ollama   (cost meter, fallback) │
└──────┬──────────────┬───────────────┬────────────────┬────────────────────┘
       │              │               │                │
       ▼              ▼               ▼                ▼
 PostgreSQL 16    Redis 7         Object store      n8n (self-hosted)
 + pgvector       queue (arq),    (S3/MinIO):       webhooks, schedules,
 (system of       cache, locks,   creatives, PDFs,  3rd-party glue
 record, RAG)     pub/sub         reports           ▼
                                               External APIs (official only):
                                               Google Ads, Meta Marketing, GA4,
                                               GSC, GBP, WordPress REST, Shopify,
                                               Gmail, WhatsApp Cloud API, Slack,
                                               Telegram, Zoho CRM, HubSpot, Canva
```

### Runtime components

| Component | Tech | Responsibility |
|---|---|---|
| `web` | Next.js 14, React 18, Tailwind, shadcn/ui, TanStack Query | Dashboard, workspaces, approval inbox |
| `api` | FastAPI, SQLAlchemy 2, Pydantic v2, Alembic | REST/WebSocket API, RBAC, domain logic |
| `worker` | arq (Redis) running LangGraph graphs | Executes tasks asynchronously, retries |
| `scheduler` | arq cron | Daily/weekly/monthly recurring tasks and reports |
| `db` | PostgreSQL 16 + pgvector | System of record + embeddings |
| `redis` | Redis 7 | Queue, cache, rate limits, distributed locks, live events |
| `storage` | S3-compatible (MinIO locally) | Binary deliverables |
| `n8n` | n8n self-hosted | Integration glue, inbound webhooks, notifications |
| `proxy` | Caddy | TLS, reverse proxy |

## 4. AI employee runtime model

Each AI employee = **definition** (DB rows) + **graph** (code):

- `ai_employees` row: name, designation, department, model config, tool scopes, autonomy level.
- `employee_instructions` rows: versioned system prompt, task playbooks, output schema.
- Memory:
  - **Working memory**: the task's context packet (client brief, prior deliverables, dependencies' outputs).
  - **Long-term memory**: `knowledge_base` chunks in pgvector, filtered by `organization_id`, `client_id`, `employee_id`.
  - **Episodic memory**: summaries of past task executions (`task_runs.summary`) retrievable by similarity.
- Graph shape (shared template, specialised per employee):
  `load_context → plan → act (tool loop, max N steps) → self_check (QA checklist) → produce_output (JSON schema) → submit_for_review`

## 5. Org chart

```
                          ┌──────────────────────────┐
                          │  CEO / HUMAN FOUNDER     │  final authority, approvals
                          │  Mani Ratnam             │
                          └────────────┬─────────────┘
                                       │
                          ┌────────────▼─────────────┐
                          │ E01 AI MARKETING MANAGER │  "Arjun"
                          │ plan · assign · QA · report│
                          └────────────┬─────────────┘
       ┌──────────────┬───────────────┼───────────────┬──────────────────┐
       ▼              ▼               ▼               ▼                  ▼
 GROWTH & ACQ.   CONTENT & BRAND   TECH & BUILD   INTELLIGENCE      CLIENT
 ─────────────   ───────────────   ────────────   ────────────      ──────
 E02 SEO         E04 Content       E10 Web Dev    E13 Data Analyst  E15 Client
     Specialist      Writer        E11 Automation E14 Market            Success
 E06 Performance E05 Graphic           Specialist     Research          Manager
     Marketing       Designer      E12 eCommerce      Analyst
 E07 Lead Gen    E03 Social Media      Manager
 E08 Email Mktg      Manager
                 E09 Video Mktg
                          │
                ┌─────────▼──────────┐
                │ TASK EXECUTION + QA│  (self-check → Manager review → human gate)
                └─────────┬──────────┘
                ┌─────────▼──────────┐
                │ CLIENT DELIVERABLES│  & REPORTS
                └────────────────────┘
```

| ID | Name | Designation | Pod |
|---|---|---|---|
| E01 | Arjun | AI Marketing Manager | Management |
| E02 | Surya | AI SEO Specialist | Growth |
| E03 | Meera | AI Social Media Manager | Content & Brand |
| E04 | Kavya | AI Content Writer | Content & Brand |
| E05 | Ravi | AI Graphic Designer | Content & Brand |
| E06 | Vikram | AI Performance Marketing Specialist | Growth |
| E07 | Priya | AI Lead Generation Executive | Growth |
| E08 | Anika | AI Email Marketing Executive | Growth |
| E09 | Dev | AI Video Marketing Executive | Content & Brand |
| E10 | Kiran | AI Web Development Specialist | Tech |
| E11 | Nikhil | AI Automation Specialist | Tech |
| E12 | Sana | AI eCommerce Manager | Tech |
| E13 | Rohan | AI Data Analyst | Intelligence |
| E14 | Isha | AI Market Research Analyst | Intelligence |
| E15 | Lakshmi | AI Client Success Manager | Client |

(Names are editable display labels.)

## 6. Model routing (default plan, editable per org)

| Workload | Default model | Fallback | Why |
|---|---|---|---|
| Manager planning, QA review, strategy, proposals | Claude Opus (latest) | Claude Sonnet | Highest reasoning quality where errors cost most |
| Writing, social, email, scripts | Claude Sonnet (latest) | GPT-class / Gemini | Quality/cost balance |
| Classification, extraction, lead enrichment parsing | Claude Haiku (latest) | Ollama local model | Cheap, high volume |
| Image generation | Image API (e.g. OpenAI Images / Imagen) | — | Claude does not generate images |
| Embeddings | Configurable embedding API or local (Ollama `nomic-embed-text`) | — | pgvector RAG |

Model IDs live in `ai_model_configs`, never hard-coded. Every call writes a `usage_costs` row (tokens, provider, computed cost in USD and INR).

## 7. Integration reality check (what official APIs allow)

| Platform | Official path | Constraints to respect |
|---|---|---|
| Google Ads | Google Ads API | Needs developer token (basic access requires application review), MCC account; budget changes gated |
| Meta Ads | Marketing API | Requires Meta app review + Business verification for most permissions; ad launches gated |
| GA4 | Analytics Data API | Read-only reporting; OAuth per client property |
| Search Console | Search Console API | Read; URL inspection quota limited |
| Google Business Profile | Business Profile APIs | Access must be requested/approved by Google |
| WordPress | REST API + Application Passwords | Publish = gated; drafts allowed |
| Shopify | Admin GraphQL API (custom/public app) | Product/price changes gated |
| Gmail | Gmail API (OAuth) | Drafts allowed, send gated; bulk marketing email must go via an ESP (e.g. Brevo/Mailchimp/SES), not Gmail |
| WhatsApp | WhatsApp Business Platform (Cloud API) | Business-initiated messages need pre-approved templates & opt-in; 24h service window |
| Slack / Telegram | Bot APIs | Internal notifications + approval buttons |
| Zoho CRM / HubSpot | REST APIs, OAuth | Two-way sync of leads/contacts/deals |
| Canva | Canva Connect API | Design creation/export; some endpoints need Canva Enterprise/approval |
| LinkedIn | Not automated for scraping or messaging | Lead gen uses compliant data sources (Apollo, Clay, Hunter, public websites) only |

No scraping behind logins, no auto-DMs on platforms that forbid them, consent and DPDP Act (India), GDPR (UK), CAN-SPAM (USA), Spam Act (Australia) honoured for outreach.

## 8. Non-functional targets (targets, not measurements)

- p95 API latency < 300 ms for non-AI endpoints.
- Task pickup < 10 s after dispatch.
- Zero gated actions executed without an `approved` approval row (enforced in code + tested).
- Daily backups, 30-day retention; RPO 24 h, RTO 4 h for v1.
