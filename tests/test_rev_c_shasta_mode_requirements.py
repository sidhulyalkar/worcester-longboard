import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _requirements():
    return json.loads(
        (ROOT / "hardware/rev_c_shasta_mode_requirements.json").read_text()
    )


def test_shasta_mode_is_research_only_and_cannot_authorize_power():
    data = _requirements()
    assert data["authority"] == "RESEARCH_ONLY"
    assert data["physical_authority"] is False
    assert data["procurement_authority"] is False
    assert data["powered_operation_authorized"] is False


def test_shasta_control_envelope_is_below_existing_learn_mode_intent():
    env = _requirements()["provisional_control_envelope"]
    assert env["status"] == "UNQUALIFIED_SOFTWARE_HYPOTHESIS"
    assert env["speed_cap_mps"] == 2.7
    assert env["accel_max_mps2"] == 0.45
    assert env["regen_decel_max_mps2"] == 0.8
    assert env["phase_current_max_a"] == 18.0
    assert env["drive_current_slew_max_a_per_s"] == 20.0
    assert env["brake_current_slew_max_a_per_s"] == 30.0
    assert env["fault_release_current_slew_a_per_s"] == 60.0


def test_companion_boundary_forbids_board_leash_and_early_dog_testing():
    boundary = _requirements()["companion_boundary"]
    assert boundary["leash_attachment_to_board"] == "PROHIBITED"
    assert boundary["dog_present_during_software_or_bench_development"] is False
    assert boundary["dog_present_during_initial_rider_only_powered_qualification"] is False
    assert boundary["dog_use_requires_future_explicit_authority"] is True


def test_companion_mode_keeps_independent_brake_and_disables_deliberate_carve_assist():
    behavior = _requirements()["required_behavior"]
    assert behavior["remote_deadman_required"] is True
    assert behavior["independent_mechanical_brake_remains_required"] is True
    assert behavior["deliberate_differential_carve_assist"] is False
    assert behavior["automatic_lighting_request_when_fitted"] is True


def test_current_slew_is_not_mislabeled_as_physical_jerk():
    interpretation = _requirements()["provisional_control_envelope"][
        "interpretation"
    ]
    assert any("not physical jerk authority" in item for item in interpretation)


def test_qualification_ladder_introduces_dog_only_after_rider_only_stage():
    stages = _requirements()["qualification_ladder"]
    assert [stage["stage"] for stage in stages] == [0, 1, 2, 3]
    assert all(stage["dog_present"] is False for stage in stages[:3])
    assert stages[3]["dog_present"] is True
    assert stages[3]["requires_future_explicit_companion_authority"] is True
