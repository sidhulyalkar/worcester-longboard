import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
SPEC = importlib.util.spec_from_file_location(
    "build_showcase_manifest", ROOT / "tools" / "build_showcase_manifest.py"
)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mod)


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def fingerprint(doc):
    unsigned = dict(doc)
    unsigned.pop("authority_fingerprint_sha256", None)
    payload = json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def minimal_plan():
    return {
        "schema_version": 1,
        "project": "Worcester X1",
        "gates": {
            "chassis": {
                "issue": 25,
                "requires": [],
                "evidence": [
                    {"path": "authority", "equals": "x1_chassis"},
                    {"path": "qualified", "equals": True},
                    {
                        "path": "authority_fingerprint_sha256",
                        "type": "valid_authority_fingerprint",
                    },
                ],
            }
        },
        "capabilities": {},
    }


def minimal_procurement():
    return {"rules": {}, "items": []}


def test_default_manifest_is_fail_closed(tmp_path):
    seed = {
        "project": "Worcester X1",
        "configuration": "test",
        "physical_authority": False,
        "powered_operation_authorized": False,
        "components": [
            {
                "id": "deck",
                "evidence_state": "REFERENCE",
                "authority_gate": "chassis",
            }
        ],
    }
    seed_path = tmp_path / "seed.json"
    authority_path = tmp_path / "authority.json"
    procurement_path = tmp_path / "procurement.json"
    write_json(seed_path, seed)
    write_json(authority_path, minimal_plan())
    write_json(procurement_path, minimal_procurement())

    old_root = mod.ROOT
    mod.ROOT = tmp_path
    try:
        out = mod.build(seed_path, authority_path, procurement_path, [])
    finally:
        mod.ROOT = old_root

    assert out["powered_operation_authorized"] is False
    assert out["physical_authority"] is False
    assert out["gates"]["chassis"]["satisfied"] is False
    assert out["components"][0]["evidence_state"] == "REFERENCE"


def test_unfingerprinted_qualified_claim_does_not_promote(tmp_path):
    seed = {
        "project": "Worcester X1",
        "configuration": "test",
        "physical_authority": False,
        "powered_operation_authorized": False,
        "components": [
            {
                "id": "deck",
                "evidence_state": "REFERENCE",
                "authority_gate": "chassis",
            }
        ],
    }
    seed_path = tmp_path / "seed.json"
    authority_path = tmp_path / "authority.json"
    procurement_path = tmp_path / "procurement.json"
    evidence_path = tmp_path / "evidence.json"
    write_json(seed_path, seed)
    write_json(authority_path, minimal_plan())
    write_json(procurement_path, minimal_procurement())
    write_json(evidence_path, {"authority": "x1_chassis", "qualified": True})

    old_root = mod.ROOT
    mod.ROOT = tmp_path
    try:
        out = mod.build(
            seed_path, authority_path, procurement_path, [evidence_path]
        )
    finally:
        mod.ROOT = old_root

    assert out["gates"]["chassis"]["satisfied"] is False
    assert out["components"][0]["evidence_state"] == "REFERENCE"


def test_valid_authority_promotes_visual_state(tmp_path):
    seed = {
        "project": "Worcester X1",
        "configuration": "test",
        "physical_authority": False,
        "powered_operation_authorized": False,
        "components": [
            {
                "id": "deck",
                "evidence_state": "REFERENCE",
                "authority_gate": "chassis",
            }
        ],
    }
    evidence = {"authority": "x1_chassis", "qualified": True}
    evidence["authority_fingerprint_sha256"] = fingerprint(evidence)

    seed_path = tmp_path / "seed.json"
    authority_path = tmp_path / "authority.json"
    procurement_path = tmp_path / "procurement.json"
    evidence_path = tmp_path / "evidence.json"
    write_json(seed_path, seed)
    write_json(authority_path, minimal_plan())
    write_json(procurement_path, minimal_procurement())
    write_json(evidence_path, evidence)

    old_root = mod.ROOT
    mod.ROOT = tmp_path
    try:
        out = mod.build(
            seed_path, authority_path, procurement_path, [evidence_path]
        )
    finally:
        mod.ROOT = old_root

    assert out["gates"]["chassis"]["satisfied"] is True
    assert out["components"][0]["evidence_state"] == "QUALIFIED"


def test_powered_claim_is_rejected(tmp_path):
    path = tmp_path / "powered.json"
    write_json(path, {"powered_operation_authorized": True})
    try:
        mod.sanitize_evidence_documents([path])
    except ValueError as exc:
        assert "powered-operation" in str(exc)
    else:
        raise AssertionError("powered-operation claim should fail closed")


def test_risk_summary_is_ranked_and_sanitized():
    register = {
        "risks": [
            {
                "id": "M-low",
                "subsystem": "low",
                "failure_mode": "low mode",
                "effect": "low effect",
                "priority_score": 10,
                "status": "OPEN",
                "must_close_before": "later",
                "prevention": ["not needed in public summary"],
            },
            {
                "id": "M-high",
                "subsystem": "high",
                "failure_mode": "high mode",
                "effect": "high effect",
                "priority_score": 60,
                "status": "OPEN",
                "must_close_before": "earlier",
                "verification": ["not needed in public summary"],
            },
        ]
    }

    summary = mod.summarize_risks(register, limit=1)

    assert [row["id"] for row in summary] == ["M-high"]
    assert summary[0]["priority_score"] == 60
    assert "verification" not in summary[0]
    assert "prevention" not in summary[0]
