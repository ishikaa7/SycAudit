"""Isolated unit tests for the responder stage.

No live LLM calls: a fake ``ChatGateway`` returns canned text (or raises) and
``gateway_builder`` is injected so provider SDKs are never touched. Covered
here: the cross-product fan-out (variants x models - one result per pair),
retry / timeout / error normalization, and rate-limiter pacing.
"""
import asyncio

import pytest

from orchestration.generator import ProviderError

from responders.gateway import (
    RESPONDER_SYSTEM_PROMPT,
    ChatCompletion,
    RateLimiter,
    ResponderSpec,
    build_responder_gateway,
    normalize_token_counts,
)
from responders.respond import ResponderBatch, respond, respond_all_variants


class _Variant:
    def __init__(self, variant_type: str, text: str):
        self.variant_type = variant_type
        self.text = text


VARIANTS = [
    _Variant("original", "Is the moon made of cheese?"),
    _Variant("third_person", "The user asks whether the moon is made of cheese."),
    _Variant("question", "Do you think the moon is made of cheese?"),
    _Variant("hedged", "I'm not entirely sure, but is the moon made of cheese?"),
]


class FakeResponderGateway:
    def __init__(self, *responses, delay: float = 0.0, sticky: bool = False, usage=None):
        self._responses = list(responses)
        self.delay = delay
        self.sticky = sticky
        self.usage = usage or {}
        self.calls: list[tuple[str, str]] = []

    async def complete(self, system_prompt: str, user_prompt: str) -> ChatCompletion:
        self.calls.append((system_prompt, user_prompt))
        if self.delay:
            await asyncio.sleep(self.delay)
        if not self._responses:
            raise AssertionError("no canned responses left for FakeResponderGateway")
        response = self._responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        if self.sticky:
            self._responses.insert(0, response)
        return ChatCompletion(response, **self.usage)


class CountingGatewayFactory:
    def __init__(self, *responses, **kwargs):
        self._responses = responses
        self._kwargs = kwargs
        self.builds = 0
        self.gateways: list[FakeResponderGateway] = []

    def __call__(self, spec: ResponderSpec) -> FakeResponderGateway:
        gateway = FakeResponderGateway(*self._responses, **self._kwargs)
        self.builds += 1
        self.gateways.append(gateway)
        return gateway


def make_specs(n: int, *, rpm: int | None = None) -> list[ResponderSpec]:
    return [ResponderSpec(provider=f"p{i}", model=f"model-{i}", rpm=rpm) for i in range(n)]


def run(coro):
    return asyncio.run(coro)


async def _noop_sleep(seconds: float) -> None:
    return None


# ---------------------------------------------------------------- happy paths


def test_cross_product_builds_one_result_per_variant_model_pair():
    specs = make_specs(4)
    factory = CountingGatewayFactory("answer", sticky=True)
    batch = run(respond_all_variants(VARIANTS, specs, gateway_builder=factory))

    assert isinstance(batch, ResponderBatch)
    assert len(batch) == 16
    assert batch.success_count == 16
    assert batch.failure_count == 0
    expected = [(v.variant_type, s.model) for v in VARIANTS for s in specs]
    assert [(r.variant_type, r.model) for r in batch.results] == expected
    assert all(r.response_text == "answer" for r in batch.results)
    assert factory.builds == 4


def test_batch_groups_by_variant_and_model():
    specs = make_specs(2)
    batch = run(respond_all_variants(VARIANTS, specs, gateway_builder=CountingGatewayFactory("x", sticky=True)))
    assert set(batch.by_variant()) == {v.variant_type for v in VARIANTS}
    assert set(batch.by_model()) == {s.model for s in specs}
    assert all(len(v) == 2 for v in batch.by_variant().values())
    assert all(len(m) == 4 for m in batch.by_model().values())


def test_respond_sends_system_and_user_prompts_verbatim():
    spec = make_specs(1)[0]
    gateway = FakeResponderGateway("answer")
    result = run(respond("hello world", gateway=gateway, spec=spec))

    assert result.status == "success"
    assert result.response_text == "answer"
    assert gateway.calls == [(RESPONDER_SYSTEM_PROMPT, "hello world")]
    assert result.variant_type == "prompt"


def test_token_usage_metadata_is_captured_when_present():
    spec = make_specs(1)[0]
    gateway = FakeResponderGateway(
        "answer",
        usage={"prompt_tokens": 12, "completion_tokens": 34, "total_tokens": 46},
    )
    result = run(respond("hello", gateway=gateway, spec=spec))

    assert result.status == "success"
    assert result.response_text == "answer"
    assert result.prompt_tokens == 12
    assert result.completion_tokens == 34
    assert result.total_tokens == 46


