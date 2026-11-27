-- PMR AI Workforce Platform — core schema v1 (PostgreSQL 16 + pgvector)
-- Multi-tenant: every business table carries organization_id.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS citext;

-- ---------- ENUMS ----------
CREATE TYPE user_role        AS ENUM ('founder','admin','manager','specialist','client_viewer');
CREATE TYPE task_status      AS ENUM ('new','assigned','in_progress','waiting_for_approval',
                                      'under_review','revision_required','completed','failed');
CREATE TYPE task_priority    AS ENUM ('critical','high','medium','low');
CREATE TYPE approval_status  AS ENUM ('pending','approved','rejected','expired','cancelled');
CREATE TYPE approval_category AS ENUM ('publish_content','bulk_email','external_communication',
                                      'launch_ads','change_ad_budget','purchase','modify_live_site',
                                      'delete_data','financial_commitment','contractual_commitment');
CREATE TYPE value_type       AS ENUM ('actual','target','estimate');
CREATE TYPE project_status   AS ENUM ('draft','proposed','active','on_hold','completed','cancelled');
CREATE TYPE lead_stage       AS ENUM ('new','researched','qualified','contacted','meeting',
                                      'proposal','won','lost','disqualified');
CREATE TYPE campaign_status  AS ENUM ('draft','ready','pending_approval','live','paused','ended');
CREATE TYPE channel_type     AS ENUM ('email','whatsapp','slack','telegram','phone','meeting','web_form','other');
CREATE TYPE actor_type       AS ENUM ('user','ai_employee','system','integration');

-- ---------- TENANCY & USERS ----------
CREATE TABLE organizations (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name          text NOT NULL,
  slug          citext NOT NULL UNIQUE,
  country       char(2) NOT NULL DEFAULT 'IN',
  timezone      text NOT NULL DEFAULT 'Asia/Kolkata',
  base_currency char(3) NOT NULL DEFAULT 'INR',
  monthly_ai_budget_usd numeric(10,2) NOT NULL DEFAULT 200,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email           citext NOT NULL UNIQUE,
  full_name       text NOT NULL,
  password_hash   text,                       -- null when SSO-only
  mfa_enabled     boolean NOT NULL DEFAULT false,
  is_active       boolean NOT NULL DEFAULT true,
  last_login_at   timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE memberships (
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id         uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role            user_role NOT NULL,
  client_id       uuid,                        -- set for client_viewer scoping (FK added below)
  created_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, user_id)
);

-- ---------- AI MODEL CONFIG ----------
CREATE TABLE ai_model_configs (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id  uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name             text NOT NULL,                       -- e.g. 'reasoning-default'
  provider         text NOT NULL CHECK (provider IN ('anthropic','openai','google','ollama')),
  model_id         text NOT NULL,
  temperature      numeric(3,2) NOT NULL DEFAULT 0.3 CHECK (temperature BETWEEN 0 AND 2),
  max_output_tokens int NOT NULL DEFAULT 4096 CHECK (max_output_tokens > 0),
  input_cost_per_mtok_usd  numeric(10,4) NOT NULL DEFAULT 0,
  output_cost_per_mtok_usd numeric(10,4) NOT NULL DEFAULT 0,
  fallback_config_id uuid REFERENCES ai_model_configs(id),
  is_active        boolean NOT NULL DEFAULT true,
  UNIQUE (organization_id, name)
);

-- ---------- AI EMPLOYEES ----------
CREATE TABLE ai_employees (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id  uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  code             text NOT NULL,                      -- 'E01'..'E15'
  display_name     text NOT NULL,
  designation      text NOT NULL,
  department       text NOT NULL,
  reports_to_id    uuid REFERENCES ai_employees(id),
  model_config_id  uuid REFERENCES ai_model_configs(id),
  autonomy_level   smallint NOT NULL DEFAULT 2 CHECK (autonomy_level BETWEEN 0 AND 3),
  tool_scopes      text[] NOT NULL DEFAULT '{}',       -- e.g. {'gsc:read','wordpress:draft'}
  max_concurrent_tasks smallint NOT NULL DEFAULT 3 CHECK (max_concurrent_tasks > 0),
  is_active        boolean NOT NULL DEFAULT true,
  created_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, code)
);

