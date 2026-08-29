import pytest
from backend.app.agent.hypotheses import Hypothesis, HypothesisStatus


def test_hypothesis_defaults():
    hyp = Hypothesis(id="hyp-1", statement="Database connection pool exhausted")

    assert hyp.id == "hyp-1"
    assert hyp.statement == "Database connection pool exhausted"
    assert hyp.status == HypothesisStatus.GENERATED
    assert hyp.score == 0.0
    assert hyp.supporting_evidence_ids == []
    assert hyp.contradicting_evidence_ids == []
    assert hyp.missing_evidence == []
    assert hyp.disconfirming_condition is None
    assert hyp.reasoning == ""


def test_hypothesis_helpers():
    hyp = Hypothesis(id="hyp-2", statement="Memory leak in worker process")

    hyp.add_supporting_evidence("ev-101")
    hyp.add_supporting_evidence("ev-101")  # Deduplication
    assert hyp.supporting_evidence_ids == ["ev-101"]

    hyp.add_contradicting_evidence("ev-201")
    hyp.add_contradicting_evidence("ev-201")  # Deduplication
    assert hyp.contradicting_evidence_ids == ["ev-201"]

    hyp.set_missing_evidence(["heap_dump", "gc_logs"])
    assert hyp.missing_evidence == ["heap_dump", "gc_logs"]

    hyp.update_assessment(
        status=HypothesisStatus.CONFIRMED,
        score=0.92,
        reasoning="GC logs confirm out-of-memory errors",
    )
    assert hyp.status == HypothesisStatus.CONFIRMED
    assert hyp.score == 0.92
    assert hyp.reasoning == "GC logs confirm out-of-memory errors"
