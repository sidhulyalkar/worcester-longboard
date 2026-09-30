import hashlib
import json

from tools.qualify_rev_c_chassis_release import qualify


def _stamp(doc):
    payload = json.dumps(
        doc, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    stamped = dict(doc)
    stamped["authority_fingerprint_sha256"] = hashlib.sha256(payload).hexdigest()
    return stamped


def _fit_pilot():
    return _stamp({"qualified_for_four_zone_duplication": True})


def _manifest():
    pilot = _fit_pilot()
    return {
        "schema_version": 1,
        "scope": "rev_c_chassis_purchase_release",
        "selected_chassis_family": "compact_matrix_reference",
        "selected_wheel_family": "200x50_pneumatic",
        "selected_brake_architecture": "rear_v5_reference",
        "selected_topology_for_measurement": "rear_v5_rear_2wd_shared",
        "checks": {
            "deck_envelope_comparison_completed": True,
            "traction_trade_study_reviewed": True,
            "independent_stopping_path_credible": True,
            "range_pack_inert_envelope_plausible": True,
            "no_unqualified_safety_critical_adapter": True,
            "rejected_alternatives_recorded": True,
        },
        "evidence_refs": {
            "deck_envelope_record_sha256": "1" * 64,
            "topology_trade_record_sha256": "2" * 64,
            "inert_pack_envelope_record_sha256": "3" * 64,
            "fit_pilot_authority_fingerprint_sha256": pilot[
                "authority_fingerprint_sha256"
            ],
        },
        "rejected_alternatives": [
            {
                "id": "agent_wide_deck",
                "reason": "physical stance comparison found insufficient leverage advantage",
            }
        ],
        "open_questions": ["physical V5 plus drive axial coexistence"],
        "powered_operation_authorized": False,
    }


def test_valid_release_qualifies_without_authorizing_power():
    pilot = _fit_pilot()
    report = qualify(_manifest(), pilot)
    assert report["qualified"] is True
    assert report["authority"] == "x1_rev_c_chassis_release"
    assert report["powered_operation_authorized"] is False
    assert len(report["authority_fingerprint_sha256"]) == 64


def test_missing_physical_deck_comparison_fails_closed():
    pilot = _fit_pilot()
    manifest = _manifest()
    manifest["checks"]["deck_envelope_comparison_completed"] = False
    report = qualify(manifest, pilot)
    assert report["qualified"] is False
    assert any("deck_envelope_comparison_completed" in e for e in report["errors"])


def test_missing_rejected_alternatives_fails_closed():
    pilot = _fit_pilot()
    manifest = _manifest()
    manifest["rejected_alternatives"] = []
    report = qualify(manifest, pilot)
    assert report["qualified"] is False
    assert any("rejected_alternatives" in e for e in report["errors"])


def test_mismatched_fit_pilot_authority_fails_closed():
    pilot = _fit_pilot()
    manifest = _manifest()
    manifest["evidence_refs"]["fit_pilot_authority_fingerprint_sha256"] = "f" * 64
    report = qualify(manifest, pilot)
    assert report["qualified"] is False
    assert any("different fit-pilot authority" in e for e in report["errors"])


def test_unqualified_fit_pilot_cannot_release_chassis():
    pilot = _stamp({"qualified_for_four_zone_duplication": False})
    manifest = _manifest()
    manifest["evidence_refs"]["fit_pilot_authority_fingerprint_sha256"] = pilot[
        "authority_fingerprint_sha256"
    ]
    report = qualify(manifest, pilot)
    assert report["qualified"] is False
    assert any("not qualified" in e for e in report["errors"])


def test_release_cannot_authorize_power():
    pilot = _fit_pilot()
    manifest = _manifest()
    manifest["powered_operation_authorized"] = True
    report = qualify(manifest, pilot)
    assert report["qualified"] is False
    assert report["powered_operation_authorized"] is False
