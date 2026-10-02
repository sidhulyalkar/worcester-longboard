import hashlib
import json
from pathlib import Path

import pytest

from tools.init_rev_c_environmental_session import initialize


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


def _write_authorities(tmp_path: Path):
    chassis = _stamp(
        {
            "schema_version": 1,
            "authority": "x1_rolling_chassis_physical",
            "qualified": True,
            "powered_operation_authorized": False,
        }
    )
    dummy = _stamp(
        {
            "schema_version": 1,
            "authority": "x1_dummy_pack_mount",
            "qualified": True,
            "powered_operation_authorized": False,
        }
    )
    chassis_path = tmp_path / "chassis.json"
    dummy_path = tmp_path / "dummy.json"
    chassis_path.write_text(json.dumps(chassis), encoding="utf-8")
    dummy_path.write_text(json.dumps(dummy), encoding="utf-8")
    return chassis_path, dummy_path, chassis, dummy


def test_initializer_links_exact_valid_physical_authorities(tmp_path: Path):
    chassis_path, dummy_path, chassis, dummy = _write_authorities(tmp_path)
    session = tmp_path / "environmental-01"

    report = initialize(
        session,
        chassis_path,
        dummy_path,
        "INERT-ENC-A",
        "HARNESS-A",
    )

    assert report["physical_authority"] is False
    assert report["electrical_wet_operation_authority"] is False
    assert report["procurement_authority"] is False
    assert report["powered_operation_authority"] is False

    manifest = json.loads((session / "environmental_manifest.json").read_text())
    assert manifest["scope"] == "rev_c_inert_environmental_durability_trial"
    assert (
        manifest["chassis_authority_fingerprint_sha256"]
        == chassis["authority_fingerprint_sha256"]
    )
    assert (
        manifest["dummy_pack_authority_fingerprint_sha256"]
        == dummy["authority_fingerprint_sha256"]
    )
    assert manifest["candidate_enclosure_id"] == "INERT-ENC-A"
    assert manifest["harness_revision_id"] == "HARNESS-A"
    assert manifest["live_battery_present"] is False
    assert manifest["powered_vehicle"] is False


def test_initializer_rejects_tampered_authority(tmp_path: Path):
    chassis_path, dummy_path, _, _ = _write_authorities(tmp_path)
    dummy = json.loads(dummy_path.read_text())
    dummy["qualified"] = False
    dummy_path.write_text(json.dumps(dummy), encoding="utf-8")

    with pytest.raises(ValueError, match="fingerprint-valid"):
        initialize(
            tmp_path / "environmental-01",
            chassis_path,
            dummy_path,
            "INERT-ENC-A",
            "HARNESS-A",
        )


def test_initializer_refuses_to_overwrite_existing_session(tmp_path: Path):
    chassis_path, dummy_path, _, _ = _write_authorities(tmp_path)
    session = tmp_path / "environmental-01"
    session.mkdir()
    marker = session / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError):
        initialize(
            session,
            chassis_path,
            dummy_path,
            "INERT-ENC-A",
            "HARNESS-A",
        )

    assert marker.read_text(encoding="utf-8") == "keep"
