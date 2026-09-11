import copy
import hashlib
import json
from pathlib import Path

import pytest

from tools.evaluate_build_authority import evaluate, _validate_plan

ROOT = Path(__file__).resolve().parents[1]


def _plan():
    return json.loads((ROOT / "hardware/build_authority.json").read_text())


def _procurement():
    return json.loads((ROOT / "hardware/procurement_manifest.json").read_text())


def _stamp(doc):
    payload = json.dumps(doc, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    stamped = dict(doc)
    stamped["authority_fingerprint_sha256"] = hashlib.sha256(payload).hexdigest()
    return stamped


def _all_physical_evidence():
    return [
        _stamp({"qualified_for_four_zone_duplication": True}),
        _stamp({"authority": "x1_fit_session", "schema_version": 2, "rev_b_gate": {"ready_for_rev_b_fit_cad": True}}),
        _stamp({"authority": "x1_mechanical_brake_interface", "qualified": True, "brake_interface_verified": True, "powered_operation_authorized": False}),
        _stamp({"authority": "x1_rolling_chassis_physical", "qualified": True, "powered_operation_authorized": False}),
        _stamp({"authority": "x1_brake_drive_topology", "schema_version": 1, "qualified": True, "selected_topology": "same_rear_axle_v5_plus_drive", "powered_operation_authorized": False}),
        _stamp({"authority": "x1_rev_b_template", "qualified": True}),
        _stamp({"authority": "x1_power_architecture", "qualified": True}),
    ]


def test_public_repo_defaults_are_conservative():
    report = evaluate(_plan(), _procurement(), [])
    assert report["capabilities"]["order_fit_pilot_parts"]["allowed"] is True
    assert report["capabilities"]["order_measurement_chassis_parts"]["allowed"] is True
    assert report["capabilities"]["duplicate_four_fit_zones"]["allowed"] is False
    assert report["capabilities"]["fabricate_unpowered_chassis"]["allowed"] is False
    assert report["capabilities"]["qualify_brake_drive_topology"]["allowed"] is False
    assert report["capabilities"]["order_power_hardware"]["allowed"] is False
    assert report["capabilities"]["powered_operation"]["allowed"] is False


def test_measurement_procurement_is_item_level_and_preferred_path_exclusive():
    report = evaluate(_plan(), _procurement(), [])
    items = report["procurement_items"]
    assert report["procurement_stage_authorized"]["MEASURE_FIRST"] is True
    assert items["DONOR-COMP95"]["orderable"] is True
    assert items["BRAKE-V5"]["orderable"] is True
    assert items["TRUCK-M3-400"]["orderable"] is False
    assert items["HUB-RSII"]["orderable"] is False
    assert any("preferred chassis item" in x for x in items["TRUCK-M3-400"]["blockers"])
    assert items["TIRE-T2-9"]["orderable"] is False
    assert items["TUBE-9"]["orderable"] is False
    assert items["AXLE-M3-70"]["orderable"] is False
    assert any("deferred until" in blocker for blocker in items["AXLE-M3-70"]["blockers"])


def test_fallback_can_only_open_after_explicit_strategy_change():
    procurement = copy.deepcopy(_procurement())
    procurement["rules"]["preferred_chassis_item_id"] = None
    report = evaluate(_plan(), procurement, [])
    assert report["procurement_items"]["TRUCK-M3-400"]["orderable"] is True
    assert report["procurement_items"]["HUB-RSII"]["orderable"] is True


def test_downstream_evidence_cannot_skip_upstream_gate():
    evidence = [_stamp({"authority": "x1_rolling_chassis_physical", "qualified": True, "powered_operation_authorized": False})]
    report = evaluate(_plan(), _procurement(), evidence)
    state = report["gates"]["rolling_chassis_physical_qualified"]
    assert state["evidence_matched"] is True
    assert state["satisfied"] is False
    assert any("brake_interface_qualified" in x for x in state["blockers"])


def test_topology_evidence_cannot_skip_brake_or_chassis():
    topology = _stamp({
        "authority": "x1_brake_drive_topology",
        "schema_version": 1,
        "qualified": True,
        "selected_topology": "same_rear_axle_v5_plus_drive",
        "powered_operation_authorized": False,
    })
    report = evaluate(_plan(), _procurement(), [topology])
    state = report["gates"]["brake_drive_topology_qualified"]
    assert state["evidence_matched"] is True
    assert state["satisfied"] is False
    assert any("brake_interface_qualified" in x for x in state["blockers"])
    assert any("rolling_chassis_physical_qualified" in x for x in state["blockers"])


def test_power_architecture_cannot_freeze_without_topology_authority():
    evidence = [x for x in _all_physical_evidence() if x.get("authority") != "x1_brake_drive_topology"]
    report = evaluate(_plan(), _procurement(), evidence)
    assert report["gates"]["power_architecture_frozen"]["satisfied"] is False
    assert any("brake_drive_topology_qualified" in x for x in report["gates"]["power_architecture_frozen"]["blockers"])


def test_power_ordering_stays_blocked_by_procurement_policy():
    report = evaluate(_plan(), _procurement(), _all_physical_evidence())
    assert report["gates"]["brake_drive_topology_qualified"]["satisfied"] is True
    assert report["gates"]["power_architecture_frozen"]["satisfied"] is True
    assert report["capabilities"]["order_power_hardware"]["allowed"] is False
    assert "procurement stage blocked: POWER_GATED" in report["capabilities"]["order_power_hardware"]["blockers"]
    assert report["capabilities"]["powered_operation"]["allowed"] is False


def test_future_power_ordering_requires_explicit_manifest_promotion():
    procurement = copy.deepcopy(_procurement())
    procurement["rules"]["power_gated_authorized"] = True
    report = evaluate(_plan(), procurement, _all_physical_evidence())
    assert report["capabilities"]["order_power_hardware"]["allowed"] is True
    assert report["capabilities"]["powered_operation"]["allowed"] is False


def test_tampered_evidence_fingerprint_is_rejected():
    evidence = _all_physical_evidence()
    evidence[2]["brake_interface_verified"] = False
    report = evaluate(_plan(), _procurement(), evidence)
    assert report["gates"]["brake_interface_qualified"]["satisfied"] is False


def test_gate_cycles_are_rejected():
    plan = _plan()
    plan["gates"]["fit_pilot_qualified"]["requires"] = ["power_architecture_frozen"]
    with pytest.raises(ValueError, match="cycle"):
        _validate_plan(plan)
