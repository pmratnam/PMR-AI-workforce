-- Sample records. Clearly fictional demo data (example.com domains). No real performance numbers.
BEGIN;

INSERT INTO organizations (id, name, slug, country, timezone, base_currency, monthly_ai_budget_usd)
VALUES ('00000000-0000-0000-0000-000000000001','PMR Digital Marketing Agency','pmr','IN','Asia/Kolkata','INR',200);

INSERT INTO users (id, email, full_name, mfa_enabled) VALUES
 ('00000000-0000-0000-0000-0000000000a1','founder@pmr.example.com','Founder (PMR)', true);
INSERT INTO memberships (organization_id, user_id, role) VALUES
 ('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-0000000000a1','founder');

INSERT INTO ai_model_configs (id, organization_id, name, provider, model_id, temperature) VALUES
 ('00000000-0000-0000-0000-0000000000c1','00000000-0000-0000-0000-000000000001','reasoning','anthropic','claude-opus-5-5',0.2),
 ('00000000-0000-0000-0000-0000000000c2','00000000-0000-0000-0000-000000000001','writing','anthropic','claude-sonnet-5-5',0.6),
 ('00000000-0000-0000-0000-0000000000c3','00000000-0000-0000-0000-000000000001','fast','anthropic','claude-haiku-5-5',0.1);
UPDATE ai_model_configs SET fallback_config_id='00000000-0000-0000-0000-0000000000c2' WHERE name='reasoning';

-- 15 AI employees
INSERT INTO ai_employees (id, organization_id, code, display_name, designation, department, model_config_id, tool_scopes) VALUES
 ('00000000-0000-0000-0000-000000000e01','00000000-0000-0000-0000-000000000001','E01','Arjun','AI Marketing Manager','Management','00000000-0000-0000-0000-0000000000c1','{tasks:write,approvals:create,reports:write,kb:read,notify:internal}'),
 ('00000000-0000-0000-0000-000000000e02','00000000-0000-0000-0000-000000000001','E02','Surya','AI SEO Specialist','Growth','00000000-0000-0000-0000-0000000000c2','{gsc:read,ga4:read,pagespeed:read,crawler:run,gbp:read,kb:read}'),
 ('00000000-0000-0000-0000-000000000e03','00000000-0000-0000-0000-000000000001','E03','Meera','AI Social Media Manager','Content & Brand','00000000-0000-0000-0000-0000000000c2','{meta:read,meta:publish_gated,calendar:write,kb:read}'),
 ('00000000-0000-0000-0000-000000000e04','00000000-0000-0000-0000-000000000001','E04','Kavya','AI Content Writer','Content & Brand','00000000-0000-0000-0000-0000000000c2','{wordpress:draft,calendar:write,web:research,kb:read}'),
 ('00000000-0000-0000-0000-000000000e05','00000000-0000-0000-0000-000000000001','E05','Ravi','AI Graphic Designer','Content & Brand','00000000-0000-0000-0000-0000000000c2','{canva:design,image:generate,storage:write,kb:read}'),
 ('00000000-0000-0000-0000-000000000e06','00000000-0000-0000-0000-000000000001','E06','Vikram','AI Performance Marketing Specialist','Growth','00000000-0000-0000-0000-0000000000c1','{gads:read,gads:create_paused,meta_ads:read,meta_ads:create_paused,ga4:read}'),
 ('00000000-0000-0000-0000-000000000e07','00000000-0000-0000-0000-000000000001','E07','Priya','AI Lead Generation Executive','Growth','00000000-0000-0000-0000-0000000000c3','{leads:write,crm:write_leads,enrich:read,email_verify:run,web:research}'),
 ('00000000-0000-0000-0000-000000000e08','00000000-0000-0000-0000-000000000001','E08','Anika','AI Email Marketing Executive','Growth','00000000-0000-0000-0000-0000000000c2','{esp:draft,crm:read,gmail:draft}'),
 ('00000000-0000-0000-0000-000000000e09','00000000-0000-0000-0000-000000000001','E09','Dev','AI Video Marketing Executive','Content & Brand','00000000-0000-0000-0000-0000000000c2','{youtube:read,video:generate,kb:read}'),
 ('00000000-0000-0000-0000-000000000e10','00000000-0000-0000-0000-000000000001','E10','Kiran','AI Web Development Specialist','Tech','00000000-0000-0000-0000-0000000000c1','{git:branch_pr,staging:deploy,wordpress:staging_write,lighthouse:run}'),
 ('00000000-0000-0000-0000-000000000e11','00000000-0000-0000-0000-000000000001','E11','Nikhil','AI Automation Specialist','Tech','00000000-0000-0000-0000-0000000000c1','{n8n:staging_write,crm:read,kb:read}'),
 ('00000000-0000-0000-0000-000000000e12','00000000-0000-0000-0000-000000000001','E12','Sana','AI eCommerce Manager','Tech','00000000-0000-0000-0000-0000000000c2','{shopify:read,shopify:draft,gmc:read}'),
 ('00000000-0000-0000-0000-000000000e13','00000000-0000-0000-0000-000000000001','E13','Rohan','AI Data Analyst','Intelligence','00000000-0000-0000-0000-0000000000c1','{ga4:read,gsc:read,gads:read,meta_ads:read,esp:read,crm:read,db:read}'),
 ('00000000-0000-0000-0000-000000000e14','00000000-0000-0000-0000-000000000001','E14','Isha','AI Market Research Analyst','Intelligence','00000000-0000-0000-0000-0000000000c2','{web:search,web:research,kb:write_research}'),
 ('00000000-0000-0000-0000-000000000e15','00000000-0000-0000-0000-000000000001','E15','Lakshmi','AI Client Success Manager','Client','00000000-0000-0000-0000-0000000000c2','{gmail:draft,whatsapp:draft,crm:write_notes,calendar:propose}');
