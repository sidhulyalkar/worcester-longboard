import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _snapshot():
    return json.loads(
        (
            ROOT / "hardware/rev_c_public_use_constraints_2026-10-01.json"
        ).read_text()
    )


def test_public_use_snapshot_never_authorizes_operation():
    data = _snapshot()
    assert data["authority"] == "INFORMATIONAL_ONLY"
    assert data["public_operation_authorized"] is False


def test_california_emb_definition_keeps_sub_1000w_and_20mph_boundaries_explicit():
    reqs = _snapshot()["california"]["electrically_motorized_board_definition"][
        "requirements"
    ]
    assert any("averaging less than 1000 watts" in item for item in reqs)
    assert any("no more than 20 mph" in item for item in reqs)


def test_software_derate_is_not_assumed_to_change_vehicle_classification():
    boundary = _snapshot()["california"]["classification_boundary"]
    assert boundary["software_derate_not_assumed_to_change_classification"] is True
    assert boundary["high_power_trail_architecture_public_road_status"] == (
        "NOT_ESTABLISHED"
    )


def test_worcester_park_is_terrain_reference_not_assumed_test_venue():
    park = _snapshot()["los_gatos"]["worcester_park"]
    assert park["town_park"] is True
    assert park["ride_test_venue_status"] == (
        "BLOCKED_BY_CURRENT_TOWN_PARK_SKATEBOARD_RULE"
    )
    assert "terrain" in park["role_in_project"]


def test_public_and_trail_architecture_paths_remain_distinct():
    fork = _snapshot()["product_architecture_fork"]
    assert fork["trail_private_authorized"]["regulatory_category_assumed"] is False
    assert (
        fork["public_road_oriented_derivative"]["software_only_power_limit_sufficient"]
        is False
    )
