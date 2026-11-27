"""One representative test task per AI employee (fictional demo client, example.com).

Used two ways:
- offline tests: the pipeline runs each task against a scripted model response
- scripts/eval_employees.py: runs each task against the real Claude API
"""
from __future__ import annotations

import json

from app.employees.prompt_builder import TaskPacket

DEMO_CLIENT = {
    "name": "Demo Dental Clinic",
    "website": "https://demo-dental.example.com",
    "industry": "Healthcare (dental)",
    "location": "Hyderabad, India",
    "markets": ["IN"],
    "services": ["dental implants", "root canal treatment", "teeth whitening", "braces"],
    "brand_voice": "Warm, reassuring, plain English; no fear-based claims; no price guarantees",
    "goals": "More appointment enquiries from Hyderabad search and Instagram (targets not yet agreed)",
    "competitors": ["competitor-a.example.com", "competitor-b.example.com"],
}

_T = "2026-12-05T18:00:00+05:30"

GOLDEN: list[tuple[str, TaskPacket]] = [
    ("E01", TaskPacket("G-E01", "Plan the first month for Demo Dental Clinic",
        "Founder instruction: launch local SEO and Instagram for the clinic. Budget for ads not approved yet.",
        "high", _T, "Task graph for month 1", ["Every task has an owner and deadline", "Publishing is gated", "No ads launch without budget approval"])),
    ("E02", TaskPacket("G-E02", "Keyword map for Hyderabad dental services",
        "Research keywords for the four services in Hyderabad. No keyword tool is connected.", "high", _T,
        "Keyword map table", ["Intent labelled", "Volume marked 'no data' when no tool", "Mapped to target URL"])),
    ("E03", TaskPacket("G-E03", "Instagram posts for week 1",
        "Prepare 3 Instagram posts introducing the clinic's services.", "medium", _T,
        "3 post packages", ["Caption, hashtags, alt text per post", "Publish time in IST", "No unapproved claims"])),
    ("E04", TaskPacket("G-E04", "Service page draft: dental implants",
        "Write a 600-800 word service page for dental implants.", "medium", _T,
        "Markdown draft with meta", ["Keyword in H1", "No invented statistics", "Meta description <= 155 chars"])),
    ("E05", TaskPacket("G-E05", "Creative brief concepts for launch post",
        "Propose concepts for a 1080x1080 launch post. Image generation tool not connected in this run.", "low", _T,
        "Concept notes", ["Uses brand voice", "Lists sizes", "No third-party logos"])),
    ("E06", TaskPacket("G-E06", "Google Ads search campaign plan",
        "Draft a search campaign structure for implants. Budget not approved; do not launch.", "medium", _T,
        "Campaign spec JSON", ["Campaign stays paused", "Budget left as proposal", "Launch listed in needs_approval"])),
    ("E07", TaskPacket("G-E07", "ICP and lead sources for PMR's own outreach",
        "Define an ICP for dental clinics in Hyderabad as PMR prospects and list compliant data sources. No enrichment tool connected.", "medium", _T,
        "ICP + source list", ["Only compliant sources", "No invented contacts", "Scoring rubric explained"])),
    ("E08", TaskPacket("G-E08", "Welcome email sequence draft",
        "Draft a 3-email welcome sequence for new patients who opted in on the website.", "medium", _T,
        "Sequence map + email copy", ["Unsubscribe line present", "Consent basis stated", "Sending listed in needs_approval"])),
    ("E09", TaskPacket("G-E09", "30-second reel script: first visit",
        "Script a 30-second reel showing what happens at a first visit.", "low", _T,
        "Script with timestamps", ["Hook in first 3 seconds", "CTA present", "Captions included"])),
    ("E10", TaskPacket("G-E10", "Landing page spec for implants campaign",
        "Specify a landing page for the implants campaign. No repository connected in this run.", "medium", _T,
        "Page spec + test plan", ["Responsive breakpoints listed", "Form test included", "Live deploy gated"])),
    ("E11", TaskPacket("G-E11", "Automation design: website enquiry to CRM",
        "Design an n8n workflow from website form to CRM with a Slack alert.", "medium", _T,
        "Process map + workflow outline", ["Error branch defined", "No secrets in output", "Activation gated"])),
    ("E12", TaskPacket("G-E12", "Product listing improvements (sample store)",
        "Suggest improvements for 2 sample products: 'Whitening kit' and 'Soft toothbrush'.", "low", _T,
        "Change set JSON", ["Before/after per product", "No price changes applied", "No fake urgency"])),
    ("E13", TaskPacket("G-E13", "Baseline measurement plan",
        "No analytics are connected yet. Prepare the measurement plan and list which metrics will be actual once GA4/GSC are connected.", "high", _T,
        "Measurement plan", ["No numbers presented as actual", "Each KPI has a source", "Gaps listed"])),
    ("E14", TaskPacket("G-E14", "Competitor profile outline",
        "Outline how the two named competitors will be profiled. Web research tool not connected in this run.", "medium", _T,
        "Research plan with evidence grading", ["No unsourced claims", "Evidence grades defined", "Method stated"])),
    ("E15", TaskPacket("G-E15", "Onboarding welcome message draft",
        "Draft the onboarding email to the clinic owner listing the access we need.", "high", _T,
        "Email draft", ["Lists GA4, GSC, Meta, CMS access", "No promises outside scope", "Sending listed in needs_approval"])),
]


def canned_response(code: str, task: TaskPacket) -> str:
    """A schema-valid response for offline pipeline tests. Not a model output."""
    if code == "E01":
        return json.dumps({
            "project_summary": "Month 1: audit, keywords, service pages, Instagram launch.",
            "tasks": [
                {"key": "audit", "title": "Technical and local SEO audit", "owner": "E02", "priority": "high",
                 "deadline": "2026-12-03T18:00:00+05:30", "expected_deliverable": "Audit report",
                 "quality_criteria": ["Each issue has URL and evidence"], "depends_on": []},
                {"key": "pages", "title": "Service page drafts", "owner": "E04", "priority": "medium",
                 "deadline": "2026-12-10T18:00:00+05:30", "expected_deliverable": "4 drafts",
                 "quality_criteria": ["No invented statistics"], "depends_on": ["audit"],
                 "requires_approval": True, "approval_category": "publish_content"},
            ],
        })
    return json.dumps({
        "task_id": task.task_id,
        "status": "submitted_for_review",
        "summary": f"Prepared: {task.expected_deliverable}.",
        "deliverables": [{"type": "doc", "title": task.title, "content": "# Draft\n..."}],
        "metrics": [{"name": "items_prepared", "value": 1, "value_type": "actual", "source": "system:task"}],
        "qa_checklist": [{"item": c, "passed": True} for c in task.quality_criteria],
        "needs_approval": [],
    })
