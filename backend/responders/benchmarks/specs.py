"""Frozen snapshot of the active responder set for ``budget-v1`` calibration.

Mirrors ``scripts/seed_models.SEED_MODELS``, which is the operational source of
the active responder configuration. Vendoring the specs here keeps the
benchmark runnable without a live PostgreSQL database and deterministic like the
frozen prompts dataset; it changes nothing about how responders are called (the
same ``build_responder_gateway`` path is used). Keep this in sync with
``SEED_MODELS`` whenever the responder set changes.
"""
from __future__ import annotations

from responders.gateway import ResponderSpec

# Exactly the currently active responder configuration:
#   groq / openai/gpt-oss-20b                 (rpm 30)
#   groq / openai/gpt-oss-120b                (rpm 30)
#   gemini / gemini-3.6-flash                 (rpm 10)
#   huggingface / Qwen/Qwen2.5-72B-Instruct   (rpm 15)
# temperature/max_tokens use the ResponderSpec defaults (0.7 / 1024), matching
# the llm_models column defaults those rows are seeded with.
BENCHMARK_RESPONDERS: tuple[ResponderSpec, ...] = (
    ResponderSpec(provider="groq", model="openai/gpt-oss-20b", rpm=30),
    ResponderSpec(provider="groq", model="openai/gpt-oss-120b", rpm=30),
    ResponderSpec(provider="gemini", model="gemini-3.6-flash", rpm=10),
    ResponderSpec(provider="huggingface", model="Qwen/Qwen2.5-72B-Instruct", rpm=15),
)