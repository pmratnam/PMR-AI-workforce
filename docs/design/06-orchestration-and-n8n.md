# 06. AI Orchestration Workflows & n8n Blueprints

## 1. Task state machine (enforced in `services/task_state_machine.py`)

```
            assign                start                 submit
  NEW ───────────► ASSIGNED ───────────► IN_PROGRESS ───────────► UNDER_REVIEW
                      ▲                     │  ▲                     │   │   │
                      │ reassign            │  │ revise              │   │   │ manager approve_internal
                      │                     │  └── REVISION_REQUIRED ◄┘   │   │  + requires_approval
                      │                     │ error ×2                   │   ▼
                      └──────────── FAILED ◄┘   (≤3 revisions, then      │  WAITING_FOR_APPROVAL
                                     ▲          escalate)                │   │ human approves → execute
                                     └────────── human rejects ──────────┼───┘ action → COMPLETED
                                                                         │
                                                  approve_internal, no gate └──► COMPLETED
```

Rules: only the state machine can write `tasks.status`; every transition writes `activity_logs`; `COMPLETED` requires (a) Manager verdict `approve_internal`, (b) approval row `approved` **and** executed successfully when the task is gated. A tool-call failure after approval sets the task to `FAILED`, never `COMPLETED`.

## 2. Manager graph (LangGraph)

```
founder_instruction
      │
   [intake] ── missing info? ──► ask_founder (interrupt; resumes on reply)
      │
   [plan]  → task DAG JSON → validate (owners exist, acyclic, deadlines, gates) → persist tasks
      │
   [dispatch] → enqueue tasks whose dependencies are COMPLETED and owner has capacity
      │
   (event loop on task events)
      ├─ task submitted ──► [review] ─► approve_internal ─► gate? ─► approvals.request
      │                             └► revision_required ─► re-enqueue with notes
      ├─ task blocked/failed ──► [monitor] ─► reassign / split / escalate
      └─ cron 19:00 IST ──► [report:daily];  Mon 09:00 ──► [report:weekly]
```

## 3. Employee graph (shared template)

```
load_context (client packet + task packet + RAG top-k + episodic notes)
   → plan_steps
   → act  (tool loop; max 12 tool calls; each call: scope check → gate check → execute → log → cost)
   → self_check (role QA checklist + universal QA)
   → produce_output (validate against task_report JSON schema; 1 auto-repair attempt)
   → submit (status UNDER_REVIEW) | blocker (notify Manager)
```

Gated tool calls never execute in `act`: the gate interceptor stores `{tool, payload, hash}` in `approvals` and returns `APPROVAL_REQUIRED` to the agent, which lists it in `needs_approval`.

## 4. Client lifecycle workflow (15 stages → owners → gates)

| # | Stage | Owner(s) | Output | Human gate |
|---|---|---|---|---|
| 1 | Lead acquisition | E07, E14 | Lead records | Buying lists |
| 2 | Lead qualification | E07 → E01 | Fit score, notes | — |
| 3 | Client onboarding | E15 | Onboarding checklist, access requests | Sending emails/WA |
| 4 | Business & website audit | E02, E10, E13 | Audit report | — |
| 5 | Competitor analysis | E14, E02 | Competitor profiles | — |
| 6 | Digital marketing strategy | E01 (+E02,E03,E06,E08) | Strategy doc | — |
| 7 | Proposal & quotation | E01 drafts, E15 packages | Proposal PDF | **Pricing + sending (founder)** |
| 8 | Client approval | Founder / client | Signed proposal | Contractual commitment |
| 9 | Project creation | E01 | Project + task DAG | — |
| 10 | Task assignment | E01 | Assigned tasks | — |
| 11 | Content & creative production | E04, E05, E09, E03 | Deliverables | — |
| 12 | Campaign execution | E03, E06, E08, E10, E12 | Live campaigns/posts | **Publish, launch, budget, live site** |
| 13 | Performance monitoring | E13 | Metrics (actual) | — |
| 14 | Client reporting | E13 data → E15 report | Monthly report | Sending to client |
| 15 | Renewal & upselling | E15, E01 | Renewal/upsell proposal | Pricing + sending |

## 5. Recurring cadence (cron, Asia/Kolkata)

| When | Job |
|---|---|
| Every 15 min | dispatch ready tasks; expire stale approvals (72 h); sync integration health |
| 06:00 daily | E13 metrics sync (GA4, GSC, Ads, Meta, ESP) |
| 09:00 daily | create recurring daily tasks per employee (RRULE) |
| 19:00 daily | Manager daily digest → founder (Slack/Telegram/email) |
| Mon 09:00 | weekly sprint plan + client weekly reports (drafts) |
| 1st of month 10:00 | monthly client reports, employee KPI report, cost report |

## 6. n8n blueprints (integration glue — the platform remains the system of record)

Each blueprint is a workflow exported to `automation/n8n/workflows/`. Pattern: **n8n handles triggers and third-party plumbing; it calls the platform API; the platform decides and audits.** n8n never bypasses the approval gate.

| # | Workflow | Trigger | Steps |
|---|---|---|---|
| N1 | Inbound lead capture | Webhook (website form / Meta Lead Ads webhook) | Normalise → `POST /leads` → platform creates E07 qualification task → Slack notify |
| N2 | CRM sync | Cron 30 min | Pull changed leads/deals from Zoho/HubSpot → upsert via API; push platform stage changes back |
| N3 | Approval notifications | Platform webhook `approval.created` | Slack/Telegram message with summary + "Open in app" link (decisions happen in-app with MFA for spend) |
| N4 | Approved action executor (selected providers) | Platform webhook `approval.approved` | Verify signature + payload hash → call provider (e.g. WordPress publish, Meta post) → `POST /approvals/{id}/result` |
| N5 | WhatsApp inbound | WhatsApp Cloud API webhook | Store message via `/webhooks/whatsapp` → E15 draft-reply task |
| N6 | Daily digest delivery | Platform webhook `report.generated` | Format → Slack + Telegram + email to founder |
| N7 | Integration token health | Cron daily | Check OAuth tokens → mark expired → notify founder with reconnect link |
| N8 | Client report delivery | `approval.approved` (category external_communication) | Send PDF via Gmail API/ESP → log conversation message |

Example N1 skeleton (n8n JSON excerpt):
```json
{
  "name": "N1 Inbound lead capture",
  "nodes": [
    {"name": "Webhook", "type": "n8n-nodes-base.webhook", "parameters": {"path": "lead-in", "httpMethod": "POST"}},
    {"name": "Normalise", "type": "n8n-nodes-base.set", "parameters": {"values": {"string": [
      {"name": "company_name", "value": "={{$json.company}}"},
      {"name": "source", "value": "website_form"}]}}},
    {"name": "Create lead", "type": "n8n-nodes-base.httpRequest", "parameters": {
      "method": "POST", "url": "={{$env.PMR_API}}/api/v1/leads",
      "authentication": "predefinedCredentialType", "sendBody": true}},
    {"name": "Notify Slack", "type": "n8n-nodes-base.slack", "parameters": {"channel": "#leads"}}
  ],
  "connections": {"Webhook": {"main": [[{"node": "Normalise"}]]},
                  "Normalise": {"main": [[{"node": "Create lead"}]]},
                  "Create lead": {"main": [[{"node": "Notify Slack"}]]}}
}
```
(Skeleton only; full importable JSON is produced and tested in Phase 6.)
