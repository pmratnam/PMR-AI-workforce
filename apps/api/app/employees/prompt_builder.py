"""Assembles a model request for an AI employee.

system  = BASE PROMPT (placeholders filled) + ROLE PROMPT          (stable -> cacheable)
user    = CLIENT CONTEXT PACKET + TASK PACKET + EPISODIC NOTES + OUTPUT SCHEMA

Anything that came from outside the platform (client docs, web pages, prior deliverables)
is wrapped in <untrusted_data> so the base prompt's rule 6 can apply to it.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from . import registry
from .schemas import SCHEMA_FOR_MODE

PROMPT_DIR = Path(__file__).parent / "prompts"
_PLACEHOLDER = re.compile(r"{{\s*([a-z_]+)\s*}}")
MANAGER_MODES = {"intake", "plan", "monitor", "review", "report"}


class PromptError(ValueError):
    pass


class PromptSource:
    """Reads prompt text. Files by default; the DB-backed loader (active rows in
    employee_instructions) is passed in as `overrides` so tests and seeds share one path."""

    def __init__(self, directory: Path = PROMPT_DIR, overrides: Mapping[str, str] | None = None):
        self.directory = directory
        self.overrides = dict(overrides or {})

    def get(self, name: str) -> str:
        if name in self.overrides:
            return self.overrides[name]
        path = self.directory / f"{name}.md"
        if not path.exists():
            raise PromptError(f"prompt {name!r} not found in {self.directory}")
        return path.read_text(encoding="utf-8")


@dataclass
class TaskPacket:
    task_id: str
    title: str
    description: str
    priority: str
    deadline: str
    expected_deliverable: str
    quality_criteria: list[str]
    dependency_outputs: list[dict[str, Any]] = field(default_factory=list)
    reviewer_feedback: list[str] = field(default_factory=list)


@dataclass
class BuiltPrompt:
    system: str
    user: str
    schema_name: str
    output_schema: dict[str, Any]


def _fill(template: str, values: Mapping[str, str]) -> str:
    def sub(m: re.Match[str]) -> str:
        key = m.group(1)
        if key not in values:
            raise PromptError(f"no value for placeholder {{{{{key}}}}}")
        return values[key]

    out = _PLACEHOLDER.sub(sub, template)
    if "{{" in out:
        raise PromptError("unfilled placeholder remains after substitution")
    return out


def _untrusted(label: str, payload: Any) -> str:
    body = payload if isinstance(payload, str) else json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    return f'<untrusted_data source="{label}">\n{body}\n</untrusted_data>'


def build(
    code: str,
    task: TaskPacket,
    client_context: Mapping[str, Any] | None = None,
    episodic_notes: list[str] | None = None,
    mode: str | None = None,
    source: PromptSource | None = None,
) -> BuiltPrompt:
    emp = registry.get(code)
    src = source or PromptSource()

    if code == "E01":
        mode = mode or "plan"
        if mode not in MANAGER_MODES:
            raise PromptError(f"unknown Manager mode {mode!r}")
        schema_name = "plan" if mode == "plan" else "review" if mode == "review" else None
    else:
        if mode not in (None, "task"):
            raise PromptError("specialists only run in 'task' mode")
        mode, schema_name = "task", "task"
    if schema_name is None:
        raise PromptError(f"Manager mode {mode!r} has no output schema yet (planned for Phase 3)")

    system = _fill(src.get("base"), {"employee_name": emp.display_name, "designation": emp.designation})
    system += "\n\n" + src.get(code).strip() + "\n"

    schema = SCHEMA_FOR_MODE[schema_name].model_json_schema()
    parts = [f"MODE: {mode.upper()}"]
    parts.append("CLIENT CONTEXT PACKET\n" + _untrusted("client_context", client_context or {"note": "no client context (internal PMR task)"}))
    packet = {
        "task_id": task.task_id, "title": task.title, "description": task.description,
        "priority": task.priority, "deadline": task.deadline,
        "expected_deliverable": task.expected_deliverable, "quality_criteria": task.quality_criteria,
        "reviewer_feedback_from_previous_attempts": task.reviewer_feedback,
    }
    parts.append("TASK PACKET\n" + json.dumps(packet, indent=2, ensure_ascii=False))
    if task.dependency_outputs:
        parts.append("OUTPUTS OF DEPENDENCY TASKS\n" + _untrusted("dependency_outputs", task.dependency_outputs))
    if episodic_notes:
        parts.append("EPISODIC NOTES\n" + "\n".join(f"- {n}" for n in episodic_notes))
    parts.append(
        "OUTPUT SCHEMA\nReturn only one JSON object that validates against this JSON Schema. "
        "No prose before or after it.\n" + json.dumps(schema, ensure_ascii=False)
    )
    return BuiltPrompt(system=system, user="\n\n".join(parts), schema_name=schema_name, output_schema=schema)
