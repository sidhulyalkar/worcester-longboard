import hashlib
import json
from pathlib import Path

from tools.render_procurement_packet import render_packet

ROOT = Path(__file__).resolve().parents[1]


def test_public_packet_is_actionable_and_fail_closed():
    plan = json.loads((ROOT / "hardware/build_authority.json").read_text())
    procurement = json.loads((ROOT / "hardware/procurement_manifest.json").read_text())
    text = render_packet(plan, procurement)
    assert "**$120.90**" in text
    assert "LC-3135" in text
    assert "FEELER-GAUGE" in text
    assert "DONOR-COMP95" in text
    assert "BRAKE-V5" in text
    assert "TRUCK-M3-400 | MEASURE_FIRST" in text
    assert "required release gate blocked: rev_c_chassis_release_qualified" in text
    assert "TIRE-T2-9 | MEASURE_FIRST | MEASURE_FIRST item lacks required_for issue authority" in text
    assert "DRIVE-G1-DUAL | POWER_GATED | POWER_GATED is not authorized" in text
    assert "four-zone duplication: **BLOCKED**" in text
    assert "power ordering: **BLOCKED**" in text
    assert "powered operation: **BLOCKED**" in text


def _stamp(doc):
    payload = json.dumps(
        doc, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    stamped = dict(doc)
    stamped["authority_fingerprint_sha256"] = hashlib.sha256(payload).hexdigest()
    return stamped


def test_private_packet_can_open_only_preferred_measurement_items_with_release_evidence():
    plan = json.loads((ROOT / "hardware/build_authority.json").read_text())
    procurement = json.loads((ROOT / "hardware/procurement_manifest.json").read_text())
    fit = _stamp({
        "authority": "x1_one_zone_pilot",
        "scope": "unpowered_fit_rig_only",
        "qualified_for_four_zone_duplication": True,
        "powered_operation_authorized": False,
        "hardware_provenance": {
            "selection_authority_fingerprint_sha256": "1" * 64,
            "selection_record_sha256": "2" * 64,
        },
        "mass_reference_provenance": {
            "authority_fingerprint_sha256": "3" * 64,
            "record_sha256": "4" * 64,
        },
    })
    release = _stamp(
        {
            "authority": "x1_rev_c_chassis_release",
            "schema_version": 1,
            "qualified": True,
            "deck_envelope_comparison_completed": True,
            "selected_deck_candidate_id": "comp95_class",
            "selected_chassis_family": "COMP95_BASELINE",
            "selected_wheel_family": "MBS_RSII_200X50",
            "selected_brake_architecture": "MBS_V5_REAR",
            "selected_topology_for_measurement": "REAR_V5_REAR_2WD_SHARED",
            "range_pack_inert_envelope_plausible": True,
            "no_unqualified_safety_critical_adapter": True,
            "powered_operation_authorized": False,
        }
    )
    text = render_packet(plan, procurement, [fit, release])
    assert "using 2 supplied evidence document(s)" in text
    assert "| DONOR-COMP95 | 1 | MBS / 10303 | $499.95 | issues-12-14 |" in text
    assert "| BRAKE-V5 | 1 | MBS / 15006 | $89.95 | issue-14 |" in text
    assert "TRUCK-M3-400 | MEASURE_FIRST | fallback blocked" in text
    assert "DRIVE-G1-DUAL | POWER_GATED | POWER_GATED is not authorized" in text
    assert "power ordering: **BLOCKED**" in text
    assert "powered operation: **BLOCKED**" in text
