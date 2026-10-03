import hashlib
import json
from pathlib import Path

import pytest

from tools.init_x1_fit_platform_repeatability import initialize


def _digest(data):
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _authority():
    data = {
        "schema_version": 1,
        "authority": "x1_one_zone_pilot",
        "scope": "unpowered_fit_rig_only",
        "qualified_for_four_zone_duplication": True,
        "channel": "left_heel",
        "hx711_sps": 10,
        "linear_fit": {
            "intercept": 100000.0,
            "counts_per_n": 1000.0,
            "r2": 1.0,
        },
        "mass_reference_provenance": {
            "mass_entries": [
                {
                    "mass_id": "CAL-10",
                    "role": "CALIBRATION",
                    "mass_kg": 10.0,
                    "uncertainty_kg": 0.01,
                },
                {
                    "mass_id": "VAL-7P5",
                    "role": "VALIDATION",
                    "mass_kg": 7.5,
                    "uncertainty_kg": 0.0075,
                },
            ]
        },
        "powered_operation_authorized": False,
    }
    data["authority_fingerprint_sha256"] = _digest(data)
    return data


def test_initializer_seeds_exact_one_zone_lineage(tmp_path: Path):
    authority = _authority()
    source = tmp_path / "pilot_authority.json"
    source.write_text(json.dumps(authority), encoding="utf-8")

    session = tmp_path / "repeatability"
    report = initialize(session, source, "REPEAT-001")

    assert report["scope"] == "x1_fit_platform_repeatability_workspace"
    assert report["issue"] == 63
    assert report["one_zone_authority_fingerprint_sha256"] == authority[
        "authority_fingerprint_sha256"
    ]
    assert report["validation_mass"]["mass_id"] == "VAL-7P5"
    assert report["four_zone_duplication_authority"] is False
    assert report["powered_operation_authority"] is False

    manifest = json.loads(
        (session / "platform_repeatability_manifest.json").read_text()
    )
    assert manifest["session_id"] == "REPEAT-001"
    assert manifest["one_zone_authority_fingerprint_sha256"] == authority[
        "authority_fingerprint_sha256"
    ]
    copied = json.loads(
        (session / "provenance/one_zone_pilot_authority.json").read_text()
    )
    assert copied == authority


def test_initializer_rejects_tampered_one_zone_authority(tmp_path: Path):
    authority = _authority()
    authority["linear_fit"]["counts_per_n"] = 900.0
    source = tmp_path / "pilot_authority.json"
    source.write_text(json.dumps(authority), encoding="utf-8")

    with pytest.raises(ValueError, match="fingerprint is invalid"):
        initialize(tmp_path / "repeatability", source, "REPEAT-001")


def test_initializer_refuses_nonempty_session(tmp_path: Path):
    authority = _authority()
    source = tmp_path / "pilot_authority.json"
    source.write_text(json.dumps(authority), encoding="utf-8")
    session = tmp_path / "repeatability"
    session.mkdir()
    marker = session / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError):
        initialize(session, source, "REPEAT-001")
    assert marker.read_text(encoding="utf-8") == "keep"
