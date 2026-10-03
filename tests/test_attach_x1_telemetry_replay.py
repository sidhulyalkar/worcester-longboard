import copy
import hashlib
import json
from pathlib import Path

import pytest

from tools.attach_x1_telemetry_replay_to_commissioning import attach

ROOT = Path(__file__).resolve().parents[1]
STAGE_TEMPLATE = json.loads(
    (
        ROOT / "hardware/rev_c_powered_commissioning_stage_template.json"
    ).read_text()
)
COMMISSIONING = json.loads(
    (
        ROOT / "hardware/rev_c_powered_commissioning_snapshot_2026-10-01.json"
    ).read_text()
)


def _stamp(doc):
    payload = json.dumps(
        doc,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    out = dict(doc)
    out["authority_fingerprint_sha256"] = hashlib.sha256(payload).hexdigest()
    return out


def _fixture():
    stage_id = "SECURED_UNLOADED_SPIN"
    power_fp = "a" * 64
    manifest = copy.deepcopy(STAGE_TEMPLATE)
    manifest.update(
        {
            "board_id": "X1-A",
            "configuration_id": "CFG-A",
            "stage_id": stage_id,
            "power_architecture_fingerprint_sha256": power_fp,
        }
    )
    spec = next(
        item for item in COMMISSIONING["stages"]
        if item["stage_id"] == stage_id
    )
    metrics = [
        {
            "metric_id": metric,
            "unit": "synthetic-unit",
            "value": None,
            "evidence_ref": f"telemetry://physical/{metric}",
            "method": "fixture",
            "source_signals": ["fixture"],
        }
        for metric in spec["required_measurements"]
    ]
    replay = _stamp(
        {
            "schema_version": 1,
            "authority": "x1_commissioning_telemetry_replay",
            "qualified": True,
            "errors": [],
            "session_id": "physical-fixture",
            "board_id": "X1-A",
            "configuration_id": "CFG-A",
            "commissioning_stage_id": stage_id,
            "power_architecture_fingerprint_sha256": power_fp,
            "telemetry_session_fingerprint_sha256": "b" * 64,
            "metrics": metrics,
            "metric_ids": sorted(item["metric_id"] for item in metrics),
            "synthetic_fixture": False,
            "physical_evidence_eligible": True,
            "commissioning_stage_qualified": False,
            "powered_operation_authorized": False,
            "public_operation_authorized": False,
            "dog_accompanied_operation_authorized": False,
            "interpretation_boundary": "fixture",
        }
    )
    return manifest, replay, spec


def test_attach_populates_exact_replay_fingerprint_and_measurements():
    manifest, replay, spec = _fixture()
    out = attach(manifest, replay, COMMISSIONING)

    assert (
        out["telemetry_replay_fingerprint_sha256"]
        == replay["authority_fingerprint_sha256"]
    )
    assert [x["metric_id"] for x in out["measurements"]] == spec[
        "required_measurements"
    ]
    assert all(
        x["source"] == "x1_commissioning_telemetry_replay"
        for x in out["measurements"]
    )
    replay_by_id = {x["metric_id"]: x for x in replay["metrics"]}
    for item in out["measurements"]:
        assert item["evidence_ref"] == replay_by_id[item["metric_id"]][
            "evidence_ref"
        ]


def test_attach_rejects_synthetic_replay():
    manifest, replay, _ = _fixture()
    replay["synthetic_fixture"] = True
    replay["physical_evidence_eligible"] = False
    replay.pop("authority_fingerprint_sha256")
    replay = _stamp(replay)

    with pytest.raises(ValueError, match="synthetic telemetry"):
        attach(manifest, replay, COMMISSIONING)


def test_attach_rejects_lineage_mismatch():
    manifest, replay, _ = _fixture()
    replay["configuration_id"] = "CFG-B"
    replay.pop("authority_fingerprint_sha256")
    replay = _stamp(replay)

    with pytest.raises(ValueError, match="lineage mismatch"):
        attach(manifest, replay, COMMISSIONING)
