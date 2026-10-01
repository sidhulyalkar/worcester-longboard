import csv
import json
import math
from pathlib import Path

from tools.analyze_rev_c_ride_compliance import analyze


def _write_run(path: Path, *, speed: float = 2.0, vibration_scale: float = 1.0):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "time_s",
                "speed_mps",
                "accel_z_mps2",
                "gyro_roll_dps",
                "gyro_yaw_dps",
            ),
        )
        writer.writeheader()
        for i in range(121):
            t = i * 0.05
            writer.writerow(
                {
                    "time_s": t,
                    "speed_mps": speed + 0.02 * math.sin(i / 8),
                    "accel_z_mps2": 9.80665
                    + vibration_scale * 0.6 * math.sin(i / 3),
                    "gyro_roll_dps": 8.0 * math.sin(i / 7),
                    "gyro_yaw_dps": 5.0 * math.sin(i / 9),
                }
            )


def _write_observations(path: Path, runs):
    fields = (
        "run_id",
        "config_id",
        "carve_response",
        "trail_chatter",
        "recentering",
        "steering_effort",
        "stability",
        "foot_fatigue",
        "confidence",
        "emergency_stepoff_ok",
        "notes",
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for run in runs:
            writer.writerow(
                {
                    "run_id": run["id"],
                    "config_id": run["config_id"],
                    "carve_response": "progressive",
                    "trail_chatter": "moderate",
                    "recentering": "predictable",
                    "steering_effort": "moderate",
                    "stability": "stable",
                    "foot_fatigue": "low",
                    "confidence": "good",
                    "emergency_stepoff_ok": "yes",
                    "notes": "",
                }
            )


def _settings(**overrides):
    values = {
        "chassis_id": "COMP95_BASELINE",
        "tire_family": "T1_200X50",
        "tire_pressure_front_kpa": 200.0,
        "tire_pressure_rear_kpa": 200.0,
        "shock_block_id": "M3_SOFT_WHITE_78A",
        "shock_block_position": "outside",
        "wheelbase_mm": 940.0,
        "deck_id": "comp95",
        "footbed_id": "stock",
    }
    values.update(overrides)
    return values


def _manifest(tmp_path: Path):
    configs = [
        {
            "id": "baseline",
            "experiment_block": "pressure",
            "primary_variable": "baseline",
            "settings": _settings(),
        },
        {
            "id": "pressure_lower",
            "experiment_block": "pressure",
            "primary_variable": "tire_pressure",
            "settings": _settings(
                tire_pressure_front_kpa=180.0,
                tire_pressure_rear_kpa=180.0,
            ),
        },
    ]
    runs = []
    for config_id, scale in (("baseline", 1.0), ("pressure_lower", 0.7)):
        for repeat in range(3):
            name = f"{config_id}_{repeat + 1:02d}"
            csv_name = f"{name}.csv"
            _write_run(tmp_path / csv_name, vibration_scale=scale)
            runs.append(
                {
                    "id": name,
                    "config_id": config_id,
                    "csv_path": csv_name,
                    "rider_observation_recorded": True,
                    "notes": "",
                }
            )
    _write_observations(tmp_path / "rider_observations.csv", runs)
    return {
        "schema_version": 1,
        "scope": "rev_c_unpowered_ride_compliance_trials",
        "session_id": "test",
        "course_id": "fixed-course",
        "surface_description": "synthetic",
        "same_course_for_all_runs": True,
        "imu_source_id": "synthetic-imu",
        "imu_mount_id": "fixed-imu",
        "imu_mount_unchanged": True,
        "speed_source_id": "synthetic-speed",
        "speed_source_calibrated": True,
        "sensor_timebase_aligned": True,
        "rider_observations_csv": "rider_observations.csv",
        "unpowered_test": True,
        "dog_or_leash_present": False,
        "tire_pressure_approved_range_kpa": [150.0, 300.0],
        "target_speed_mps": 2.0,
        "speed_tolerance_fraction": 0.10,
        "max_within_run_speed_std_fraction": 0.08,
        "max_config_median_speed_delta_fraction": 0.05,
        "minimum_samples_per_run": 100,
        "minimum_duration_s": 5.0,
        "minimum_repeats_per_config": 3,
        "baseline_config_id": "baseline",
        "configs": configs,
        "runs": runs,
        "powered_operation_authorized": False,
    }


def test_valid_speed_matched_comparison_reports_metrics_without_winner(tmp_path: Path):
    manifest = _manifest(tmp_path)
    report = analyze(manifest, tmp_path)

    assert report["valid"] is True
    assert report["physical_authority"] is False
    assert report["procurement_authority"] is False
    assert report["powered_operation_authorized"] is False
    assert "winner" not in report
    assert "score" not in report

    candidate = report["config_results"]["pressure_lower"]
    assert candidate["valid_for_comparison"] is True
    assert candidate["valid_repeat_count"] == 3
    assert (
        "roll_yaw_correlation_delta_vs_baseline"
        in candidate["relative_to_baseline"]
    )
    assert (
        "roll_yaw_correlation_pct_vs_baseline"
        not in candidate["relative_to_baseline"]
    )
    assert (
        candidate["relative_to_baseline"][
            "vertical_accel_rms_mps2_pct_vs_baseline"
        ]
        < 0
    )


def test_speed_mismatch_invalidates_run_and_comparison(tmp_path: Path):
    manifest = _manifest(tmp_path)
    bad_run = manifest["runs"][-1]
    _write_run(tmp_path / bad_run["csv_path"], speed=1.4, vibration_scale=0.7)

    report = analyze(manifest, tmp_path)
    assert report["valid"] is False
    result = next(x for x in report["run_results"] if x["id"] == bad_run["id"])
    assert result["valid"] is False
    assert any("outside" in error for error in result["errors"])
    assert (
        report["config_results"]["pressure_lower"]["valid_for_comparison"] is False
    )


def test_excessive_within_run_speed_variation_is_rejected(tmp_path: Path):
    manifest = _manifest(tmp_path)
    path = tmp_path / manifest["runs"][-1]["csv_path"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "time_s",
                "speed_mps",
                "accel_z_mps2",
                "gyro_roll_dps",
                "gyro_yaw_dps",
            ),
        )
        writer.writeheader()
        for i in range(121):
            writer.writerow(
                {
                    "time_s": i * 0.05,
                    "speed_mps": 2.0 + 0.5 * math.sin(i / 2),
                    "accel_z_mps2": 9.80665 + 0.4 * math.sin(i / 3),
                    "gyro_roll_dps": 8.0 * math.sin(i / 7),
                    "gyro_yaw_dps": 5.0 * math.sin(i / 9),
                }
            )

    report = analyze(manifest, tmp_path)
    assert report["valid"] is False
    result = next(
        x for x in report["run_results"]
        if x["id"] == manifest["runs"][-1]["id"]
    )
    assert any("speed std" in error for error in result["errors"])


