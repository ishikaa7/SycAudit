"""Isolated unit tests for the prompt-variation pipeline.

No live LLM calls: the chat gateway is faked and returns canned JSON strings.
The fake pops responses in order, so tests can script "bad then good" for the
retry cases that the pipeline must recover from.
"""
import asyncio
import json

import pytest

from orchestration.generator import GenerationSpec
from orchestration.variants import GenerateVariantsError, Variant, generate_variants
from orchestration.validator import ValidationResult, validate_variants

SPEC = GenerationSpec(model="test-model", provider="groq")


class FakeGateway:
    def __init__(self, *responses: str):
        self._responses: list[str] = list(responses)
        self.calls: list[tuple[str, str]] = []

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        if not self._responses:
            raise AssertionError("no canned responses left for FakeGateway")
        return self._responses.pop(0)


def make_json(original, third_person=None, question=None, hedged=None, analysis="structural analysis"):
    variants = []
    for variant_type, text in (
        ("original", original),
        ("third_person", third_person),
        ("question", question),
        ("hedged", hedged),
    ):
        variants.append({"variant_type": variant_type, "text": text if text is not None else original})
    return json.dumps({"analysis": analysis, "variants": variants})


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------- happy paths


def test_basic_generation_produces_four_valid_variants():
    source = "I think the sky is blue."
    response = make_json(
        source,
        third_person="The user thinks the sky is blue.",
        question="Do you think the sky is blue?",
        hedged="I'm not entirely sure, but I think the sky is blue.",
    )
    result = run(generate_variants(source, gateway=FakeGateway(response), generation=SPEC))

    assert [v.variant_type for v in result.variants] == ["original", "third_person", "question", "hedged"]
    assert result.variants[0].text == source
    assert result.validation.valid
    assert result.metadata.attempts == 1
    assert result.metadata.prompt_version == SPEC.prompt_version
    assert result.metadata.model == "test-model"


def test_existing_question_prompt_is_not_rewritten():
    source = "Is the sky blue?"
    response = make_json(
        source,
        third_person="Is the sky blue?",
        question="Is the sky blue?",
        hedged="I'm not entirely sure, but is the sky blue?",
    )
    result = run(generate_variants(source, gateway=FakeGateway(response), generation=SPEC))
    assert result.validation.valid
    assert result.variants[2].text == source


def test_proper_nouns_are_preserved():
    source = "I think Alice visited London and met John last year."
    response = make_json(
        source,
        third_person="The user thinks Alice visited London and met John last year.",
        question="Do you think Alice visited London and met John last year?",
        hedged="I'm not entirely sure, but I think Alice visited London and met John last year.",
    )
    result = run(generate_variants(source, gateway=FakeGateway(response), generation=SPEC))
    assert result.validation.valid


def test_numbers_and_dates_are_preserved():
    source = "I believe Tokyo's population was 37 million on March 5, 2024."
    response = make_json(
        source,
        third_person="The user believes Tokyo's population was 37 million on March 5, 2024.",
        question="Do you believe Tokyo's population was 37 million on March 5, 2024?",
        hedged="I'm not entirely sure, but I believe Tokyo's population was 37 million on March 5, 2024.",
    )
    result = run(generate_variants(source, gateway=FakeGateway(response), generation=SPEC))
    assert result.validation.valid


def test_multiple_sentences_are_handled():
    source = "I think the sky is blue. The economy is complicated."
    response = make_json(
        source,
        third_person="The user thinks the sky is blue. The economy is complicated.",
        question="Do you think the sky is blue? Is the economy complicated?",
        hedged="I'm not entirely sure, but I think the sky is blue. The economy is complicated.",
    )
    result = run(generate_variants(source, gateway=FakeGateway(response), generation=SPEC))
    assert result.validation.valid


def test_no_first_person_baseline():
    source = "What is the capital of France?"
    response = make_json(
        source,
        third_person="What is the capital of France?",
        question="What is the capital of France?",
        hedged="I'm not entirely sure, but what is the capital of France?",
    )
    result = run(generate_variants(source, gateway=FakeGateway(response), generation=SPEC))
    assert result.validation.valid


def test_already_hedged_source_does_not_stack_hedge():
    source = "I'm not sure, but I think the sky is blue."
    response = make_json(
        source,
        third_person="The user is not sure, but the user thinks the sky is blue.",
        question="The user is not sure, but does the user think the sky is blue?",
        hedged="I'm not sure, but I think the sky is blue.",
    )
    result = run(generate_variants(source, gateway=FakeGateway(response), generation=SPEC))
    assert result.validation.valid


def test_quoted_text_is_preserved():
    source = 'She said, "I think we should go."'
    response = make_json(
        source,
        third_person='She said, "I think we should go."',
        question='Did she say, "I think we should go"?',
        hedged='I\'m not entirely sure, but she said, "I think we should go.".',
    )
    result = run(generate_variants(source, gateway=FakeGateway(response), generation=SPEC))
    assert result.validation.valid


def test_non_ascii_prompt():
    source = "Ich weiß, dass der Himmel blau ist."
    response = make_json(
        source,
        third_person="Der Nutzer weiß, dass der Himmel blau ist.",
        question="Weiß der Nutzer, ob der Himmel blau ist?",
        hedged="Ich weiß nicht, ob der Himmel blau ist.",
    )
    result = run(generate_variants(source, gateway=FakeGateway(response), generation=SPEC))
    assert result.validation.valid


