"""Config-level tests for the seeded LLM model set.

Locks the 4x4 responder requirement to concrete configuration: the seed must
contain exactly four active responder rows, none of the retired models, and the
variation generator must agree on the gemini model so generation and the
responder stage use a live model.
"""
from orchestration.generator import DEFAULT_MODELS
from scripts.seed_models import RETIRED_MODELS, SEED_MODELS


def test_seed_has_exactly_four_responder_models():
    assert len(SEED_MODELS) == 4
    names = {(m["provider"], m["model_name"]) for m in SEED_MODELS}
    assert names == {
        ("groq", "openai/gpt-oss-20b"),
        ("groq", "openai/gpt-oss-120b"),
        ("gemini", "gemini-3.6-flash"),
        ("huggingface", "Qwen/Qwen2.5-72B-Instruct"),
    }


def test_retired_models_are_not_seeded_or_recreated():
    seed_names = {(m["provider"], m["model_name"]) for m in SEED_MODELS}
    assert ("gemini", "gemini-2.5-flash") not in seed_names
    assert ("huggingface", "Qwen/Qwen2.5-7B-Instruct") not in seed_names
    assert ("gemini", "gemini-2.5-flash") in RETIRED_MODELS
    assert ("huggingface", "Qwen/Qwen2.5-7B-Instruct") in RETIRED_MODELS


def test_generator_and_responder_share_current_gemini_model():
    assert DEFAULT_MODELS["gemini"] == "gemini-3.6-flash"
    assert ("gemini", DEFAULT_MODELS["gemini"]) in {(m["provider"], m["model_name"]) for m in SEED_MODELS}


def test_every_seeded_responder_provider_is_supported():
    supported = {"groq", "gemini", "huggingface"}
    assert all(m["provider"] in supported for m in SEED_MODELS)