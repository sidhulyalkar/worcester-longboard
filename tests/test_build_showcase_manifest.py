import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_showcase_manifest", ROOT / "tools" / "build_showcase_manifest.py"
)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mod)


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def test_default_manifest_is_fail_closed(tmp_path):
    seed = {
        "project": "Worcester X1",
        "configuration": "test",
        "powered_operation_authorized": False,
        "components": [
            {
                "id": "deck",
                "evidence_state": "REFERENCE",
                "authority_gate": "chassis",
            }
        ],
    }
    authority = {
        "gates": {
            "chassis": {
                "issue": 25,
                "requires": [],
                "evidence": [{"path": "authority", "equals": "x1_chassis"}],
            }
        }
    }
    seed_path = tmp_path / "seed.json"
    authority_path = tmp_path / "authority.json"
    write_json(seed_path, seed)
    write_json(authority_path, authority)

    # Relative-path hashing in production expects repo paths. Patch ROOT for isolated test.
    old_root = mod.ROOT
    mod.ROOT = tmp_path
    try:
        out = mod.build(seed_path, authority_path, None)
    finally:
        mod.ROOT = old_root

    assert out["powered_operation_authorized"] is False
    assert out["physical_authority"] is False
    assert out["gates"]["chassis"]["qualified"] is False
    assert out["components"][0]["evidence_state"] == "REFERENCE"


def test_powered_claim_is_rejected():
    gates = {"g": {"evidence": [{"path": "authority", "equals": "x1_test"}]}}
    evidence = {
        "g": {
            "authority": "x1_test",
            "qualified": True,
            "powered_operation_authorized": True,
        }
    }
    try:
        mod.validate_evidence_index(gates, evidence)
    except ValueError as exc:
        assert "powered-operation" in str(exc)
    else:
        raise AssertionError("powered-operation claim should fail closed")


def test_qualified_gate_promotes_visual_state():
    seed = {
        "components": [
            {"id": "brake", "evidence_state": "BLOCKED", "authority_gate": "brake"}
        ]
    }
    status = {
        "brake": {
            "qualified": True,
            "evidence_supplied": True,
            "issue": 14,
            "requires": [],
            "expected_authority": "x1_brake",
        }
    }
    out = mod.promote_components(seed, status)
    assert out[0]["evidence_state"] == "QUALIFIED"
    assert out[0]["gate_qualified"] is True
