"""The 15 PMR AI employees: identity, reporting line, model tier, tool scopes.

Source of truth for seeding `ai_employees`. Spec: docs/design/02-employee-specifications.md.
Tool scopes follow `<integration>:<permission>`. Scopes ending in `_gated` never execute
directly; they create an approval request (see design doc 07).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ModelTier(str, Enum):
    REASONING = "reasoning"  # planning, review, strategy, ads, code
    WRITING = "writing"      # copy, social, email, scripts
    FAST = "fast"            # extraction, classification, enrichment


@dataclass(frozen=True)
class EmployeeDef:
    code: str
    display_name: str
    designation: str
    department: str
    model_tier: ModelTier
    tool_scopes: tuple[str, ...]
    reports_to: str | None = "E01"
    autonomy_level: int = 2  # L2: gated external actions queue approvals
    max_concurrent_tasks: int = 3
    owns: tuple[str, ...] = field(default_factory=tuple)  # exclusive responsibilities


EMPLOYEES: tuple[EmployeeDef, ...] = (
    EmployeeDef("E01", "Arjun", "AI Marketing Manager", "Management", ModelTier.REASONING,
                ("tasks:write", "approvals:create", "reports:write", "kb:read", "notify:internal"),
                reports_to=None, max_concurrent_tasks=10, owns=("planning", "review")),
    EmployeeDef("E02", "Surya", "AI SEO Specialist", "Growth", ModelTier.WRITING,
                ("gsc:read", "ga4:read", "pagespeed:read", "crawler:run", "gbp:read", "gbp:post_gated", "kb:read")),
    EmployeeDef("E03", "Meera", "AI Social Media Manager", "Content & Brand", ModelTier.WRITING,
                ("meta:read", "meta:publish_gated", "calendar:write", "kb:read")),
    EmployeeDef("E04", "Kavya", "AI Content Writer", "Content & Brand", ModelTier.WRITING,
                ("wordpress:draft", "wordpress:publish_gated", "calendar:write", "web:research", "kb:read")),
    EmployeeDef("E05", "Ravi", "AI Graphic Designer", "Content & Brand", ModelTier.WRITING,
                ("canva:design", "image:generate", "storage:write", "kb:read", "assets:purchase_gated")),
    EmployeeDef("E06", "Vikram", "AI Performance Marketing Specialist", "Growth", ModelTier.REASONING,
                ("gads:read", "gads:create_paused", "gads:launch_gated", "gads:budget_gated",
                 "meta_ads:read", "meta_ads:create_paused", "meta_ads:launch_gated", "meta_ads:budget_gated", "ga4:read")),
    EmployeeDef("E07", "Priya", "AI Lead Generation Executive", "Growth", ModelTier.FAST,
                ("leads:write", "crm:write_leads", "enrich:read", "email_verify:run", "web:research")),
    EmployeeDef("E08", "Anika", "AI Email Marketing Executive", "Growth", ModelTier.WRITING,
                ("esp:draft", "esp:send_gated", "crm:read", "gmail:draft")),
    EmployeeDef("E09", "Dev", "AI Video Marketing Executive", "Content & Brand", ModelTier.WRITING,
                ("youtube:read", "youtube:upload_gated", "video:generate", "kb:read")),
    EmployeeDef("E10", "Kiran", "AI Web Development Specialist", "Tech", ModelTier.REASONING,
                ("git:branch_pr", "staging:deploy", "wordpress:staging_write", "production:deploy_gated", "lighthouse:run")),
    EmployeeDef("E11", "Nikhil", "AI Automation Specialist", "Tech", ModelTier.REASONING,
                ("n8n:staging_write", "n8n:activate_gated", "crm:read", "kb:read")),
    EmployeeDef("E12", "Sana", "AI eCommerce Manager", "Tech", ModelTier.WRITING,
                ("shopify:read", "shopify:draft", "shopify:apply_gated", "gmc:read")),
    EmployeeDef("E13", "Rohan", "AI Data Analyst", "Intelligence", ModelTier.REASONING,
                ("ga4:read", "gsc:read", "gads:read", "meta_ads:read", "esp:read", "crm:read", "db:read"),
                owns=("performance_numbers",)),
    EmployeeDef("E14", "Isha", "AI Market Research Analyst", "Intelligence", ModelTier.WRITING,
                ("web:search", "web:research", "kb:write_research")),
    EmployeeDef("E15", "Lakshmi", "AI Client Success Manager", "Client", ModelTier.WRITING,
                ("gmail:draft", "gmail:send_gated", "whatsapp:draft", "whatsapp:send_gated",
                 "crm:write_notes", "calendar:propose"),
                owns=("client_communication",)),
)

BY_CODE: dict[str, EmployeeDef] = {e.code: e for e in EMPLOYEES}
SPECIALISTS: tuple[EmployeeDef, ...] = tuple(e for e in EMPLOYEES if e.code != "E01")


def get(code: str) -> EmployeeDef:
    try:
        return BY_CODE[code]
    except KeyError:
        raise KeyError(f"unknown employee code {code!r}") from None


def is_gated_scope(scope: str) -> bool:
    return scope.endswith("_gated")