CREATE TABLE employee_instructions (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id     uuid NOT NULL REFERENCES ai_employees(id) ON DELETE CASCADE,
  kind            text NOT NULL CHECK (kind IN ('system_prompt','playbook','output_schema','qa_checklist')),
  name            text NOT NULL,
  version         int NOT NULL CHECK (version > 0),
  content         text NOT NULL,
  is_active       boolean NOT NULL DEFAULT false,
  created_by      uuid REFERENCES users(id),
  created_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (employee_id, kind, name, version)
);
-- only one active version per (employee, kind, name)
CREATE UNIQUE INDEX uq_instr_active ON employee_instructions(employee_id, kind, name) WHERE is_active;

-- ---------- CLIENTS, CONTACTS, LEADS ----------
CREATE TABLE clients (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name            text NOT NULL,
  website         text,
  industry        text,
  country         char(2) NOT NULL,
  timezone        text NOT NULL DEFAULT 'Asia/Kolkata',
  currency        char(3) NOT NULL DEFAULT 'INR',
  status          text NOT NULL DEFAULT 'onboarding'
                    CHECK (status IN ('prospect','onboarding','active','paused','churned')),
  monthly_retainer numeric(12,2) CHECK (monthly_retainer >= 0),
  health_score    smallint CHECK (health_score BETWEEN 0 AND 100),
  account_owner_user_id uuid REFERENCES users(id),
  crm_external_id text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  deleted_at      timestamptz,
  UNIQUE (organization_id, name)
);
CREATE INDEX ix_clients_org_status ON clients(organization_id, status) WHERE deleted_at IS NULL;

ALTER TABLE memberships ADD CONSTRAINT fk_membership_client
  FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE;

