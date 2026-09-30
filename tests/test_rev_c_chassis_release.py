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


def _deck():
    return _stamp(
        {
            "schema_version": 1,
            "authority": "x1_rev_c_deck_comparison",
            "scope": "sanitized_pre_purchase_deck_comparison",
            "qualified": True,
            "errors": [],
            "selected_candidate_id": "comp95_class",
            "candidate_summaries": [],
            "selection_reason_recorded": True,
            "private_source_sha256": "1" * 64,
            "powered_operation_authorized": False,
        }
    )


def _topology():
    return _stamp(
        {
            "schema_version": 1,
            "authority": "x1_rev_c_topology_trade",
            "scope": "pre_purchase_topology_measurement_selection_only",
            "qualified": True,
            "errors": [],
            "selected_topology_for_measurement": "REAR_V5_REAR_2WD_SHARED",
            "candidate_summaries": {},
            "traction_sweep_reviewed": True,
            "independent_stopping_path_credible": True,
            "no_unqualified_safety_critical_adapter": True,
            "private_or_local_source_sha256": "2" * 64,
            "powered_operation_authorized": False,
        }
    )


def _inert():
    return _stamp(
        {
            "schema_version": 1,
            "authority": "x1_rev_c_inert_pack_envelope",
            "scope": "pre_purchase_inert_pack_envelope_only",
            "qualified": True,
            "errors": [],
            "chassis_candidate_id": "compact_matrix_reference",
            "pack_summaries": {},
            "range_pack_inert_envelope_plausible": True,
            "private_or_local_source_sha256": "3" * 64,
            "powered_operation_authorized": False,
        }
    )


def _manifest(pilot=None, deck=None, topology=None, inert=None):
    pilot = pilot or _fit_pilot()
    deck = deck or _deck()
    topology = topology or _topology()
    inert = inert or _inert()
    return {
        "schema_version": 1,
        "scope": "rev_c_chassis_purchase_release",
        "selected_deck_candidate_id": "comp95_class",
        "selected_chassis_family": "compact_matrix_reference",
        "selected_wheel_family": "200x50_pneumatic",
        "selected_brake_architecture": "rear_v5_reference",
        "selected_topology_for_measurement": "REAR_V5_REAR_2WD_SHARED",
        "checks": {
            "deck_envelope_comparison_completed": True,
            "traction_trade_study_reviewed": True,
            "independent_stopping_path_credible": True,
            "range_pack_inert_envelope_plausible": True,
            "no_unqualified_safety_critical_adapter": True,
            "rejected_alternatives_recorded": True,
        },
        "evidence_refs": {
            "deck_comparison_authority_fingerprint_sha256": deck[
                "authority_fingerprint_sha256"
            ],
            "topology_trade_authority_fingerprint_sha256": topology[
                "authority_fingerprint_sha256"
            ],
            "inert_pack_envelope_authority_fingerprint_sha256": inert[
                "authority_fingerprint_sha256"
            ],
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
        "open_questions": ["physical brake/drive coexistence remains downstream"],
        "powered_operation_authorized": False,
    }


def _qualify(manifest=None, pilot=None, deck=None, topology=None, inert=None):
    pilot = pilot or _fit_pilot()
    deck = deck or _deck()
    topology = topology or _topology()
    inert = inert or _inert()
    manifest = manifest or _manifest(pilot, deck, topology, inert)
    return qualify(manifest, pilot, deck, topology, inert)


def test_valid_release_qualifies_without_authorizing_power():
    report = _qualify()
    assert report["qualified"] is True
    assert report["authority"] == "x1_rev_c_chassis_release"
    assert report["selected_deck_candidate_id"] == "comp95_class"
    assert report["powered_operation_authorized"] is False
    assert len(report["authority_fingerprint_sha256"]) == 64


def test_missing_physical_deck_comparison_fails_closed():
    pilot, deck, topology, inert = _fit_pilot(), _deck(), _topology(), _inert()
    manifest = _manifest(pilot, deck, topology, inert)
    manifest["checks"]["deck_envelope_comparison_completed"] = False
    report = qualify(manifest, pilot, deck, topology, inert)
    assert report["qualified"] is False
    assert any("deck_envelope_comparison_completed" in e for e in report["errors"])


def test_missing_rejected_alternatives_fails_closed():
    pilot, deck, topology, inert = _fit_pilot(), _deck(), _topology(), _inert()
    manifest = _manifest(pilot, deck, topology, inert)
    manifest["rejected_alternatives"] = []
    report = qualify(manifest, pilot, deck, topology, inert)
    assert report["qualified"] is False
    assert any("rejected_alternatives" in e for e in report["errors"])


def test_mismatched_fit_pilot_authority_fails_closed():
    pilot, deck, topology, inert = _fit_pilot(), _deck(), _topology(), _inert()
    manifest = _manifest(pilot, deck, topology, inert)
    manifest["evidence_refs"]["fit_pilot_authority_fingerprint_sha256"] = "f" * 64
    report = qualify(manifest, pilot, deck, topology, inert)
    assert report["qualified"] is False
    assert any("different fit-pilot authority" in e for e in report["errors"])


def test_selected_deck_must_match_deck_authority():
    pilot, deck, topology, inert = _fit_pilot(), _deck(), _topology(), _inert()
    manifest = _manifest(pilot, deck, topology, inert)
    manifest["selected_deck_candidate_id"] = "agent_class"
    report = qualify(manifest, pilot, deck, topology, inert)
    assert report["qualified"] is False
    assert any("selected deck disagrees" in e for e in report["errors"])


def test_selected_topology_must_match_topology_authority():
    pilot, deck, topology, inert = _fit_pilot(), _deck(), _topology(), _inert()
    manifest = _manifest(pilot, deck, topology, inert)
    manifest["selected_topology_for_measurement"] = "REAR_V5_FRONT_2WD"
    report = qualify(manifest, pilot, deck, topology, inert)
    assert report["qualified"] is False
    assert any("topology disagrees" in e for e in report["errors"])


def test_unqualified_inert_range_envelope_cannot_release_chassis():
    pilot, deck, topology = _fit_pilot(), _deck(), _topology()
    inert = _inert()
    unsigned = dict(inert)
    unsigned.pop("authority_fingerprint_sha256")
    unsigned["range_pack_inert_envelope_plausible"] = False
    inert = _stamp(unsigned)
    manifest = _manifest(pilot, deck, topology, inert)
    report = qualify(manifest, pilot, deck, topology, inert)
    assert report["qualified"] is False
    assert any("does not qualify the range envelope" in e for e in report["errors"])


def test_unqualified_fit_pilot_cannot_release_chassis():
    pilot = _stamp({"qualified_for_four_zone_duplication": False})
    deck, topology, inert = _deck(), _topology(), _inert()
    manifest = _manifest(pilot, deck, topology, inert)
    report = qualify(manifest, pilot, deck, topology, inert)
    assert report["qualified"] is False
    assert any("not qualified" in e for e in report["errors"])


def test_release_cannot_authorize_power():
    pilot, deck, topology, inert = _fit_pilot(), _deck(), _topology(), _inert()
    manifest = _manifest(pilot, deck, topology, inert)
    manifest["powered_operation_authorized"] = True
    report = qualify(manifest, pilot, deck, topology, inert)
    assert report["qualified"] is False
    assert report["powered_operation_authorized"] is False