UPDATE ai_employees SET reports_to_id='00000000-0000-0000-0000-000000000e01' WHERE code <> 'E01';

INSERT INTO employee_instructions (employee_id, kind, name, version, content, is_active, created_by) VALUES
 ('00000000-0000-0000-0000-000000000e01','system_prompt','master',1,'See design/03-system-prompts.md section B',true,'00000000-0000-0000-0000-0000000000a1'),
 ('00000000-0000-0000-0000-000000000e02','system_prompt','role',1,'See design/03-system-prompts.md E02',true,'00000000-0000-0000-0000-0000000000a1');

-- Demo client & project
INSERT INTO clients (id, organization_id, name, website, industry, country, currency, status, monthly_retainer, account_owner_user_id) VALUES
 ('00000000-0000-0000-0000-0000000000d1','00000000-0000-0000-0000-000000000001','Demo Dental Clinic','https://demo-dental.example.com','Healthcare','IN','INR','onboarding',45000,'00000000-0000-0000-0000-0000000000a1');

INSERT INTO contacts (id, organization_id, client_id, full_name, email, phone_e164, job_title, country, consent_basis, consent_at) VALUES
 ('00000000-0000-0000-0000-0000000000f1','00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-0000000000d1','Demo Owner','owner@demo-dental.example.com','+919800000000','Owner','IN','contract',now());

INSERT INTO projects (id, organization_id, client_id, name, service_lines, objective, status, start_date, due_date, manager_employee_id, created_by) VALUES
 ('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-0000000000d1','Local SEO + Social Launch','{seo,social_media,content}','Increase appointment enquiries from Hyderabad search (target to be agreed with client)','active','2026-12-01','2027-02-28','00000000-0000-0000-0000-000000000e01','00000000-0000-0000-0000-0000000000a1');

INSERT INTO tasks (id, organization_id, project_id, title, status, priority, owner_employee_id, deadline, expected_deliverable, quality_criteria) VALUES
 ('00000000-0000-0000-0000-000000001001','00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-0000000000b1','Technical + local SEO audit','assigned','high','00000000-0000-0000-0000-000000000e02','2026-12-03T18:00:00+05:30','Audit report + prioritised issue list','["Every issue has URL and evidence","Severity assigned","Fix owner named"]'),
 ('00000000-0000-0000-0000-000000001002','00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-0000000000b1','Keyword map for Hyderabad dental services','new','high','00000000-0000-0000-0000-000000000e02','2026-12-05T18:00:00+05:30','Keyword map sheet','["Intent labelled","Volume source or no data","Mapped to target URL"]'),
 ('00000000-0000-0000-0000-000000001003','00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-0000000000b1','Write 4 service-page drafts','new','medium','00000000-0000-0000-0000-000000000e04','2026-12-10T18:00:00+05:30','4 Markdown drafts with meta','["Keyword in H1","No invented stats","Meta <= 155 chars"]');
UPDATE tasks SET requires_approval=true, approval_category='publish_content' WHERE id='00000000-0000-0000-0000-000000001003';

INSERT INTO task_dependencies (task_id, depends_on_task_id) VALUES
 ('00000000-0000-0000-0000-000000001002','00000000-0000-0000-0000-000000001001'),
 ('00000000-0000-0000-0000-000000001003','00000000-0000-0000-0000-000000001002');

INSERT INTO leads (organization_id, company_name, company_website, country, industry, source, stage, fit_score, fit_reasons, email_verification, owner_employee_id) VALUES
 ('00000000-0000-0000-0000-000000000001','Example Realty LLC','https://realty.example.com','AE','Real estate','website_form','qualified',78,'["Target market UAE","Needs performance marketing"]','valid','00000000-0000-0000-0000-000000000e07');

INSERT INTO performance_metrics (organization_id, subject_type, metric, value, unit, value_type, source, period_start, period_end) VALUES
 ('00000000-0000-0000-0000-000000000001','agency','monthly_recurring_revenue',10000,'USD','target','founder:goal','2027-06-01','2027-06-30');

COMMIT;
