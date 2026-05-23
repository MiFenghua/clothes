from __future__ import annotations

from app.agents.quality_gates import image_quality_gates
from app.schemas.quality import GateStatus


def test_minor_artifact_score_warns_but_does_not_block_strong_tryon_image():
    report = image_quality_gates(
        candidate_id="candidate_1",
        identity_score=0.9,
        garment_score=0.9,
        artifact_score=0.8,
        realism_score=0.9,
        threshold=0.84,
    )

    artifact_gate = next(gate for gate in report.gates if gate.gate == "Artifact Gate")
    assert artifact_gate.status == GateStatus.warning
    assert artifact_gate.blocking is False
    assert report.accepted is True
