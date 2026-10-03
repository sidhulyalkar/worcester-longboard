import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _snapshot():
    return json.loads(
        (
            ROOT / "hardware/rev_c_telemetry_reference_snapshot_2026-10-02.json"
        ).read_text()
    )


def _signals():
    return json.loads(
        (
            ROOT / "hardware/x1_telemetry_signal_registry_2026-10-02.json"
        ).read_text()
    )


def test_logging_is_never_a_control_dependency():
    boundary = _snapshot()["logging_boundary"]
    assert boundary["real_time_control_dependency"] is False
    assert boundary["logger_failure_may_invalidate_evidence"] is True
    assert boundary["logger_failure_may_preserve_unsafe_propulsion"] is False


def test_telemetry_validity_never_proves_safety_or_calibration():
    boundary = _snapshot()["logging_boundary"]
    assert boundary["telemetry_validity_proves_physical_calibration"] is False
    assert boundary["telemetry_validity_proves_vehicle_safety"] is False
    assert boundary["telemetry_validity_authorizes_powered_operation"] is False


def test_stage_zero_does_not_require_raw_telemetry_but_energized_stages_do():
    stages = _snapshot()["commissioning_integration"]
    assert stages["BENCH_READINESS"]["telemetry_required"] is False
    for stage_id in (
        "SECURED_UNLOADED_SPIN",
        "RESTRAINED_LOADED_BENCH",
        "RIDER_FREE_CONTROLLED_GROUND",
        "RIDER_ONLY_VERY_LOW_SPEED",
    ):
        assert stages[stage_id]["telemetry_required"] is True


def test_clock_contract_does_not_assume_shared_device_time():
    contract = _snapshot()["clock_contract"]
    assert contract["raw_streams_may_have_independent_clocks"] is True
    assert contract["synchronization_declared_required"] is True
    assert contract["sync_uncertainty_required"] is True
    assert contract["minimum_required_stream_overlap_fraction"] == 0.90


def test_raw_private_data_does_not_belong_in_public_repo():
    privacy = _snapshot()["privacy"]
    assert privacy["raw_session_data"] == "rider/private/"
    assert privacy["precise_routes_public"] is False
    assert privacy["serials_public"] is False
    assert privacy["personal_motion_public"] is False


def test_signal_registry_requires_provenance_and_derivation_identity():
    contract = _signals()["provenance_contract"]
    assert contract["every_stream_signal_declares_source_id"] is True
    assert contract["calibration_id_required_for_physical_calibration_claim"] is False
    assert contract["derived_signal_requires_derivation_id"] is True