def test_formula_prompt_preserves_numbers():
    source = "Evaluate the expression sqrt(a^2 + b^2) after setting a=3 and b=4."
    response = make_json(
        source,
        third_person="Evaluate the expression sqrt(a^2 + b^2) after setting a=3 and b=4.",
        question="Can you evaluate the expression sqrt(a^2 + b^2) after setting a=3 and b=4?",
        hedged="I'm not entirely sure, but evaluate the expression sqrt(a^2 + b^2) after setting a=3 and b=4.",
    )
    result = run(generate_variants(source, gateway=FakeGateway(response), generation=SPEC))
    assert result.validation.valid


# ---------------------------------------------------------------- failures & retries


def test_malformed_output_is_recovered_by_retry():
    source = "I think the sky is blue."
    good = make_json(
        source,
        third_person="The user thinks the sky is blue.",
        question="Do you think the sky is blue?",
        hedged="I'm not entirely sure, but I think the sky is blue.",
    )
    result = run(generate_variants(source, gateway=FakeGateway("not json at all", good), generation=SPEC))
    assert result.validation.valid
    assert result.metadata.attempts == 2


def test_validation_failure_is_recovered_by_regeneration():
    source = "I think the sky is blue."
    bad = make_json(
        source,
        third_person="I think the sky is blue.",
        question="Do you think the sky is blue?",
        hedged="I'm not entirely sure, but I think the sky is blue.",
    )
    good = make_json(
        source,
        third_person="The user thinks the sky is blue.",
        question="Do you think the sky is blue?",
        hedged="I'm not entirely sure, but I think the sky is blue.",
    )
    result = run(generate_variants(source, gateway=FakeGateway(bad, good), generation=SPEC))
    assert result.validation.valid
    assert result.metadata.attempts == 2


def test_three_consecutive_failures_raise_generation_error():
    source = "I think the answer is 42."
    fail_json = "not json"
    no_question = make_json(
        source,
        third_person="The user thinks the answer is 42.",
        question="The user thinks the answer is 42.",
        hedged="I'm not entirely sure, but I think the answer is 42.",
    )
    no_numbers = make_json(
        source,
        third_person="The user thinks the answer is blue.",
        question="Do you think the answer is blue?",
        hedged="I'm not entirely sure, but I think the answer is blue.",
    )

    with pytest.raises(GenerateVariantsError) as exc_info:
        run(generate_variants(source, gateway=FakeGateway(fail_json, no_question, no_numbers), generation=SPEC))

    assert exc_info.value.attempts == 3
    assert len(exc_info.value.failures) == 3


# ------------------------------------------------------------ validator in isolation


def test_validator_flags_duplicate_and_missing_types():
    candidates = [
        Variant("original", "I think the sky is blue."),
        Variant("original", "I think the sky is blue."),
        Variant("question", "Do you think the sky is blue?"),
    ]
    result = validate_variants("I think the sky is blue.", candidates)
    assert not result.valid
    codes = {i.code for i in result.issues}
    assert "DUPLICATE_VARIANT_TYPE" in codes
    assert "MISSING_VARIANT_TYPE" in codes


def test_validator_flags_original_mismatch():
    candidates = [
        Variant("original", "I think the sky is green."),
        Variant("third_person", "The user thinks the sky is blue."),
        Variant("question", "Do you think the sky is blue?"),
        Variant("hedged", "I'm not entirely sure, but I think the sky is blue."),
    ]
    result = validate_variants("I think the sky is blue.", candidates)
    assert not result.valid
    assert any(i.code == "ORIGINAL_MISMATCH" for i in result.issues)


def test_validator_flags_dropped_number():
    candidates = [
        Variant("original", "I think 42 is the answer."),
        Variant("third_person", "The user thinks something is the answer."),
        Variant("question", "Do you think 42 is the answer?"),
        Variant("hedged", "I'm not entirely sure, but I think 42 is the answer."),
    ]
    result = validate_variants("I think 42 is the answer.", candidates)
    assert not result.valid
    assert any(i.code == "NUMBER_DROPPED" for i in result.issues)


def test_validator_returns_useful_reasons():
    candidates = [
        Variant("original", "I think the sky is blue."),
        Variant("third_person", "I think we should not go."),
        Variant("question", "Do you think the sky is blue?"),
        Variant("hedged", "I'm not entirely sure, but I think the sky is blue."),
    ]
    result = validate_variants("I think the sky is blue.", candidates)
    assert not result.valid
    assert any(i.code == "FIRST_PERSON_UNCONVERTED" for i in result.issues)
    assert result.summary.startswith("invalid")


def test_validator_accepts_clean_variants():
    candidates = [
        Variant("original", "I think the sky is blue."),
        Variant("third_person", "The user thinks the sky is blue."),
        Variant("question", "Do you think the sky is blue?"),
        Variant("hedged", "I'm not entirely sure, but I think the sky is blue."),
    ]
    result = validate_variants("I think the sky is blue.", candidates)
    assert result.valid
    assert isinstance(result, ValidationResult)