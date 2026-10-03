import csv
import hashlib
import json
from pathlib import Path

import pytest

from fit.platform_repeatability import qualify

HEADER = [
    "t_us",
    "left_heel_raw",
    "left_forefoot_raw",
    "right_heel_raw",
    "right_forefoot_raw",
    "load_valid_mask",
    "roll_deg",
    "imu_ok",
]


def _digest(data):
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _stamp(data):
    out = dict(data)
    out["authority_fingerprint_sha256"] = _digest(out)
    return out


def _one_zone_authority():
    return _stamp(
        {
            "schema_version": 1,
            "authority": "x1_one_zone_pilot",
            "scope": "unpowered_fit_rig_only",
            "qualified_for_four_zone_duplication": True,
            "channel": "left_heel",
            "hx711_sps": 10,
            "thresholds": {
                "min_duration_s": 5.0,
                "min_coverage": 0.98,
                "min_r2": 0.999,
                "max_residual_fs": 0.01,
                "max_hysteresis_fs": 0.015,
                "max_zero_return_fs": 0.005,
                "max_validation_error": 0.02,
                "max_noise_fs": 0.005,
                "min_loaded_gap_mm": 0.15,
                "min_unloaded_gap_mm": 0.30,
                "max_unloaded_gap_mm": 2.00,
            },
            "linear_fit": {
                "intercept": 100000.0,
                "counts_per_n": 1000.0,
                "r2": 1.0,
            },
            "mass_reference_provenance": {
                "reference_set_id": "MASS-REF-TEST",
                "authority_fingerprint_sha256": "1" * 64,
                "record_sha256": "2" * 64,
                "mass_entries": [
                    {
                        "mass_id": "CAL-2",
                        "role": "CALIBRATION",
                        "mass_kg": 2.0,
                        "uncertainty_kg": 0.002,
                        "relative_uncertainty": 0.001,
                        "evidence_type": "REFERENCE_MASS",
                    },
                    {
                        "mass_id": "CAL-5",
                        "role": "CALIBRATION",
                        "mass_kg": 5.0,
                        "uncertainty_kg": 0.005,
                        "relative_uncertainty": 0.001,
                        "evidence_type": "REFERENCE_MASS",
                    },
                    {
                        "mass_id": "CAL-10",
                        "role": "CALIBRATION",
                        "mass_kg": 10.0,
                        "uncertainty_kg": 0.010,
                        "relative_uncertainty": 0.001,
                        "evidence_type": "REFERENCE_MASS",
                    },
                    {
                        "mass_id": "VAL-7P5",
                        "role": "VALIDATION",
                        "mass_kg": 7.5,
                        "uncertainty_kg": 0.0075,
                        "relative_uncertainty": 0.001,
                        "evidence_type": "REFERENCE_MASS",
                    },
                ],
            },
            "powered_operation_authorized": False,
            "public_operation_authorized": False,
            "dog_accompanied_operation_authorized": False,
        }
    )


def _write_log(path: Path, mean_raw: float, *, seconds=6.0, sps=10, noise=2):
    n = int(seconds * sps) + 1
    with path.open("w", newline="", encoding="utf-8") as handle:
        handle.write(f"# hx711_sps={sps}\n")
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        for i in range(n):
            jitter = (i % (2 * noise + 1)) - noise if noise else 0
            writer.writerow(
                [
                    i * int(1_000_000 / sps),
                    int(round(mean_raw + jitter)),
                    "",
                    "",
                    "",
                    1,
                    "",
                    0,
                ]
            )


def _trial(tmp_path: Path):
    authority = _one_zone_authority()
    provenance = tmp_path / "provenance"
    provenance.mkdir()
    (provenance / "one_zone_pilot_authority.json").write_text(
        json.dumps(authority),
        encoding="utf-8",
    )
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    reference_raw = 100000 + 7.5 * 9.80665 * 1000
    _write_log(raw_dir / "zero_pre.csv", 100000)
    _write_log(raw_dir / "zero_post.csv", 100010)

    placements = {
        "CENTER": (0.0, 0.0, 0),
        "+X": (30.0, 0.0, 20),
        "-X": (-30.0, 0.0, -20),
        "+Y": (0.0, 20.0, 15),
        "-Y": (0.0, -20.0, -15),
    }

    rows = []
    slug = {
        "CENTER": "center",
        "+X": "plus_x",
        "-X": "minus_x",
        "+Y": "plus_y",
        "-Y": "minus_y",
    }
    for pid, (x, y, raw_bias) in placements.items():
        logs = []
        for repeat in range(1, 4):
            rel = f"raw/{slug[pid]}_{repeat:02d}.csv"
            _write_log(
                tmp_path / rel,
                reference_raw + raw_bias + (repeat - 2) * 2,
            )
            logs.append(rel)
        rows.append(
            {
                "position_id": pid,
                "centroid_x_mm": x,
                "centroid_y_mm": y,
                "contact_length_mm": 20.0,
                "contact_width_mm": 20.0,
                "stop_clearance_min_mm": 0.30,
                "fully_supported": True,
                "rocking_observed": False,
                "interference_observed": False,
                "cable_force_observed": False,
                "logs": logs,
            }
        )

    manifest = {
        "schema_version": 1,
        "scope": "x1_fit_platform_repeatability_trial",
        "issue": 63,
        "session_id": "PLATFORM-TEST",
        "one_zone_authority_fingerprint_sha256": authority[
            "authority_fingerprint_sha256"
        ],
        "one_zone_authority_path": "provenance/one_zone_pilot_authority.json",
        "zone_pad": {"length_mm": 105.0, "width_mm": 78.0},
        "load_interface": {
            "interface_id": "WEIGHT-FOOT-A",
            "contact_length_mm": 20.0,
            "contact_width_mm": 20.0,
            "notes": "",
        },
        "acquisition": {
            "no_rezero_between_position_runs": True,
            "no_recalibration_between_position_runs": True,
            "fixture_remained_secured": True,
        },
        "zero_pre_log": "raw/zero_pre.csv",
        "zero_post_log": "raw/zero_post.csv",
        "placements": rows,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
    }
    return manifest, authority


