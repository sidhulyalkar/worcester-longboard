from pathlib import Path

from tools.validate_shasta_control_contract import validate

ROOT = Path(__file__).resolve().parents[1]


def test_shasta_contract_matches_controller_and_remains_non_authoritative():
    report = validate()
    assert report["valid"] is True
    assert report["physical_authority"] is False
    assert report["procurement_authority"] is False
    assert report["powered_operation_authorized"] is False
    assert report["parsed_controller_envelope"] == {
        "speed_cap_mps": 2.7,
        "accel_max_mps2": 0.45,
        "regen_decel_max_mps2": 0.8,
        "phase_current_max_a": 18.0,
        "drive_current_slew_max_a_per_s": 20.0,
        "brake_current_slew_max_a_per_s": 30.0,
        "fault_release_current_slew_a_per_s": 60.0,
    }


def test_shasta_contract_detects_controller_limit_drift(tmp_path: Path):
    source = (
        ROOT / "firmware/src/x1_control_core.cpp"
    ).read_text(encoding="utf-8")
    source = source.replace(
        "case RideMode::Shasta: return {2.70f, 0.45f,0.80f,18.0f, 20.0f, 30.0f, 60.0f};",
        "case RideMode::Shasta: return {3.20f, 0.45f,0.80f,18.0f, 20.0f, 30.0f, 60.0f};",
    )
    drifted = tmp_path / "x1_control_core.cpp"
    drifted.write_text(source, encoding="utf-8")

    report = validate(
        ROOT / "hardware/rev_c_shasta_mode_requirements.json",
        ROOT / "firmware/include/x1_control_core.hpp",
        drifted,
    )
    assert report["valid"] is False
    assert any("speed_cap_mps mismatch" in error for error in report["errors"])