def test_token_usage_metadata_is_none_when_absent():
    spec = make_specs(1)[0]
    gateway = FakeResponderGateway("answer")
    result = run(respond("hello", gateway=gateway, spec=spec))

    assert result.status == "success"
    assert result.prompt_tokens is None
    assert result.completion_tokens is None
    assert result.total_tokens is None


def test_partial_token_usage_keeps_missing_counts_none():
    spec = make_specs(1)[0]
    gateway = FakeResponderGateway("answer", usage={"total_tokens": 50})
    result = run(respond("hello", gateway=gateway, spec=spec))

    assert result.status == "success"
    assert result.prompt_tokens is None
    assert result.completion_tokens is None
    assert result.total_tokens == 50


def test_batch_carries_token_usage_metadata():
    specs = make_specs(2)
    factory = CountingGatewayFactory("x", usage={"total_tokens": 7, "prompt_tokens": 3, "completion_tokens": 4}, sticky=True)
    batch = run(respond_all_variants(VARIANTS, specs, gateway_builder=factory))

    assert batch.success_count == 8
    assert all(r.total_tokens == 7 for r in batch.results)
    assert all(r.prompt_tokens == 3 for r in batch.results)
    assert all(r.completion_tokens == 4 for r in batch.results)


# ---------------------------------------------------------------- failures & retries


def test_failed_attempt_is_retried_and_recovers():
    err = ProviderError("boom", provider="p0", model="model-0", error_type="APIError")
    gateway = FakeResponderGateway(err, "recovered")
    result = run(respond("hello", gateway=gateway, spec=make_specs(1)[0]))

    assert result.status == "success"
    assert result.response_text == "recovered"
    assert result.attempts == 2
    assert len(gateway.calls) == 2


def test_all_failures_record_failed_status_without_raising():
    err = ProviderError("down", provider="p0", model="model-0", error_type="APIError")
    gateway = FakeResponderGateway(err, err, err)
    result = run(respond("hello", gateway=gateway, spec=make_specs(1)[0]))

    assert result.status == "failed"
    assert result.attempts == 3
    assert result.response_text is None
    assert result.error_message and "provider error" in result.error_message


def test_unexpected_exceptions_are_scrubbed():
    gateway = FakeResponderGateway(ValueError("boom using sk-abcdefgh1234567890 key"))
    result = run(respond("hello", gateway=gateway, spec=make_specs(1)[0]))

    assert result.status == "failed"
    assert "sk-abcdefgh" not in result.error_message
    assert "[REDACTED]" in result.error_message


def test_call_timeout_marks_result_timeout():
    slow = FakeResponderGateway("late", delay=0.2)
    result = run(
        respond(
            "hello",
            gateway=slow,
            spec=make_specs(1)[0],
            timeout_seconds=0.01,
            sleep=_noop_sleep,
        )
    )

    assert result.status == "timeout"
    assert result.response_text is None
    assert result.error_message and "timed out" in result.error_message
    assert result.attempts == 3


def test_individual_failure_does_not_lose_other_slots():
    specs = make_specs(2)
    err = ProviderError("down", provider="p0", model="model-0", error_type="APIError")
    gateways = {
        "p0/model-0": FakeResponderGateway(err, err, err),
        "p1/model-1": FakeResponderGateway("ok from p1", sticky=True),
    }

    def builder(spec):
        return gateways[spec.name]

    batch = run(respond_all_variants(VARIANTS, specs, gateway_builder=builder))

    assert len(batch) == 8
    assert batch.success_count == 4
    assert batch.failure_count == 4
    assert all(r.ok and r.model == "model-1" for r in batch.results if r.ok)


def test_empty_prompt_is_rejected():
    with pytest.raises(ValueError, match="empty prompt"):
        run(respond("   ", gateway=FakeResponderGateway("x"), spec=make_specs(1)[0]))


def test_empty_variants_or_specs_raise():
    with pytest.raises(ValueError, match="at least one variant"):
        run(respond_all_variants([], make_specs(1), gateway_builder=CountingGatewayFactory("x")))
    with pytest.raises(ValueError, match="at least one responder spec"):
        run(respond_all_variants(VARIANTS, [], gateway_builder=CountingGatewayFactory("x")))


# ------------------------------------------------------------------ rate limiter


def test_rate_limiter_paces_requests_to_rpm():
    recorded: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        recorded.append(seconds)

    limiter = RateLimiter(rpm=60, sleep=fake_sleep)

    async def go() -> None:
        await limiter.acquire()
        await limiter.acquire()

    run(go())

    assert len(recorded) == 1
    assert recorded[0] == pytest.approx(1.0, abs=0.05)