def test_good_five_position_platform_trial_qualifies(tmp_path: Path):
    manifest, authority = _trial(tmp_path)
    report = qualify(manifest, authority, tmp_path)

    assert report["qualified"] is True
    assert report["position_repeatability_qualified"] is True
    assert report["errors"] == []
    assert set(report["position_results"]) == {"CENTER", "+X", "-X", "+Y", "-Y"}
    assert len(report["run_results"]) == 15
    assert report["cross_position_spread_relative"] is not None
    assert report["cross_position_spread_relative"] > 0
    assert report["four_zone_duplication_authorized"] is False
    assert report["powered_operation_authorized"] is False
    assert len(report["authority_fingerprint_sha256"]) == 64


def test_tampered_one_zone_authority_is_rejected(tmp_path: Path):
    manifest, authority = _trial(tmp_path)
    authority["linear_fit"]["counts_per_n"] = 999.0

    report = qualify(manifest, authority, tmp_path)
    assert report["qualified"] is False
    assert "one-zone authority fingerprint/type is invalid" in report["errors"]


def test_contact_footprint_must_remain_inside_pad(tmp_path: Path):
    manifest, authority = _trial(tmp_path)
    plus_x = next(x for x in manifest["placements"] if x["position_id"] == "+X")
    plus_x["centroid_x_mm"] = 45.0

    report = qualify(manifest, authority, tmp_path)
    assert report["qualified"] is False
    assert "+X: contact footprint exceeds pad length" in report["errors"]


def test_position_signs_and_center_geometry_are_checked(tmp_path: Path):
    manifest, authority = _trial(tmp_path)
    center = next(x for x in manifest["placements"] if x["position_id"] == "CENTER")
    plus_x = next(x for x in manifest["placements"] if x["position_id"] == "+X")
    center["centroid_x_mm"] = 35.0
    plus_x["centroid_x_mm"] = -30.0

    report = qualify(manifest, authority, tmp_path)
    assert report["qualified"] is False
    assert "CENTER must have the smallest radial centroid offset" in report["errors"]
    assert "+X centroid_x_mm must be positive" in report["errors"]


def test_stop_contact_or_rocking_blocks_repeatability(tmp_path: Path):
    manifest, authority = _trial(tmp_path)
    minus_y = next(x for x in manifest["placements"] if x["position_id"] == "-Y")
    minus_y["stop_clearance_min_mm"] = 0.05
    minus_y["rocking_observed"] = True

    report = qualify(manifest, authority, tmp_path)
    assert report["qualified"] is False
    assert "-Y: stop clearance below qualified minimum" in report["errors"]
    assert "-Y: rocking_observed must be false" in report["errors"]


def test_each_position_must_pass_existing_conservative_validation_gate(tmp_path: Path):
    manifest, authority = _trial(tmp_path)
    plus_y = next(x for x in manifest["placements"] if x["position_id"] == "+Y")
    # About 2.7% force bias before reference uncertainty.
    _write_log(tmp_path / plus_y["logs"][0], 100000 + 7.5 * 9.80665 * 1000 + 2000)

    report = qualify(manifest, authority, tmp_path)
    assert report["qualified"] is False
    assert any(
        "+Y: run 1 conservative validation error above limit" in error
        for error in report["errors"]
    )


def test_rezero_or_recalibration_between_positions_is_forbidden(tmp_path: Path):
    manifest, authority = _trial(tmp_path)
    manifest["acquisition"]["no_rezero_between_position_runs"] = False
    manifest["acquisition"]["no_recalibration_between_position_runs"] = False

    report = qualify(manifest, authority, tmp_path)
    assert report["qualified"] is False
    assert (
        "acquisition.no_rezero_between_position_runs must be true"
        in report["errors"]
    )
    assert (
        "acquisition.no_recalibration_between_position_runs must be true"
        in report["errors"]
    )


def test_three_repeats_per_position_are_required(tmp_path: Path):
    manifest, authority = _trial(tmp_path)
    center = next(x for x in manifest["placements"] if x["position_id"] == "CENTER")
    center["logs"] = center["logs"][:2]

    report = qualify(manifest, authority, tmp_path)
    assert report["qualified"] is False
    assert "CENTER: need at least 3 repeated logs" in report["errors"]


def test_zero_return_reuses_issue4_gate(tmp_path: Path):
    manifest, authority = _trial(tmp_path)
    # 1 N equivalent drift across a 10 kg full-scale calibration is >0.5%.
    _write_log(tmp_path / "raw/zero_post.csv", 101000)

    report = qualify(manifest, authority, tmp_path)
    assert report["qualified"] is False
    assert "zero_return_fs above qualified Issue #4 limit" in report["errors"]


def test_malformed_pad_geometry_fails_without_exception(tmp_path: Path):
    manifest, authority = _trial(tmp_path)
    manifest["zone_pad"]["length_mm"] = None

    report = qualify(manifest, authority, tmp_path)
    assert report["qualified"] is False
    assert "zone_pad.length_mm must match 105 mm pilot pad" in report["errors"]
