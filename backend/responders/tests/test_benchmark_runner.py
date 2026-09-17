"""Unit tests for the ``budget-v1`` calibration runner and report.

No live LLM calls: a fake gateway returns canned ChatCompletions (optionally
with tokens and a finish reason) and is injected via ``gateway_builder`` as the
responder stage's unit tests do. The DB-backed spec loader in
``scripts/benchmark_budget.py`` is intentionally NOT exercised here.
"""
import asyncio

import pytest

from responders.benchmarks import (
    BENCHMARK_PROMPTS,
    BENCHMARK_VERSION,
    BenchmarkPrompt,
    format_report,
    run_benchmark,
    summarize,
)
from responders.benchmarks.runner import _percentile
from responders.gateway import ChatCompletion, ResponderSpec


class FakeBenchmarkGateway:
    def __init__(self, text: str = "answer", usage: dict | None = None):
        self.text = text
        self.usage = usage or {}
        self.spec: ResponderSpec | None = None
        self.calls: list[str] = []

    async def complete(self, system_prompt: str, user_prompt: str) -> ChatCompletion:
        self.calls.append(user_prompt)
        return ChatCompletion(self.text, **self.usage)


class RecordingBuilder:
    def __init__(self, text: str = "answer", usage: dict | None = None):
        self.text = text
        self.usage = usage or {}
        self.gateways: list[FakeBenchmarkGateway] = []

    def __call__(self, spec: ResponderSpec) -> FakeBenchmarkGateway:
        gateway = FakeBenchmarkGateway(self.text, self.usage)
        gateway.spec = spec
        self.gateways.append(gateway)
        return gateway


def make_specs(n: int) -> list[ResponderSpec]:
    return [
        ResponderSpec(provider=f"p{i}", model=f"model-{i}", rpm=None) for i in range(n)
    ]


def run(coro):
    return asyncio.run(coro)


def test_run_benchmark_returns_one_result_per_prompt_spec_pair():
    builder = RecordingBuilder()
    results = run(run_benchmark(specs=make_specs(2), gateway_builder=builder))

    assert len(results) == len(BENCHMARK_PROMPTS) * 2
    assert all(r.status == "success" for r in results)
    assert {r.prompt_id for r in results} == {p.prompt_id for p in BENCHMARK_PROMPTS}
    assert {(r.provider, r.model) for r in results} == {("p0", "model-0"), ("p1", "model-1")}


def test_run_benchmark_clones_specs_with_keep_truncated_opt_in():
    builder = RecordingBuilder()
    run(run_benchmark(specs=make_specs(1), gateway_builder=builder))

    assert len(builder.gateways) == 1
    assert builder.gateways[0].spec.keep_truncated is True
    assert len(builder.gateways[0].calls) == len(BENCHMARK_PROMPTS)


def test_run_benchmark_applies_benchmark_only_max_tokens_override():
    builder = RecordingBuilder()
    run(run_benchmark(specs=make_specs(1), gateway_builder=builder, max_tokens=4096))

    assert len(builder.gateways) == 1
    spec = builder.gateways[0].spec
    assert spec.keep_truncated is True
    assert spec.max_tokens == 4096
    # the caller's spec is untouched
    original = make_specs(1)[0]
    assert original.max_tokens == 1024


def test_run_benchmark_without_override_keeps_configured_ceiling():
    builder = RecordingBuilder()
    run(run_benchmark(specs=[ResponderSpec(provider="p0", model="model-0", max_tokens=2048)], gateway_builder=builder))
    assert builder.gateways[0].spec.max_tokens == 2048


def test_run_benchmark_rejects_non_positive_max_tokens():
    with pytest.raises(ValueError):
        run(run_benchmark(specs=make_specs(1), gateway_builder=RecordingBuilder(), max_tokens=0))


def test_results_preserve_response_text_and_error_message():
    from orchestration.generator import ProviderError

    class EchoGateway:
        async def complete(self, system_prompt: str, user_prompt: str) -> ChatCompletion:
            return ChatCompletion("the answer text", finish_reason="stop")

    results = run(
        run_benchmark(
            prompts=[BENCHMARK_PROMPTS[0]],
            specs=[ResponderSpec(provider="p0", model="model-0")],
            gateway_builder=lambda spec: EchoGateway(),
        )
    )
    assert results[0].response_text == "the answer text"

    class BoomGateway:
        async def complete(self, system_prompt: str, user_prompt: str) -> ChatCompletion:
            raise ProviderError("boom", provider="p0", model="model-0", error_type="APIError")

    failed = run(
        run_benchmark(
            prompts=[BENCHMARK_PROMPTS[0]],
            specs=[ResponderSpec(provider="p0", model="model-0")],
            gateway_builder=lambda spec: BoomGateway(),
        )
    )
    assert failed[0].status == "failed"
    assert "boom" in (failed[0].error_message or "")


