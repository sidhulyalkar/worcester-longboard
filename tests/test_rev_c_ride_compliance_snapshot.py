import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _snapshot():
    return json.loads(
        (
            ROOT / "hardware/rev_c_ride_compliance_snapshot_2026-10-01.json"
        ).read_text()
    )


def test_compliance_snapshot_prioritizes_lightweight_reversible_tuning():
    data = _snapshot()
    assert data["schema_version"] == 1
    assert data["facts_only"] is True

    layers = sorted(data["compliance_layers"], key=lambda x: x["order"])
    assert [x["order"] for x in layers] == list(range(1, 8))
    assert [x["mechanism"] for x in layers[:3]] == [
        "pneumatic_tire",
        "truck_elastomer_position",
        "wheelbase",
    ]
    assert layers[-1]["mechanism"] == "independent_suspension"


def test_stock_matrix_400_reference_starts_soft_and_brake_compatible():
    data = _snapshot()
    trucks = {
        item["id"]: item for item in data["matrix_iii"]["truck_references"]
    }
    truck = trucks["M3_CNC_400"]
    assert truck["stock_shock_block"] == "M3_SOFT_WHITE_78A"
    assert truck["stock_position"] == "outside"
    assert truck["brake_compatible"] is True
    assert truck["direct_agent_gear_drive_compatible"] is False


def test_soft_block_reference_exposes_position_before_hardness_purchase():
    data = _snapshot()
    blocks = {item["id"]: item for item in data["matrix_iii"]["shock_blocks"]}
    soft = blocks["M3_SOFT_WHITE_78A"]
    assert soft["durometer_a"] == 78
    assert "maximum carve" in soft["vendor_guidance"]["inside"]
    assert "balance" in soft["vendor_guidance"]["outside"]


def test_compliance_snapshot_does_not_authorize_accessory_shopping():
    policy = _snapshot()["procurement_policy"]
    assert policy["buy_new_shock_blocks_now"] is False
    assert policy["buy_explorer_wheels_now"] is False
    assert policy["buy_9inch_wheels_now"] is False
    assert policy["buy_suspension_now"] is False


def test_experimental_invariants_keep_objective_and_subjective_results_separate():
    invariants = _snapshot()["experimental_invariants"]
    assert any("one primary compliance variable" in x for x in invariants)
    assert any("Subjective snowboard feel" in x for x in invariants)
    assert any("No powered compliance test" in x for x in invariants)