CREATE TABLE contacts (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  client_id       uuid REFERENCES clients(id) ON DELETE SET NULL,
  full_name       text NOT NULL,
  email           citext,
  phone_e164      text CHECK (phone_e164 ~ '^\+[1-9][0-9]{6,14}$'),
  job_title       text,
  country         char(2),
  consent_basis   text CHECK (consent_basis IN ('opt_in','legitimate_interest','contract','none')),
  consent_at      timestamptz,
  do_not_contact  boolean NOT NULL DEFAULT false,
  crm_external_id text,
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_contacts_org_email ON contacts(organization_id, email) WHERE email IS NOT NULL;

CREATE TABLE leads (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  contact_id      uuid REFERENCES contacts(id) ON DELETE SET NULL,
  company_name    text NOT NULL,
  company_website text,
  country         char(2),
  industry        text,
  company_size    text,
  services_interest text[] NOT NULL DEFAULT '{}',
  source          text NOT NULL,                       -- 'apollo','website_form','referral',...
  source_url      text,
  stage           lead_stage NOT NULL DEFAULT 'new',
  fit_score       smallint CHECK (fit_score BETWEEN 0 AND 100),
  fit_reasons     jsonb NOT NULL DEFAULT '[]',
  email_verification text CHECK (email_verification IN ('valid','invalid','risky','unknown')),
  estimated_value numeric(12,2),
  owner_employee_id uuid REFERENCES ai_employees(id),
  converted_client_id uuid REFERENCES clients(id),
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_leads_pipeline ON leads(organization_id, stage, fit_score DESC);

-- ---------- PROJECTS & TASKS ----------
CREATE TABLE projects (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  client_id       uuid REFERENCES clients(id) ON DELETE RESTRICT,  -- null = internal PMR project
  name            text NOT NULL,
  service_lines   text[] NOT NULL DEFAULT '{}',
  objective       text,
  status          project_status NOT NULL DEFAULT 'draft',
  start_date      date,
  due_date        date,
  budget_amount   numeric(12,2),
  budget_currency char(3),
  manager_employee_id uuid REFERENCES ai_employees(id),
  created_by      uuid REFERENCES users(id),
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  CHECK (due_date IS NULL OR start_date IS NULL OR due_date >= start_date)
);
CREATE INDEX ix_projects_org_status ON projects(organization_id, status);
CREATE INDEX ix_projects_client ON projects(client_id);

CREATE TABLE tasks (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  project_id      uuid REFERENCES projects(id) ON DELETE CASCADE,
  parent_task_id  uuid REFERENCES tasks(id) ON DELETE CASCADE,
  title           text NOT NULL,
  description     text,
  status          task_status NOT NULL DEFAULT 'new',
  priority        task_priority NOT NULL DEFAULT 'medium',
  owner_employee_id uuid REFERENCES ai_employees(id),
  owner_user_id   uuid REFERENCES users(id),
  deadline        timestamptz NOT NULL,
  expected_deliverable text NOT NULL,
  quality_criteria jsonb NOT NULL DEFAULT '[]' CHECK (jsonb_typeof(quality_criteria) = 'array'),
  requires_approval boolean NOT NULL DEFAULT false,
  approval_category approval_category,
  revision_count  smallint NOT NULL DEFAULT 0 CHECK (revision_count BETWEEN 0 AND 10),
  attempt_count   smallint NOT NULL DEFAULT 0,
  quality_score   smallint CHECK (quality_score BETWEEN 1 AND 5),
  recurrence_rule text,                                -- RRULE for daily/weekly/monthly tasks
  started_at      timestamptz,
  completed_at    timestamptz,
  created_by_actor actor_type NOT NULL DEFAULT 'user',
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  CHECK (owner_employee_id IS NOT NULL OR owner_user_id IS NOT NULL),
  CHECK (NOT requires_approval OR approval_category IS NOT NULL),
  CHECK (status <> 'completed' OR completed_at IS NOT NULL)
);
CREATE INDEX ix_tasks_board   ON tasks(organization_id, status, priority, deadline);
CREATE INDEX ix_tasks_owner   ON tasks(owner_employee_id, status);
CREATE INDEX ix_tasks_project ON tasks(project_id);

CREATE TABLE task_dependencies (
  task_id            uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  depends_on_task_id uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  kind               text NOT NULL DEFAULT 'finish_to_start',
  PRIMARY KEY (task_id, depends_on_task_id),
  CHECK (task_id <> depends_on_task_id)
);
CREATE INDEX ix_taskdep_reverse ON task_dependencies(depends_on_task_id);
-- Cycle prevention is enforced in the service layer (DFS check before insert) and by trigger below.

CREATE OR REPLACE FUNCTION prevent_task_dependency_cycle() RETURNS trigger AS $$
BEGIN
  IF EXISTS (
    WITH RECURSIVE chain(id) AS (
      SELECT NEW.depends_on_task_id
      UNION
      SELECT d.depends_on_task_id FROM task_dependencies d JOIN chain c ON d.task_id = c.id
    ) SELECT 1 FROM chain WHERE id = NEW.task_id
  ) THEN
    RAISE EXCEPTION 'task dependency cycle detected (% -> %)', NEW.task_id, NEW.depends_on_task_id;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER trg_taskdep_nocycle BEFORE INSERT OR UPDATE ON task_dependencies
  FOR EACH ROW EXECUTE FUNCTION prevent_task_dependency_cycle();

-- Execution log: one row per attempt of an AI employee on a task
CREATE TABLE task_runs (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id         uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  employee_id     uuid REFERENCES ai_employees(id),
  attempt         smallint NOT NULL,
  status          text NOT NULL CHECK (status IN ('running','succeeded','failed','cancelled')),
  input_packet    jsonb NOT NULL,
  output_report   jsonb,
  error           text,
  summary         text,
  summary_embedding vector(1024),
  started_at      timestamptz NOT NULL DEFAULT now(),
  finished_at     timestamptz,
  UNIQUE (task_id, attempt)
);
CREATE INDEX ix_task_runs_task ON task_runs(task_id);

CREATE TABLE task_messages (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id       uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  from_actor    actor_type NOT NULL,
  from_id       uuid,
  to_actor      actor_type,
  to_id         uuid,
  type          text NOT NULL CHECK (type IN ('info','question','handoff','blocker','review_request','review_verdict')),
  body          jsonb NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_task_messages_task ON task_messages(task_id, created_at);

-- ---------- DELIVERABLES & APPROVALS ----------
CREATE TABLE deliverables (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  task_id         uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  client_id       uuid REFERENCES clients(id),
  type            text NOT NULL,                       -- doc,image,video,sheet,url,json,pr
  title           text NOT NULL,
  content_md      text,
  storage_uri     text,
  version         int NOT NULL DEFAULT 1,
  status          text NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft','in_review','approved','delivered','rejected')),
  created_by_employee_id uuid REFERENCES ai_employees(id),
  created_at      timestamptz NOT NULL DEFAULT now(),
  CHECK (content_md IS NOT NULL OR storage_uri IS NOT NULL)
);
CREATE INDEX ix_deliverables_task ON deliverables(task_id);
CREATE INDEX ix_deliverables_client ON deliverables(client_id, created_at DESC);

CREATE TABLE approvals (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  task_id         uuid REFERENCES tasks(id) ON DELETE SET NULL,
  deliverable_id  uuid REFERENCES deliverables(id) ON DELETE SET NULL,
  category        approval_category NOT NULL,
  requested_by_employee_id uuid REFERENCES ai_employees(id),
  action_tool     text NOT NULL,                       -- e.g. 'wordpress.publish_post'
  action_payload  jsonb NOT NULL,                      -- exact call to execute if approved
  payload_hash    text NOT NULL,                       -- sha256 of payload; executor verifies
  risk_summary    text NOT NULL,
  status          approval_status NOT NULL DEFAULT 'pending',
  decided_by      uuid REFERENCES users(id),
  decided_at      timestamptz,
  decision_note   text,
  expires_at      timestamptz NOT NULL DEFAULT now() + interval '72 hours',
  executed_at     timestamptz,
  execution_result jsonb,
  created_at      timestamptz NOT NULL DEFAULT now(),
  CHECK ((status IN ('approved','rejected')) = (decided_by IS NOT NULL AND decided_at IS NOT NULL)),
  CHECK (executed_at IS NULL OR status = 'approved')
);
CREATE INDEX ix_approvals_inbox ON approvals(organization_id, status, created_at) WHERE status = 'pending';

-- ---------- CAMPAIGNS & CONTENT ----------
CREATE TABLE campaigns (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  client_id       uuid NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  project_id      uuid REFERENCES projects(id) ON DELETE SET NULL,
  name            text NOT NULL,
  channel         text NOT NULL CHECK (channel IN ('google_ads','meta_ads','email','social','seo','whatsapp','youtube','other')),
  objective       text,
  status          campaign_status NOT NULL DEFAULT 'draft',
  approved_budget numeric(12,2) CHECK (approved_budget >= 0),
  budget_currency char(3),
  start_date      date,
  end_date        date,
  external_id     text,                                -- platform campaign id
  owner_employee_id uuid REFERENCES ai_employees(id),
  created_at      timestamptz NOT NULL DEFAULT now(),
  CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);
CREATE INDEX ix_campaigns_client ON campaigns(client_id, status);

CREATE TABLE content_calendar (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  client_id       uuid NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  campaign_id     uuid REFERENCES campaigns(id) ON DELETE SET NULL,
  task_id         uuid REFERENCES tasks(id) ON DELETE SET NULL,
  deliverable_id  uuid REFERENCES deliverables(id) ON DELETE SET NULL,
  platform        text NOT NULL,                       -- instagram,linkedin,blog,youtube,email,...
  title           text NOT NULL,
  pillar          text,
  publish_at      timestamptz NOT NULL,
  status          text NOT NULL DEFAULT 'planned'
                    CHECK (status IN ('planned','drafting','ready','approved','scheduled','published','cancelled')),
  published_url   text,
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_calendar_client_date ON content_calendar(client_id, publish_at);

-- ---------- CONVERSATIONS ----------
CREATE TABLE conversations (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  client_id       uuid REFERENCES clients(id) ON DELETE CASCADE,
  contact_id      uuid REFERENCES contacts(id) ON DELETE SET NULL,
  lead_id         uuid REFERENCES leads(id) ON DELETE SET NULL,
  channel         channel_type NOT NULL,
  external_thread_id text,
  subject         text,
  last_message_at timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE conversation_messages (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  direction       text NOT NULL CHECK (direction IN ('inbound','outbound','draft')),
  author_actor    actor_type NOT NULL,
  author_id       uuid,
  body            text NOT NULL,
  approval_id     uuid REFERENCES approvals(id),      -- required for outbound
  sent_at         timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  CHECK (direction <> 'outbound' OR approval_id IS NOT NULL OR author_actor = 'user')
);
CREATE INDEX ix_conv_msgs ON conversation_messages(conversation_id, created_at);

-- ---------- KNOWLEDGE BASE (RAG) ----------
CREATE TABLE knowledge_documents (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  client_id       uuid REFERENCES clients(id) ON DELETE CASCADE,   -- null = agency-wide
  employee_id     uuid REFERENCES ai_employees(id) ON DELETE CASCADE, -- null = all employees
  title           text NOT NULL,
  doc_type        text NOT NULL,          -- brand_guide, sop, research, past_deliverable, faq
  source_uri      text,
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE knowledge_chunks (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id     uuid NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  client_id       uuid,
  chunk_index     int NOT NULL,
  content         text NOT NULL,
  embedding       vector(1024) NOT NULL,
  tokens          int,
  UNIQUE (document_id, chunk_index)
);
CREATE INDEX ix_kchunks_scope ON knowledge_chunks(organization_id, client_id);
CREATE INDEX ix_kchunks_embedding ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);

-- ---------- INTEGRATIONS ----------
CREATE TABLE api_integrations (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  client_id       uuid REFERENCES clients(id) ON DELETE CASCADE,
  provider        text NOT NULL,          -- google_ads, meta, ga4, gsc, gbp, wordpress, shopify, gmail, ...
  account_ref     text NOT NULL,          -- property id / ad account id / site url
  scopes          text[] NOT NULL DEFAULT '{}',
  secret_ref      text NOT NULL,          -- pointer into secrets vault; never the secret itself
  status          text NOT NULL DEFAULT 'active' CHECK (status IN ('active','expired','revoked','error')),
  last_synced_at  timestamptz,
  last_error      text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, provider, account_ref)
);

-- ---------- USAGE & COSTS ----------
CREATE TABLE usage_costs (
  id              bigserial PRIMARY KEY,
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  employee_id     uuid REFERENCES ai_employees(id),
  task_id         uuid REFERENCES tasks(id) ON DELETE SET NULL,
  task_run_id     uuid REFERENCES task_runs(id) ON DELETE SET NULL,
  provider        text NOT NULL,
  model_id        text NOT NULL,
  kind            text NOT NULL DEFAULT 'llm' CHECK (kind IN ('llm','embedding','image','video','api_call')),
  input_tokens    int NOT NULL DEFAULT 0,
  output_tokens   int NOT NULL DEFAULT 0,
  units           numeric(12,4) NOT NULL DEFAULT 0,
  cost_usd        numeric(12,6) NOT NULL DEFAULT 0 CHECK (cost_usd >= 0),
  occurred_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_usage_org_time ON usage_costs(organization_id, occurred_at);
CREATE INDEX ix_usage_employee ON usage_costs(employee_id, occurred_at);

-- ---------- ACTIVITY / AUDIT LOG (append-only) ----------
CREATE TABLE activity_logs (
  id              bigserial PRIMARY KEY,
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  actor_type      actor_type NOT NULL,
  actor_id        uuid,
  action          text NOT NULL,          -- 'task.status_changed','approval.approved','tool.call',...
  entity_type     text NOT NULL,
  entity_id       uuid,
  before          jsonb,
  after           jsonb,
  ip              inet,
  prev_hash       text,                   -- hash chain for tamper evidence
  row_hash        text NOT NULL,
  occurred_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_activity_entity ON activity_logs(entity_type, entity_id, occurred_at);
CREATE INDEX ix_activity_org_time ON activity_logs(organization_id, occurred_at DESC);

CREATE OR REPLACE FUNCTION forbid_mutation() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'activity_logs is append-only'; END $$ LANGUAGE plpgsql;
CREATE TRIGGER trg_activity_append_only BEFORE UPDATE OR DELETE ON activity_logs
  FOR EACH ROW EXECUTE FUNCTION forbid_mutation();

-- ---------- PERFORMANCE ----------
CREATE TABLE performance_metrics (
  id              bigserial PRIMARY KEY,
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  subject_type    text NOT NULL CHECK (subject_type IN ('employee','client','campaign','project','agency')),
  subject_id      uuid,
  metric          text NOT NULL,           -- 'keywords_researched','engagement_rate',...
  value           numeric NOT NULL,
  unit            text,
  value_type      value_type NOT NULL,
  source          text NOT NULL,           -- 'system:tasks','api:ga4',...
  period_start    date NOT NULL,
  period_end      date NOT NULL,
  captured_at     timestamptz NOT NULL DEFAULT now(),
  CHECK (period_end >= period_start)
);
CREATE INDEX ix_perf_subject ON performance_metrics(subject_type, subject_id, metric, period_start);

CREATE TABLE performance_reports (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  scope           text NOT NULL CHECK (scope IN ('daily','weekly','monthly')),
  subject_type    text NOT NULL CHECK (subject_type IN ('agency','client','employee')),
  subject_id      uuid,
  period_start    date NOT NULL,
  period_end      date NOT NULL,
  content_md      text NOT NULL,
  data            jsonb NOT NULL DEFAULT '{}',
  generated_by_employee_id uuid REFERENCES ai_employees(id),
  deliverable_id  uuid REFERENCES deliverables(id),
  created_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, scope, subject_type, subject_id, period_start)
);
