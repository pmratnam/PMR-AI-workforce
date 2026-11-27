"""Model router: maps an employee's tier to a provider + model, and meters every call.

Only the Anthropic provider is implemented in Phase 2. OpenAI / Gemini / Ollama slot in
behind the same `Provider` protocol in Phase 6. `ScriptedProvider` is a test double that
returns pre-written responses so the pipeline can be tested without network or cost.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from app.employees.registry import ModelTier


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    model_id: str
    effort: str
    max_tokens: int
    input_cost_per_mtok_usd: float
    output_cost_per_mtok_usd: float


# Defaults mirror design doc 01 §6. Prices: Anthropic list prices (USD per 1M tokens), 2026-11.
DEFAULT_MODELS: dict[ModelTier, ModelConfig] = {
    ModelTier.REASONING: ModelConfig("anthropic", "claude-opus-5-5", "high", 16000, 4.00, 20.00),
    ModelTier.WRITING: ModelConfig("anthropic", "claude-sonnet-5-5", "medium", 16000, 2.00, 10.00),
    ModelTier.FAST: ModelConfig("anthropic", "claude-haiku-5-5", "low", 8000, 0.10, 0.50),
}


@dataclass
class Completion:
    text: str
    model_id: str
    input_tokens: int
    output_tokens: int
    stop_reason: str | None

    def cost_usd(self, cfg: ModelConfig) -> float:
        return round(self.input_tokens / 1e6 * cfg.input_cost_per_mtok_usd
                     + self.output_tokens / 1e6 * cfg.output_cost_per_mtok_usd, 6)


class Provider(Protocol):
    def complete(self, cfg: ModelConfig, system: str, messages: list[dict]) -> Completion: ...


class AnthropicProvider:
    """Calls the Claude Messages API. Server-side refusal fallback is enabled ("default"
    routing) so a policy decline is retried on a suitable model inside the same call."""

    def __init__(self, client=None):
        if client is None:
            import anthropic
            client = anthropic.Anthropic()
        self.client = client

    def complete(self, cfg: ModelConfig, system: str, messages: list[dict]) -> Completion:
        kwargs = dict(
            model=cfg.model_id,
            max_tokens=cfg.max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
            thinking={"type": "adaptive"},
            output_config={"effort": cfg.effort},
        )
        if cfg.model_id != "claude-haiku-5-5":  # Haiku has no server-side fallback
            kwargs.update(betas=["server-side-fallback-2026-07-01"], fallbacks="default")
            resp = self.client.beta.messages.create(**kwargs)
        else:
            resp = self.client.messages.create(**kwargs)
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        return Completion(text, resp.model, resp.usage.input_tokens, resp.usage.output_tokens, resp.stop_reason)


class ScriptedProvider:
    """Returns queued responses in order. Records every call for assertions."""

    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def complete(self, cfg: ModelConfig, system: str, messages: list[dict]) -> Completion:
        self.calls.append({"model": cfg.model_id, "system": system, "messages": messages})
        if not self.responses:
            raise RuntimeError("ScriptedProvider ran out of responses")
        text = self.responses.pop(0)
        return Completion(text, cfg.model_id, input_tokens=len(system) // 4, output_tokens=len(text) // 4, stop_reason="end_turn")


class ModelRouter:
    def __init__(self, provider: Provider, models: dict[ModelTier, ModelConfig] | None = None):
        self.provider = provider
        self.models = models or DEFAULT_MODELS

    def config_for(self, tier: ModelTier) -> ModelConfig:
        return self.models[tier]


def default_router() -> ModelRouter:
    if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
        raise RuntimeError("No Anthropic credentials: set ANTHROPIC_API_KEY to run real model calls")
    return ModelRouter(AnthropicProvider())
