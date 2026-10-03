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



def test_snowdeck_signature_overlay_is_sanitized():
    data = {
        "scope": "x1_snowdeck_bench_signature",
        "condition_id": "S1",
        "trial_count": 3,
        "neutral": {"left_load_fraction": {"mean": 0.48, "sd": 0.01}},
        "heel_to_toe_forefoot_transfer": {
            "left": {"mean": 0.2, "sd": 0.01},
            "right": {"mean": 0.22, "sd": 0.02},
        },
        "deep_knee_delta_from_neutral": {},
        "mechanical_rejects": [],
        "eligible_for_further_bench_comparison": True,
        "source_force_log_sha256": "a" * 64,
        "source_session_sha256": "b" * 64,
        "session_id": "PRIVATE-SESSION-ID",
        "private_notes": "must not enter runtime manifest",
        "physical_authority": False,
        "fabrication_authority": False,
        "ride_authority": False,
        "powered_operation_authorized": False,
    }

    clean = mod.sanitize_snowdeck_signature(data)

    assert clean["condition_id"] == "S1"
    assert clean["trial_count"] == 3
    assert "session_id" not in clean
    assert "private_notes" not in clean


def test_snowdeck_signature_overlay_refuses_authority_promotion():
    data = {
        "scope": "x1_snowdeck_bench_signature",
        "physical_authority": False,
        "fabrication_authority": True,
        "ride_authority": False,
        "powered_operation_authorized": False,
    }

    try:
        mod.sanitize_snowdeck_signature(data)
    except ValueError as exc:
        assert "fabrication_authority=false" in str(exc)
    else:
        raise AssertionError("fabrication authority must be rejected")


def test_snowdeck_comparison_cannot_select_winner():
    data = {
        "scope": "x1_snowdeck_bench_signature_comparison",
        "baseline": {"condition_id": "S0", "mechanical_rejects": []},
        "variant": {"condition_id": "S1", "mechanical_rejects": []},
        "signed_variant_minus_baseline": {},
        "variant_eligible_for_further_bench_comparison": True,
        "winner_selected": True,
        "physical_authority": False,
        "fabrication_authority": False,
        "ride_authority": False,
        "powered_operation_authorized": False,
    }

    try:
        mod.sanitize_snowdeck_comparison(data)
    except ValueError as exc:
        assert "must not select a winner" in str(exc)
    else:
        raise AssertionError("showcase must reject ranked SnowDeck comparison")



def test_deck_selection_projection_requires_valid_fingerprint():
    valid = {
        "schema_version": 1,
        "authority": "x1_rev_c_deck_comparison",
        "scope": "sanitized_pre_purchase_deck_comparison",
        "qualified": True,
        "errors": [],
        "selected_candidate_id": "agent_class",
        "candidate_summaries": [],
        "selection_reason_recorded": True,
        "private_source_sha256": "a" * 64,
        "powered_operation_authorized": False,
    }
    valid["authority_fingerprint_sha256"] = fingerprint(valid)

    projected = mod.extract_deck_comparison_selection([valid])

    assert projected["selected_candidate_id"] == "agent_class"
    assert projected["authority_fingerprint_sha256"] == valid["authority_fingerprint_sha256"]

    invalid = dict(valid)
    invalid["selected_candidate_id"] = "comp95_class"

    try:
        mod.extract_deck_comparison_selection([invalid])
    except ValueError as exc:
        assert "failed sanitized contract" in str(exc)
    else:
        raise AssertionError("tampered deck authority must fail closed")

    unknown = dict(valid)
    unknown.pop("authority_fingerprint_sha256")
    unknown["selected_candidate_id"] = "mystery_deck"
    unknown["authority_fingerprint_sha256"] = fingerprint(unknown)

    try:
        mod.extract_deck_comparison_selection([unknown])
    except ValueError as exc:
        assert "selected unknown candidate" in str(exc)
    else:
        raise AssertionError("unknown deck candidate must fail closed")


def test_deck_selection_projection_refuses_conflicting_valid_authorities():
    docs = []
    for candidate_id in ("comp95_class", "agent_class"):
        doc = {
            "schema_version": 1,
            "authority": "x1_rev_c_deck_comparison",
            "scope": "sanitized_pre_purchase_deck_comparison",
            "qualified": True,
            "errors": [],
            "selected_candidate_id": candidate_id,
            "candidate_summaries": [],
            "selection_reason_recorded": True,
            "private_source_sha256": candidate_id,
            "powered_operation_authorized": False,
        }
        doc["authority_fingerprint_sha256"] = fingerprint(doc)
        docs.append(doc)

    try:
        mod.extract_deck_comparison_selection(docs)
    except ValueError as exc:
        assert "conflicting qualified deck-comparison selections" in str(exc)
    else:
        raise AssertionError("conflicting physical deck selections must fail closed")
