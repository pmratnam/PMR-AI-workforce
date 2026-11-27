"""Runs one AI employee on one task: build prompt -> call model -> parse -> validate.

If the output is not valid JSON or fails the schema / truth rules, the runner sends the
validation errors back once and asks for a corrected object. A second failure returns a
`failed` RunResult; it never fabricates or "fixes up" the model's output itself.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from pydantic import BaseModel, ValidationError

from app.llm.router import ModelRouter

from . import prompt_builder, registry
from .schemas import SCHEMA_FOR_MODE

MAX_REPAIRS = 1
_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.S)


@dataclass
class RunResult:
    ok: bool
    employee: str
    output: BaseModel | None
    attempts: int
    errors: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    model_id: str = ""


def _parse(text: str, schema_name: str) -> tuple[BaseModel | None, str | None]:
    raw = text.strip()
    m = _FENCE.match(raw)
    if m:
        raw = m.group(1)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return None, f"response is not valid JSON: {e.msg} at position {e.pos}"
    try:
        return SCHEMA_FOR_MODE[schema_name].model_validate(data), None
    except ValidationError as e:
        details = "; ".join(f"{'.'.join(map(str, err['loc'])) or '<root>'}: {err['msg']}" for err in e.errors())
        return None, f"schema validation failed: {details}"


def run(
    code: str,
    task: prompt_builder.TaskPacket,
    router: ModelRouter,
    client_context: Mapping[str, Any] | None = None,
    episodic_notes: list[str] | None = None,
    mode: str | None = None,
    source: prompt_builder.PromptSource | None = None,
) -> RunResult:
    emp = registry.get(code)
    cfg = router.config_for(emp.model_tier)
    built = prompt_builder.build(code, task, client_context, episodic_notes, mode, source)
    messages: list[dict] = [{"role": "user", "content": built.user}]
    result = RunResult(ok=False, employee=code, output=None, attempts=0, model_id=cfg.model_id)

    for attempt in range(1 + MAX_REPAIRS):
        comp = router.provider.complete(cfg, built.system, messages)
        result.attempts = attempt + 1
        result.input_tokens += comp.input_tokens
        result.output_tokens += comp.output_tokens
        result.cost_usd = round(result.cost_usd + comp.cost_usd(cfg), 6)
        if comp.stop_reason == "refusal":
            result.errors.append("model declined the request (refusal)")
            return result
        if comp.stop_reason == "max_tokens":
            result.errors.append("response truncated at max_tokens")
            return result
        output, err = _parse(comp.text, built.schema_name)
        if output is not None:
            if code != "E01" and getattr(output, "task_id", task.task_id) != task.task_id:
                err = f"task_id mismatch: expected {task.task_id!r}"
            else:
                result.ok, result.output = True, output
                return result
        result.errors.append(err)
        messages += [
            {"role": "assistant", "content": comp.text},
            {"role": "user", "content": f"Your response was rejected: {err}\nReturn the corrected JSON object only."},
        ]
    return result
