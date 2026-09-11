import copy
import json
from pathlib import Path

import pytest

from tools.evaluate_build_authority import evaluate, _validate_plan

ROOT = Path(__file__).resolve().parents[1]


def _plan():
    return json.loads((ROOT / "hardware/build_authority.json").read_text())


def _procurement():
    return json.loads((ROOT / "hardware/procurement_manifest.json").read_text())


def _all_physical_evidence():
    return [
        {
            "qualified_for_four_zone_duplication": True,
            "authority_fingerprint_sha256": "a" * 64,
        },
        {
            "rev_b_gate": {"ready_for_rev_b_fit_cad": True},
        },
        {
            "authority": "x1_mechanical_brake_interface",
            "qualified": True,
            "brake_interface_verified": True,
            "powered_operation_authorized": False,
        },
        {
            "authority": "x1_rolling_chassis_physical",
            "qualified": True,
            "powered_operation_authorized": False,
        },
        {
            "authority": "x1_rev_b_template",
            "qualified": True,
        },
        {
            "authority": "x1_power_architecture",
            "qualified": True,
        },
    ]


def test_public_repo_defaults_are_conservative():
    report = evaluate(_plan(), _procurement(), [])
    assert report["capabilities"]["order_fit_pilot_parts"]["allowed"] is True
    assert report["capabilities"]["order_measurement_chassis_parts"]["allowed"] is True
    assert report["capabilities"]["duplicate_four_fit_zones"]["allowed"] is False
    assert report["capabilities"]["fabricate_unpowered_chassis"]["allowed"] is False
    assert report["capabilities"]["order_power_hardware"]["allowed"] is False
    assert report["capabilities"]["powered_operation"]["allowed"] is False


def test_downstream_evidence_cannot_skip_upstream_gate():
    evidence = [{
        "authority": "x1_rolling_chassis_physical",
        "qualified": True,
        "powered_operation_authorized": False,
    }]
    report = evaluate(_plan(), _procurement(), evidence)
    state = report["gates"]["rolling_chassis_physical_qualified"]
    assert state["evidence_matched"] is True
    assert state["satisfied"] is False
    assert any("brake_interface_qualified" in x for x in state["blockers"])


def test_power_ordering_stays_blocked_by_procurement_policy():
    report = evaluate(_plan(), _procurement(), _all_physical_evidence())
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


def test_gate_cycles_are_rejected():
    plan = _plan()
    plan["gates"]["fit_pilot_qualified"]["requires"] = ["power_architecture_frozen"]
    with pytest.raises(ValueError, match="cycle"):
        _validate_plan(plan)
