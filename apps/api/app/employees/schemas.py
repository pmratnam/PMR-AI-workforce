"""Output contracts for AI employees (design doc 03, section D, and the Manager MODES).

Validation enforces the platform's truth rules, not just shapes:
- every metric carries value_type (actual|target|estimate) and a non-empty source
- a report that lists a gated action must not claim it was executed
- a Manager plan must be acyclic, use known owners, and respect exclusive ownership
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from . import registry


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ValueType(str, Enum):
    actual = "actual"
    target = "target"
    estimate = "estimate"


class ApprovalCategory(str, Enum):
    publish_content = "publish_content"
    bulk_email = "bulk_email"
    external_communication = "external_communication"
    launch_ads = "launch_ads"
    change_ad_budget = "change_ad_budget"
    purchase = "purchase"
    modify_live_site = "modify_live_site"
    delete_data = "delete_data"
    financial_commitment = "financial_commitment"
    contractual_commitment = "contractual_commitment"


class Priority(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


# ---------- Specialist task report ----------

class Deliverable(_Strict):
    type: str = Field(min_length=1)
    title: str = Field(min_length=1)
    content: str | None = None
    uri: str | None = None

    @model_validator(mode="after")
    def _has_body(self):
        if not (self.content or self.uri):
            raise ValueError("deliverable needs content or uri")
        return self


class Metric(_Strict):
    name: str = Field(min_length=1)
    value: float | int | str
    value_type: ValueType
    source: str = Field(min_length=1)
    unit: str | None = None


class QAItem(_Strict):
    item: str = Field(min_length=1)
    passed: bool
    note: str | None = None


class ApprovalNeed(_Strict):
    action: str = Field(min_length=1)
    category: ApprovalCategory
    reason: str = Field(min_length=1)
    executed: Literal[False] = False  # an AI employee can never report a gated action as executed


class TaskReport(_Strict):
    task_id: str = Field(min_length=1)
    status: Literal["submitted_for_review", "blocked", "failed"]
    summary: str = Field(min_length=1, max_length=600)
    deliverables: list[Deliverable] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    qa_checklist: list[QAItem]
    needs_approval: list[ApprovalNeed] = Field(default_factory=list)
    blocker: str | None = None

    @model_validator(mode="after")
    def _consistency(self):
        if self.status == "submitted_for_review" and not self.deliverables:
            raise ValueError("submitted_for_review requires at least one deliverable")
        if self.status == "blocked" and not self.blocker:
            raise ValueError("status 'blocked' requires a blocker explanation")
        if not self.qa_checklist:
            raise ValueError("qa_checklist must not be empty")
        return self

    @property
    def qa_failures(self) -> list[QAItem]:
        return [q for q in self.qa_checklist if not q.passed]


# ---------- Manager outputs ----------

class PlannedTask(_Strict):
    key: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""
    owner: str
    priority: Priority
    deadline: datetime
    expected_deliverable: str = Field(min_length=1)
    quality_criteria: list[str] = Field(min_length=1, max_length=8)
    depends_on: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    approval_category: ApprovalCategory | None = None

    @field_validator("owner")
    @classmethod
    def _known_specialist(cls, v: str) -> str:
        if v not in registry.BY_CODE:
            raise ValueError(f"unknown employee code {v!r}")
        if v == "E01":
            raise ValueError("the Manager does not assign specialist work to itself")
        return v

    @model_validator(mode="after")
    def _gate(self):
        if self.requires_approval and self.approval_category is None:
            raise ValueError(f"task {self.key}: requires_approval needs approval_category")
        return self


# keywords that indicate exclusive-ownership work; checked against title+deliverable
_CLIENT_COMMS = ("email the client", "message the client", "send to client", "client update", "whatsapp the client")


class ManagerPlan(_Strict):
    project_summary: str = Field(min_length=1)
    tasks: list[PlannedTask] = Field(min_length=1)

    @model_validator(mode="after")
    def _graph(self):
        keys = [t.key for t in self.tasks]
        if len(keys) != len(set(keys)):
            raise ValueError("task keys must be unique")
        known = set(keys)
        for t in self.tasks:
            missing = set(t.depends_on) - known
            if missing:
                raise ValueError(f"task {t.key} depends on unknown task(s) {sorted(missing)}")
            if t.key in t.depends_on:
                raise ValueError(f"task {t.key} depends on itself")
            text = f"{t.title} {t.expected_deliverable}".lower()
            if any(k in text for k in _CLIENT_COMMS) and t.owner != "E15":
                raise ValueError(f"task {t.key}: client communication must be owned by E15")
        _assert_acyclic({t.key: t.depends_on for t in self.tasks})
        return self


def _assert_acyclic(graph: dict[str, list[str]]) -> None:
    state: dict[str, int] = {}  # 1 = visiting, 2 = done

    def visit(n: str, path: list[str]) -> None:
        if state.get(n) == 2:
            return
        if state.get(n) == 1:
            raise ValueError("dependency cycle: " + " -> ".join(path + [n]))
        state[n] = 1
        for d in graph[n]:
            visit(d, path + [n])
        state[n] = 2

    for node in graph:
        visit(node, [])


class CriterionResult(_Strict):
    criterion: str
    passed: bool
    reason: str = Field(min_length=1)


class ManagerReview(_Strict):
    task_id: str
    criteria_results: list[CriterionResult] = Field(min_length=1)
    quality_score: int = Field(ge=1, le=5)
    verdict: Literal["approve_internal", "revision_required", "reject"]
    revision_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _coherent(self):
        failed = [c for c in self.criteria_results if not c.passed]
        if self.verdict == "approve_internal" and failed:
            raise ValueError("cannot approve while criteria fail")
        if self.verdict == "revision_required" and not self.revision_notes:
            raise ValueError("revision_required needs revision_notes")
        return self


SCHEMA_FOR_MODE: dict[str, type[BaseModel]] = {
    "task": TaskReport,
    "plan": ManagerPlan,
    "review": ManagerReview,
}
