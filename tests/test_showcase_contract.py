import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_showcase_seed_is_non_authoritative_and_complete():
    seed = json.loads((ROOT / "showcase" / "x1_rev_c.json").read_text())

    assert seed["physical_authority"] is False
    assert seed["powered_operation_authorized"] is False
    assert all(
        component["evidence_state"] != "QUALIFIED"
        for component in seed["components"]
    )

    studies = seed["design_studies"]
    deck_ids = [x["id"] for x in studies["deck_candidates"]]
    topology_ids = [x["id"] for x in studies["topology_branches"]]

    assert deck_ids == ["comp95", "pro_warren_iii", "agent"]
    assert topology_ids == [
        "brake_first_400mm",
        "drive_clearance_420mm",
        "brake_hanger_70mm_topology_study",
    ]
    assert len(set(topology_ids)) == len(topology_ids)

    geometry = studies["chassis_reference"]
    assert geometry["wheelbase_mm"] == 940
    assert geometry["wheel_diameter_mm"] == 194
    assert geometry["static_ground_clearance_mm"] > geometry["minimum_compressed_clearance_mm"]
    assert geometry["max_steer_deg"] == 22


def test_topology_study_does_not_invent_combined_compatibility():
    seed = json.loads((ROOT / "showcase" / "x1_rev_c.json").read_text())
    branches = {
        branch["id"]: branch
        for branch in seed["design_studies"]["topology_branches"]
    }

    assert branches["brake_first_400mm"]["brake_reference_compatible"] is True
    assert branches["brake_first_400mm"]["drive_reference_compatible"] is False
    assert branches["drive_clearance_420mm"]["brake_reference_compatible"] is False
    assert branches["drive_clearance_420mm"]["drive_reference_compatible"] is True
    assert (
        branches["brake_hanger_70mm_topology_study"]["brake_reference_compatible"]
        == "UNKNOWN_AFTER_AXLE_SWAP"
    )