def test_results_carry_prompt_metadata_and_provider_usage():
    builder = RecordingBuilder(
        usage={"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7, "finish_reason": "stop"}
    )
    results = run(run_benchmark(specs=make_specs(1), gateway_builder=builder))
    sample = results[0]

    assert (sample.prompt_id, sample.category, sample.expected_complexity) == (
        BENCHMARK_PROMPTS[0].prompt_id,
        BENCHMARK_PROMPTS[0].category,
        BENCHMARK_PROMPTS[0].expected_complexity,
    )
    assert sample.completion_tokens == 4
    assert sample.finish_reason == "stop"
    assert sample.ok
    assert sample.truncated is False


def test_results_preserve_thoughts_tokens():
    builder = RecordingBuilder(
        usage={
            "completion_tokens": 963,
            "finish_reason": "max_tokens",
            "thoughts_tokens": 1085,
        }
    )
    results = run(run_benchmark(specs=make_specs(1), gateway_builder=builder))
    sample = results[0]

    assert sample.completion_tokens == 963
    assert sample.thoughts_tokens == 1085
    assert sample.truncated is True


def test_truncated_and_finished_classification():
    assert run_benchmark_and_flag("length") is True
    assert run_benchmark_and_flag("max_tokens") is True
    assert run_benchmark_and_flag("stop") is False


def run_benchmark_and_flag(reason: str) -> bool:
    builder = RecordingBuilder(usage={"completion_tokens": 5, "finish_reason": reason})
    results = run(run_benchmark(specs=make_specs(1), gateway_builder=builder))
    return results[0].truncated


def test_missing_finish_reason_counts_as_not_reported():
    builder = RecordingBuilder(usage={"completion_tokens": 5})
    results = run(run_benchmark(specs=make_specs(1), gateway_builder=builder))
    assert results[0].finish_reason is None
    assert results[0].truncated is False


def test_summary_computes_per_model_statistics():
    builder = RecordingBuilder(
        usage={"completion_tokens": 4, "finish_reason": "stop"}
    )
    results = run(run_benchmark(specs=make_specs(1), gateway_builder=builder))

    summary = summarize(results, version=BENCHMARK_VERSION)
    assert summary.version == BENCHMARK_VERSION
    assert len(summary.models) == 1
    model = summary.models[0]
    assert model.total == len(results)
    assert model.succeeded == len(results)
    assert model.completion_tokens_median == 4
    assert model.completion_tokens_p90 == 4
    assert model.completion_tokens_max == 4
    assert model.truncated == 0
    assert model.truncation_rate == 0.0


def test_summary_tracks_truncation_rate():
    truncated_usage = {"completion_tokens": 5, "finish_reason": "max_tokens"}
    done_usage = {"completion_tokens": 3, "finish_reason": "stop"}

    class AlternateBuilder:
        def __init__(self):
            self.gateways: list[FakeBenchmarkGateway] = []

        def __call__(self, spec: ResponderSpec) -> FakeBenchmarkGateway:
            gateway = FakeBenchmarkGateway()
            gateway.usage = truncated_usage if len(self.gateways) == 0 else done_usage
            self.gateways.append(gateway)
            return gateway

    results = run(run_benchmark(specs=make_specs(2), gateway_builder=AlternateBuilder()))
    model = summarize(results).models[0]
    assert model.truncated == len(BENCHMARK_PROMPTS)
    assert model.truncation_rate == 1.0


def test_failed_calls_are_counted_not_raised():
    class BoomGateway:
        async def complete(self, system_prompt: str, user_prompt: str) -> ChatCompletion:
            raise RuntimeError("boom")

    def builder(spec: ResponderSpec) -> BoomGateway:
        return BoomGateway()

    results = run(run_benchmark(specs=make_specs(1), gateway_builder=builder))
    assert len(results) == len(BENCHMARK_PROMPTS)
    assert all(r.status == "failed" for r in results)
    summary = summarize(results).models[0]
    assert summary.failed == len(BENCHMARK_PROMPTS)
    assert summary.succeeded == 0


def test_format_report_renders_a_model_row_per_line():
    builder = RecordingBuilder(
        usage={"completion_tokens": 4, "finish_reason": "stop"}
    )
    results = run(run_benchmark(specs=make_specs(2), gateway_builder=builder))
    report = format_report(summarize(results, version=BENCHMARK_VERSION))

    assert "p0/model-0" in report
    assert "p1/model-1" in report
    assert report.count("\n") == 2 + 1 + 2  # title+results, blank, header, 2 model rows


def test_run_benchmark_requires_prompts_and_specs():
    with pytest.raises(ValueError):
        run(run_benchmark(prompts=[], specs=make_specs(1), gateway_builder=RecordingBuilder()))
    with pytest.raises(ValueError):
        run(run_benchmark(specs=[], gateway_builder=RecordingBuilder()))


def test_percentile_edge_cases():
    assert _percentile([7], 0.9) == 7
    assert _percentile([1, 2, 3, 4], 0.5) == 2
    assert _percentile([1, 2, 3, 4], 0.0) == 1
    assert _percentile([1, 2, 3, 4], 1.0) == 4
    with pytest.raises(ValueError):
        _percentile([], 0.5)


def test_prompt_id_pairs_map_through_duck_typed_inputs():
    prompts = [BenchmarkPrompt(1, "opinion", "low", "short?")]
    builder = RecordingBuilder()
    results = run(run_benchmark(prompts=prompts, specs=make_specs(1), gateway_builder=builder))
    assert len(results) == 1
    assert results[0].prompt_id == 1