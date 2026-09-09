"""Hermetic unit tests for the submission background-pipeline mapping.

Covers the pure persistence helpers in ``orchestration.pipeline``: mapping
generated variants onto ``PromptVariant`` rows and a responder batch onto
``Response`` rows. No database is involved; the ORM rows are constructed in
memory and their attribute values are asserted.
"""
import uuid

from database.models import PromptVariant, Submission
from orchestration.pipeline import build_response_rows, build_variant_rows
from orchestration.variants import Variant
from responders.respond import ResponderBatch, ResponderResult

SUBMISSION_ID = uuid.uuid4()

FAKE_VARIANTS = (
    Variant("original", "Prompt text"),
    Variant("adversarial", "Prompt text but trickier"),
    Variant("concise", "Prompt text, short"),
    Variant("multi-aspect", "Prompt text + the whole story"),
)


def _submission() -> Submission:
    return Submission(
        submission_id=SUBMISSION_ID,
        user_id=uuid.uuid4(),
        original_prompt="Prompt text",
        status="processing",
    )


def _variant_rows(framer_id: uuid.UUID | None) -> list[PromptVariant]:
    return build_variant_rows(
        _submission(),
        variants=FAKE_VARIANTS,
        generated_by_model_id=framer_id,
    )


class TestBuildVariantRows:
    def test_maps_one_row_per_variant(self):
        rows = _variant_rows(None)

        assert len(rows) == 4
        assert all(row.submission_id == SUBMISSION_ID for row in rows)
        assert [row.variant_type for row in rows] == [v.variant_type for v in FAKE_VARIANTS]
        assert [row.variant_text for row in rows] == [v.text for v in FAKE_VARIANTS]

    def test_generated_by_model_id_is_nullable(self):
        assert all(row.generated_by_model_id is None for row in _variant_rows(None))

    def test_framer_model_id_is_propagated(self):
        framer_id = uuid.uuid4()
        assert all(row.generated_by_model_id == framer_id for row in _variant_rows(framer_id))


class TestBuildResponseRows:
    def _rows(self):
        rows = _variant_rows(None)
        for row in rows:
            row.variant_id = uuid.uuid4()
        return {row.variant_type: row for row in rows}

    def _batch(self, model_id: uuid.UUID) -> ResponderBatch:
        return ResponderBatch(
            results=[
                ResponderResult(
                    variant_type="original",
                    provider="groq",
                    model="responder-a",
                    status="success",
                    response_text="Good answer.",
                    latency_ms=250,
                    total_tokens=42,
                ),
                ResponderResult(
                    variant_type="adversarial",
                    provider="groq",
                    model="responder-a",
                    status="failed",
                    error_message="provider exploded",
                    latency_ms=100,
                    total_tokens=0,
                ),
                ResponderResult(
                    variant_type="concise",
                    provider="groq",
                    model="responder-a",
                    status="timeout",
                    error_message="attempt 1: timed out",
                    total_tokens=None,
                ),
            ]
        )

    def test_maps_batch_onto_rows_preserving_failures(self):
        model_id = uuid.uuid4()
        by_type = self._rows()
        model_ids = {("groq", "responder-a"): model_id}

        rows = build_response_rows(
            list(by_type.values()),
            batch=self._batch(model_id),
            model_id_by_pair=model_ids,
        )

        by_variant = {row.variant_id: row for row in rows}
        assert len(rows) == 3
        assert all(row.model_id == model_id for row in rows)
        assert rows[0].status == "success"
        assert rows[0].response_text == "Good answer."
        assert rows[0].error_message is None
        assert rows[0].latency_ms == 250
        assert rows[0].token_usage == 42
        assert rows[1].status == "failed"
        assert rows[1].response_text is None
        assert rows[1].error_message == "provider exploded"
        assert rows[2].status == "timeout"
        assert rows[2].response_text is None
        assert rows[2].token_usage is None

    def test_rows_reference_variant_ids(self):
        model_id = uuid.uuid4()
        by_type = self._rows()
        expected_variant_id = by_type["original"].variant_id

        rows = build_response_rows(
            list(by_type.values()),
            batch=self._batch(model_id),
            model_id_by_pair={("groq", "responder-a"): model_id},
        )

        assert rows[0].variant_id == expected_variant_id

    def test_drops_unmapped_variant(self):
        model_id = uuid.uuid4()
        batch = ResponderBatch(
            results=[
                ResponderResult(
                    variant_type="does-not-exist",
                    provider="groq",
                    model="responder-a",
                    status="success",
                    response_text="orphan",
                )
            ]
        )
        rows = build_response_rows(
            list(self._rows().values()),
            batch=batch,
            model_id_by_pair={("groq", "responder-a"): model_id},
        )
        assert rows == []

    def test_drops_unmapped_model(self):
        batch = self._batch(uuid.uuid4())
        rows = build_response_rows(
            list(self._rows().values()),
            batch=batch,
            model_id_by_pair={},
        )
        assert rows == []