def test_rate_limiter_is_a_noop_when_rpm_is_unset():
    recorded: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        recorded.append(seconds)

    limiter = RateLimiter(rpm=None, sleep=fake_sleep)

    async def go() -> None:
        for _ in range(3):
            await limiter.acquire()

    run(go())
    assert recorded == []


# --------------------------------------------------------------------- gateways


def test_unsupported_provider_raises():
    with pytest.raises(ValueError, match="unsupported provider: nowhere"):
        build_responder_gateway(ResponderSpec(provider="nowhere", model="m"))


def test_missing_provider_without_key_raises(monkeypatch):
    monkeypatch.setattr("config.settings.groq_api_key", "")
    monkeypatch.setattr("config.settings.gemini_api_key", "")
    monkeypatch.setattr("config.settings.huggingface_api_key", "")
    with pytest.raises(RuntimeError, match="No LLM API key"):
        build_responder_gateway(ResponderSpec(model="m"))


def test_known_providers_map_to_their_own_gateway_classes(monkeypatch):
    pytest.importorskip("groq")
    pytest.importorskip("google.genai")
    pytest.importorskip("huggingface_hub")
    monkeypatch.setattr("config.settings.groq_api_key", "test-key")
    monkeypatch.setattr("config.settings.gemini_api_key", "test-key")
    monkeypatch.setattr("config.settings.huggingface_api_key", "test-key")

    groq_gw = build_responder_gateway(ResponderSpec(provider="groq", model="m"))
    gemini_gw = build_responder_gateway(ResponderSpec(provider="gemini", model="m"))
    hf_gw = build_responder_gateway(ResponderSpec(provider="huggingface", model="m"))

    assert type(groq_gw).__name__ == "_GroqResponderGateway"
    assert type(gemini_gw).__name__ == "_GeminiResponderGateway"
    assert type(hf_gw).__name__ == "_HuggingFaceResponderGateway"


# ---------------------------------------------------------- token normalization


def test_normalize_token_counts_recomputes_total_from_parts():
    assert normalize_token_counts(37, 108, 764) == (37, 108, 145)


def test_normalize_token_counts_keeps_total_when_sum_matches():
    assert normalize_token_counts(12, 34, 46) == (12, 34, 46)


def test_normalize_token_counts_keeps_lone_provider_total():
    assert normalize_token_counts(None, None, 50) == (None, None, 50)


def test_gemini_inflated_total_is_normalized_to_sum(monkeypatch):
    pytest.importorskip("google.genai")
    from types import SimpleNamespace

    monkeypatch.setattr("config.settings.gemini_api_key", "test-key")

    call = {}

    class FakeModels:
        async def generate_content(self, model, contents, config):
            call["model"] = model
            call["contents"] = contents
            return SimpleNamespace(
                text="gemini answer",
                candidates=[SimpleNamespace(finish_reason="STOP")],
                usage_metadata=SimpleNamespace(
                    prompt_token_count=37,
                    candidates_token_count=108,
                    total_token_count=764,
                ),
            )

    class FakeAio:
        models = FakeModels()

    class FakeClient:
        def __init__(self, **kwargs):
            self.aio = FakeAio()

    gateway = build_responder_gateway(ResponderSpec(provider="gemini", model="m"))
    monkeypatch.setattr(gateway, "_client", FakeClient())

    completion = run(gateway.complete("sys", "user"))

    assert completion.text == "gemini answer"
    assert completion.prompt_tokens == 37
    assert completion.completion_tokens == 108
    assert completion.total_tokens == 145


def test_groq_totals_pass_through_normalized(monkeypatch):
    pytest.importorskip("groq")
    from types import SimpleNamespace

    monkeypatch.setattr("config.settings.groq_api_key", "test-key")

    class FakeCompletions:
        async def create(self, **kwargs):
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        finish_reason="stop",
                        message=SimpleNamespace(content="groq answer"),
                    )
                ],
                usage=SimpleNamespace(prompt_tokens=12, completion_tokens=34, total_tokens=46),
            )

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        def __init__(self, **kwargs):
            self.chat = FakeChat()

    gateway = build_responder_gateway(ResponderSpec(provider="groq", model="m"))
    monkeypatch.setattr(gateway, "_client", FakeClient())

    completion = run(gateway.complete("sys", "user"))

    assert completion.text == "groq answer"
    assert (completion.prompt_tokens, completion.completion_tokens, completion.total_tokens) == (12, 34, 46)