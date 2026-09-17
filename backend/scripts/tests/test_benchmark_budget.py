"""Unit tests for the ``benchmark_budget`` CLI.

No live LLM calls and no database: ``select_responder_specs`` / ``load_responder_specs``
operate purely on the frozen ``BENCHMARK_RESPONDERS`` snapshot, argument parsing
is exercised through the real parser, and JSON persistence is verified against a
temporary results directory.
"""
import json
from datetime import datetime
from pathlib import Path

import pytest

from responders.gateway import ResponderSpec
from scripts.benchmark_budget import (
    BENCHMARK_RESPONDERS,
    build_argument_parser,
    load_responder_specs,
    results_path,
    select_responder_specs,
    write_results_json,
)


def names(specs):
    return [(s.provider, s.model) for s in specs]


def assert_snapshot_matches_active_seed():
    # Pins the snapshot to the operating seed (scripts/seed_models.py SEED_MODELS).
    assert names(BENCHMARK_RESPONDERS) == [
        ("groq", "openai/gpt-oss-20b"),
        ("groq", "openai/gpt-oss-120b"),
        ("gemini", "gemini-3.6-flash"),
        ("huggingface", "Qwen/Qwen2.5-72B-Instruct"),
    ]
    assert [s.rpm for s in BENCHMARK_RESPONDERS] == [30, 30, 10, 15]
    assert [s.temperature for s in BENCHMARK_RESPONDERS] == [0.7] * 4
    assert [s.max_tokens for s in BENCHMARK_RESPONDERS] == [1024] * 4


# --------------------------------------------------------------- snapshot


def test_snapshot_pins_the_four_active_responders():
    assert_snapshot_matches_active_seed()


# ------------------------------------------------------- pure selector


def test_no_filters_keeps_every_spec_in_order():
    assert select_responder_specs(BENCHMARK_RESPONDERS) == BENCHMARK_RESPONDERS


def test_provider_filter_keeps_only_that_provider():
    assert names(select_responder_specs(BENCHMARK_RESPONDERS, provider="groq")) == [
        ("groq", "openai/gpt-oss-20b"),
        ("groq", "openai/gpt-oss-120b"),
    ]


def test_model_filter_works_regardless_of_provider():
    assert names(
        select_responder_specs(BENCHMARK_RESPONDERS, model="Qwen/Qwen2.5-72B-Instruct")
    ) == [("huggingface", "Qwen/Qwen2.5-72B-Instruct")]


def test_both_filters_select_the_intersection():
    assert names(
        select_responder_specs(
            BENCHMARK_RESPONDERS,
            provider="groq",
            model="openai/gpt-oss-20b",
        )
    ) == [("groq", "openai/gpt-oss-20b")]


def test_intersection_with_no_match_returns_empty():
    assert (
        select_responder_specs(
            BENCHMARK_RESPONDERS, provider="gemini", model="openai/gpt-oss-20b"
        )
        == ()
    )


def test_unknown_model_returns_empty():
    assert select_responder_specs(BENCHMARK_RESPONDERS, model="does/not-exist") == ()


# ------------------------------------------------------- loader


def test_load_responder_specs_with_no_filters_returns_all_snapshot_specs():
    specs = load_responder_specs()
    assert specs == BENCHMARK_RESPONDERS


def test_load_responder_specs_with_provider_filter():
    specs = load_responder_specs(provider="groq")
    assert names(specs) == [
        ("groq", "openai/gpt-oss-20b"),
        ("groq", "openai/gpt-oss-120b"),
    ]


def test_load_responder_specs_with_model_filter():
    specs = load_responder_specs(model="gemini-3.6-flash")
    assert [(s.provider, s.model, s.rpm) for s in specs] == [
        ("gemini", "gemini-3.6-flash", 10)
    ]


def test_load_responder_specs_accepts_injected_specs():
    injected = (ResponderSpec(provider="groq", model="custom/model", rpm=5),)
    specs = load_responder_specs(specs=injected)
    assert specs == injected


# ---------------------------------------------------------------- CLI arguments


def test_parser_defaults_to_all_responders():
    args = build_argument_parser().parse_args([])
    assert args.provider is None
    assert args.model is None
    assert args.per_prompt is False


def test_parser_accepts_model_alone():
    args = build_argument_parser().parse_args(["--model", "openai/gpt-oss-20b"])
    assert args.provider is None
    assert args.model == "openai/gpt-oss-20b"


def test_parser_accepts_both_provider_and_model():
    args = build_argument_parser().parse_args(
        ["--provider", "groq", "--model", "openai/gpt-oss-20b"]
    )
    assert args.provider == "groq"
    assert args.model == "openai/gpt-oss-20b"


def test_parser_accepts_benchmark_max_tokens_override():
    args = build_argument_parser().parse_args(["--max-tokens", "4096"])
    assert args.max_tokens == 4096


def test_parser_max_tokens_defaults_to_none():
    args = build_argument_parser().parse_args([])
    assert args.max_tokens is None


def test_parser_rejects_unknown_provider():
    with pytest.raises(SystemExit):
        build_argument_parser().parse_args(["--provider", "nowhere"])


# ------------------------------------------------------------------ JSON output


def test_results_path_is_model_scoped_when_model_given(tmp_path):
    path = results_path(
        provider="groq",
        model="openai/gpt-oss-20b",
        now=datetime(2026, 9, 17, 12, 30, 0),
        results_dir=tmp_path,
    )
    assert path == tmp_path / "budget-v1_openai__gpt-oss-20b_20260917_123000.json"


def test_results_path_is_all_scoped_without_filters(tmp_path):
    path = results_path(
        provider=None,
        model=None,
        now=datetime(2026, 9, 17, 12, 30, 0),
        results_dir=tmp_path,
    )
    assert path == tmp_path / "budget-v1_all_20260917_123000.json"


def test_write_results_json_persists_raw_results(tmp_path):
    import asyncio

    from responders.benchmarks.runner import BenchmarkResult

    result = BenchmarkResult(
        prompt_id=1,
        category="opinion",
        expected_complexity="low",
        provider="groq",
        model="openai/gpt-oss-20b",
        status="success",
        latency_ms=123,
        attempts=1,
        prompt_tokens=3,
        completion_tokens=4,
        total_tokens=7,
        finish_reason="stop",
        response_text="the answer",
    )
    target = tmp_path / "run.json"
    written = write_results_json(
        [result],
        provider="groq",
        model="openai/gpt-oss-20b",
        path=target,
        max_tokens=4096,
    )
    assert written == target
    assert target.exists()

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["version"] == "budget-v1"
    assert payload["scope"] == {
        "provider": "groq",
        "model": "openai/gpt-oss-20b",
        "max_tokens": 4096,
    }
    assert payload["run_at"]
    assert payload["results"] == [
        {
            "prompt_id": 1,
            "category": "opinion",
            "expected_complexity": "low",
            "provider": "groq",
            "model": "openai/gpt-oss-20b",
            "status": "success",
            "latency_ms": 123,
            "attempts": 1,
            "prompt_tokens": 3,
            "completion_tokens": 4,
            "total_tokens": 7,
            "finish_reason": "stop",
            "response_text": "the answer",
            "error_message": None,
            "thoughts_tokens": None,
            "truncated": False,
        }
    ]