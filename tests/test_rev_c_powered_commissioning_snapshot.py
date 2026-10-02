import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _snapshot():
    return json.loads(
        (
            ROOT
            / "hardware/rev_c_powered_commissioning_snapshot_2026-10-01.json"
        ).read_text()
    )


def test_commissioning_snapshot_has_strict_stage_order():
    stages = sorted(_snapshot()["stages"], key=lambda item: item["stage_index"])
    assert [item["stage_index"] for item in stages] == [0, 1, 2, 3, 4]
    assert [item["stage_id"] for item in stages] == [
        "BENCH_READINESS",
        "SECURED_UNLOADED_SPIN",
        "RESTRAINED_LOADED_BENCH",
        "RIDER_FREE_CONTROLLED_GROUND",
        "RIDER_ONLY_VERY_LOW_SPEED",
    ]


def test_ground_travel_begins_rider_free_and_requires_venue():
    stages = {item["stage_id"]: item for item in _snapshot()["stages"]}
    assert stages["BENCH_READINESS"]["free_ground_travel"] is False
    assert stages["SECURED_UNLOADED_SPIN"]["free_ground_travel"] is False
    assert stages["RESTRAINED_LOADED_BENCH"]["free_ground_travel"] is False

    ground = stages["RIDER_FREE_CONTROLLED_GROUND"]
    assert ground["free_ground_travel"] is True
    assert ground["rider_present"] is False
    assert ground["venue_authority_required"] is True

    rider = stages["RIDER_ONLY_VERY_LOW_SPEED"]
    assert rider["free_ground_travel"] is True
    assert rider["rider_present"] is True
    assert rider["venue_authority_required"] is True


def test_every_energized_stage_requires_post_stage_ready_health():
    stages = _snapshot()["stages"]
    for stage in stages:
        if stage["energized"]:
            assert stage["post_stage_ready_health_required"] is True
        else:
            assert stage["post_stage_ready_health_required"] is False


def test_stage_four_requires_physical_motion_and_stopping_metrics():
    stages = {item["stage_id"]: item for item in _snapshot()["stages"]}
    metrics = set(stages["RIDER_ONLY_VERY_LOW_SPEED"]["required_measurements"])
    assert "ground_speed_mps" in metrics
    assert "longitudinal_accel_mps2" in metrics
    assert "longitudinal_jerk_mps3" in metrics
    assert "stopping_distance_m" in metrics
    assert "remote_release_propulsion_decay_s" in metrics


def test_commissioning_never_authorizes_normal_public_or_companion_operation():
    data = _snapshot()
    assert data["general_powered_operation_authorized"] is False
    assert data["public_operation_authorized"] is False
    assert data["dog_accompanied_operation_authorized"] is False

    boundaries = data["authority_boundaries"]
    assert "No Stage 0-4 report grants general powered-operation authority." in boundaries
    assert "No commissioning stage grants public-operation authority." in boundaries
    assert "No commissioning stage grants dog-accompanied-operation authority." in boundaries


def test_regen_remains_supplemental_and_stop_conditions_are_fail_closed():
    data = _snapshot()
    assert (
        "Regen remains supplemental to independent mechanical stopping."
        in data["authority_boundaries"]
    )
    stops = data["universal_stop_conditions"]
    assert "unexpected propulsion with zero command" in stops
    assert "mechanical brake unavailable or materially degraded" in stops
    assert "wheel_retention_change or critical witness movement" in stops
    assert "new lifecycle STOP_USE finding" in stops
