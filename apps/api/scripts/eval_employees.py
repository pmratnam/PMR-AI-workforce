"""Run each AI employee's golden task against the real Claude API and report pass/fail.

This spends real API credits (roughly one request per employee, plus at most one repair).
    ANTHROPIC_API_KEY=... python -m scripts.eval_employees [E02 E04 ...]

"Pass" means the employee returned a schema-valid report that obeys the truth rules.
It does not grade marketing quality; that is the Manager's review step (Phase 3).
"""
from __future__ import annotations

import json
import sys

from app.employees import runner
from app.llm.router import default_router
from tests.fixtures.golden import DEMO_CLIENT, GOLDEN


def main(codes: list[str]) -> int:
    try:
        router = default_router()
    except RuntimeError as e:
        print(f"Not run: {e}")
        return 2
    total_cost, failures = 0.0, 0
    for code, task in GOLDEN:
        if codes and code not in codes:
            continue
        res = runner.run(code, task, router, DEMO_CLIENT)
        total_cost += res.cost_usd
        status = "PASS" if res.ok else "FAIL"
        failures += not res.ok
        extra = ""
        if res.ok and hasattr(res.output, "qa_failures") and res.output.qa_failures:
            extra = f" (self-reported QA failures: {len(res.output.qa_failures)})"
        print(f"{status} {code} {res.model_id} attempts={res.attempts} cost=${res.cost_usd:.4f}{extra}")
        for err in res.errors:
            print(f"     {err[:300]}")
        if res.ok:
            with open(f"eval_output_{code}.json", "w") as f:
                json.dump(res.output.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
    print(f"total actual API cost: ${total_cost:.4f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