def test_cross_configuration_median_speed_must_match_baseline(tmp_path: Path):
    manifest = _manifest(tmp_path)
    for run in manifest["runs"]:
        if run["config_id"] == "pressure_lower":
            _write_run(
                tmp_path / run["csv_path"],
                speed=2.18,
                vibration_scale=0.7,
            )

    report = analyze(manifest, tmp_path)
    assert report["valid"] is False
    candidate = report["config_results"]["pressure_lower"]
    assert candidate["valid_for_comparison"] is False
    assert any("median configuration speed" in error for error in candidate["errors"])


def test_nonbaseline_config_cannot_change_two_primary_variables(tmp_path: Path):
    manifest = _manifest(tmp_path)
    candidate = manifest["configs"][1]
    candidate["settings"]["shock_block_position"] = "inside"

    report = analyze(manifest, tmp_path)
    assert report["valid"] is False
    assert any("exceed primary variable tire_pressure" in error for error in report["errors"])


def test_initial_pressure_comparison_requires_symmetric_pressure(tmp_path: Path):
    manifest = _manifest(tmp_path)
    candidate = manifest["configs"][1]
    candidate["settings"]["tire_pressure_front_kpa"] = 175.0

    report = analyze(manifest, tmp_path)
    assert report["valid"] is False
    assert any("symmetric front/rear pressure" in error for error in report["errors"])


def test_subjective_observation_must_be_recorded_separately(tmp_path: Path):
    manifest = _manifest(tmp_path)
    manifest["runs"][0]["rider_observation_recorded"] = False

    report = analyze(manifest, tmp_path)
    assert report["valid"] is False
    assert any("rider_observation_recorded" in error for error in report["errors"])


def test_same_course_and_imu_mount_are_required(tmp_path: Path):
    manifest = _manifest(tmp_path)
    manifest["same_course_for_all_runs"] = False
    manifest["imu_mount_unchanged"] = False

    report = analyze(manifest, tmp_path)
    assert report["valid"] is False
    assert "same_course_for_all_runs must be true" in report["errors"]
    assert "imu_mount_unchanged must be true" in report["errors"]


def test_pressure_outside_declared_approved_range_is_rejected(tmp_path: Path):
    manifest = _manifest(tmp_path)
    manifest["configs"][1]["settings"]["tire_pressure_front_kpa"] = 120.0
    manifest["configs"][1]["settings"]["tire_pressure_rear_kpa"] = 120.0

    report = analyze(manifest, tmp_path)
    assert report["valid"] is False
    assert any("outside approved pressure range" in error for error in report["errors"])


def test_dog_or_leash_presence_is_rejected(tmp_path: Path):
    manifest = _manifest(tmp_path)
    manifest["dog_or_leash_present"] = True

    report = analyze(manifest, tmp_path)
    assert report["valid"] is False
    assert "dog_or_leash_present must be false" in report["errors"]


def test_missing_rider_observation_row_is_rejected(tmp_path: Path):
    manifest = _manifest(tmp_path)
    observations = tmp_path / "rider_observations.csv"
    with observations.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = rows[0].keys()
    with observations.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows[:-1])

    report = analyze(manifest, tmp_path)
    assert report["valid"] is False
    assert any("rider observations missing runs" in error for error in report["errors"])


def test_unaccepted_emergency_stepoff_is_rejected(tmp_path: Path):
    manifest = _manifest(tmp_path)
    observations = tmp_path / "rider_observations.csv"
    with observations.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = rows[0].keys()
    rows[0]["emergency_stepoff_ok"] = "no"
    with observations.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    report = analyze(manifest, tmp_path)
    assert report["valid"] is False
    assert any("emergency step-off was not accepted" in error for error in report["errors"])


def test_sensor_provenance_is_required(tmp_path: Path):
    manifest = _manifest(tmp_path)
    manifest["speed_source_calibrated"] = False
    manifest["sensor_timebase_aligned"] = False

    report = analyze(manifest, tmp_path)
    assert report["valid"] is False
    assert "speed_source_calibrated must be true" in report["errors"]
    assert "sensor_timebase_aligned must be true" in report["errors"]


def test_powered_operation_can_never_be_authorized(tmp_path: Path):
    manifest = _manifest(tmp_path)
    manifest["powered_operation_authorized"] = True

    report = analyze(manifest, tmp_path)
    assert report["valid"] is False
    assert report["powered_operation_authorized"] is False
