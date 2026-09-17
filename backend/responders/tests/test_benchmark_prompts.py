"""Tests for the frozen ``budget-v1`` responder calibration prompt dataset.

The dataset must stay deterministic: exactly the hand-authored 20 prompts, in
stable order, unaffected by anything external.
"""
import pytest

from responders.benchmarks.prompts import (
    BENCHMARK_PROMPTS,
    BENCHMARK_VERSION,
    BenchmarkPrompt,
)


def test_benchmark_version_is_budget_v1() -> None:
    assert BENCHMARK_VERSION == "budget-v1"


def test_exactly_twenty_prompts() -> None:
    assert len(BENCHMARK_PROMPTS) == 20


def test_prompt_ids_are_unique_and_cover_1_to_20() -> None:
    ids = [p.prompt_id for p in BENCHMARK_PROMPTS]
    assert len(set(ids)) == len(ids)
    assert sorted(ids) == list(range(1, 21))


def test_every_prompt_is_a_frozen_benchmark_prompt() -> None:
    for prompt in BENCHMARK_PROMPTS:
        assert isinstance(prompt, BenchmarkPrompt)
        with pytest.raises(Exception):
            prompt.text = "mutated"  # frozen: assignment must fail


def test_every_prompt_has_category_complexity_and_non_empty_text() -> None:
    for prompt in BENCHMARK_PROMPTS:
        assert prompt.prompt_id >= 1
        assert prompt.category.strip()
        assert prompt.expected_complexity.strip()
        assert prompt.text.strip()


def test_prompt_texts_have_not_been_duplicated() -> None:
    texts = [p.text for p in BENCHMARK_PROMPTS]
    assert len(set(texts)) == len(texts)