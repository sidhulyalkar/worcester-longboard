#!/usr/bin/env python3
"""Replay validated X1 telemetry into commissioning-oriented descriptive metrics.

The summary is descriptive evidence only. It does not establish pass thresholds
or operation authority.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any

from tools.validate_x1_telemetry_session import validate as validate_session

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "hardware/x1_telemetry_contract_2026-10-01.json"


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _valid_fp(data: dict) -> bool:
    actual = data.get("authority_fingerprint_sha256")
    if not isinstance(actual, str) or not actual:
        return False
    unsigned = dict(data)
    unsigned.pop("authority_fingerprint_sha256", None)
    try:
        return actual == _digest(unsigned)
    except (TypeError, ValueError):
        return False


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _series(rows: list[dict[str, str]], column: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        try:
            value = float(row[column])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(value):
            values.append(value)
    return values


def _times(rows: list[dict[str, str]]) -> list[float]:
    return _series(rows, "time_s")


def _metric(
    metric_id: str,
    value: float,
    unit: str,
    statistic: str,
    source_stream: str,
    derivation: str,
) -> dict:
    return {
        "metric_id": metric_id,
        "value": round(float(value), 6),
        "unit": unit,
        "statistic": statistic,
        "source_stream": source_stream,
        "derivation": derivation,
    }


def _max_abs(rows: list[dict[str, str]], column: str) -> float | None:
    values = _series(rows, column)
    return max((abs(x) for x in values), default=None)


def _max_value(rows: list[dict[str, str]], column: str) -> float | None:
    values = _series(rows, column)
    return max(values) if values else None


def _min_value(rows: list[dict[str, str]], column: str) -> float | None:
    values = _series(rows, column)
    return min(values) if values else None


def _moving_average(values: list[float], window: int) -> list[float]:
    radius = window // 2
    out: list[float] = []
    for index in range(len(values)):
        start = max(0, index - radius)
        stop = min(len(values), index + radius + 1)
        out.append(statistics.fmean(values[start:stop]))
    return out


def _remote_release_decay(
    control_rows: list[dict[str, str]],
    event_rows: list[dict[str, str]],
    threshold_a: float,
    hold_s: float,
) -> float | None:
    times = _times(control_rows)
    left = _series(control_rows, "drive_command_left_a")
    right = _series(control_rows, "drive_command_right_a")
    if not times or len(times) != len(left) or len(times) != len(right):
        return None

    release_times = []
    for row in event_rows:
        if str(row.get("event_code", "")).strip() != "REMOTE_DEADMAN_RELEASE":
            continue
        try:
            t = float(row["time_s"])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(t):
            release_times.append(t)

    decays: list[float] = []
    for release_t in release_times:
        for index, t in enumerate(times):
            if t < release_t:
                continue
            if max(abs(left[index]), abs(right[index])) > threshold_a:
                continue

            hold_end = t + hold_s
            seen_hold_end = False
            remained_below = True
            for j in range(index, len(times)):
                if max(abs(left[j]), abs(right[j])) > threshold_a:
                    remained_below = False
                    break
                if times[j] >= hold_end:
                    seen_hold_end = True
                    break
            if remained_below and seen_hold_end:
                decays.append(t - release_t)
                break

    return max(decays) if decays and len(decays) == len(release_times) else None


def _interp(times: list[float], values: list[float], target: float) -> float | None:
    if not times or target < times[0] or target > times[-1]:
        return None
    for i, t in enumerate(times):
        if t == target:
            return values[i]
        if t > target and i > 0:
            t0, t1 = times[i - 1], t
            v0, v1 = values[i - 1], values[i]
            if t1 == t0:
                return None
            alpha = (target - t0) / (t1 - t0)
            return v0 + alpha * (v1 - v0)
    return values[-1]


def _integrate_abs_speed(
    motion_rows: list[dict[str, str]],
    start_t: float,
    stop_t: float,
) -> float | None:
    if stop_t <= start_t:
        return None
    times = _times(motion_rows)
    speeds = _series(motion_rows, "ground_speed_mps")
    if len(times) != len(speeds) or len(times) < 2:
        return None

    start_speed = _interp(times, speeds, start_t)
    stop_speed = _interp(times, speeds, stop_t)
    if start_speed is None or stop_speed is None:
        return None

    points = [(start_t, start_speed)]
    points.extend(
        (t, v)
        for t, v in zip(times, speeds)
        if start_t < t < stop_t
    )
    points.append((stop_t, stop_speed))

    distance = 0.0
    for (t0, v0), (t1, v1) in zip(points, points[1:]):
        distance += 0.5 * (abs(v0) + abs(v1)) * (t1 - t0)
    return distance


def _stopping_distance(
    motion_rows: list[dict[str, str]],
    event_rows: list[dict[str, str]],
) -> float | None:
    events: list[tuple[float, str]] = []
    for row in event_rows:
        try:
            t = float(row.get("time_s", ""))
        except (TypeError, ValueError):
            continue
        code = str(row.get("event_code", "")).strip()
        if math.isfinite(t) and code:
            events.append((t, code))

    distances: list[float] = []
    for index, (start_t, code) in enumerate(events):
        if code != "STOPPING_START":
            continue
        stop_t = next(
            (
                t
                for t, later_code in events[index + 1 :]
                if later_code == "VEHICLE_STOPPED" and t > start_t
            ),
            None,
        )
        if stop_t is None:
            return None
        distance = _integrate_abs_speed(motion_rows, start_t, stop_t)
        if distance is None:
            return None
        distances.append(distance)
    return max(distances) if distances else None


def _jerk(
    motion_rows: list[dict[str, str]],
    accel_column: str,
    window: int,
) -> float | None:
    times = _times(motion_rows)
    accel = _series(motion_rows, accel_column)
    if len(times) != len(accel) or len(times) < 2:
        return None
    smooth = _moving_average(accel, window)
    jerks: list[float] = []
    for t0, t1, a0, a1 in zip(times, times[1:], smooth, smooth[1:]):
        dt = t1 - t0
        if dt <= 0:
            return None
        jerks.append((a1 - a0) / dt)
    return max((abs(x) for x in jerks), default=None)


def summarize(
    manifest: dict,
    base_dir: Path,
    telemetry_authority: dict,
    power_architecture: dict,
    contract: dict | None = None,
) -> dict:
    contract = contract or json.loads(CONTRACT.read_text(encoding="utf-8"))
    errors: list[str] = []

    fresh_authority = validate_session(
        manifest,
        base_dir,
        power_architecture,
        contract,
    )
    if fresh_authority.get("valid") is not True:
        errors.append("current telemetry files/manifest no longer validate")
        errors.extend(fresh_authority.get("errors", []))

    if (
        telemetry_authority.get("authority") != "x1_telemetry_session"
        or telemetry_authority.get("valid") is not True
        or not _valid_fp(telemetry_authority)
    ):
        errors.append("telemetry authority must be valid and fingerprint-valid")
    elif (
        telemetry_authority.get("authority_fingerprint_sha256")
        != fresh_authority.get("authority_fingerprint_sha256")
    ):
        errors.append(
            "telemetry authority does not match current manifest/files/power lineage"
        )

    stage_id = manifest.get("commissioning_stage_id")
    stage_req = contract.get("stage_requirements", {}).get(stage_id, {})
    required_metrics = list(stage_req.get("required_metric_ids", []))

    stream_paths = {
        stream["stream_type"]: (base_dir / stream["file_path"]).resolve()
        for stream in manifest.get("streams", [])
        if isinstance(stream, dict)
        and isinstance(stream.get("stream_type"), str)
        and isinstance(stream.get("file_path"), str)
    }
    rows = {
        stream_type: _load_csv(path)
        for stream_type, path in stream_paths.items()
        if path.is_file()
    }

    metrics: dict[str, dict] = {}
    electrical = rows.get("electrical", [])
    motion = rows.get("motion", [])
    control = rows.get("control", [])
    events = rows.get("events", [])

    simple_specs = {
        "pack_voltage_v": (
            electrical,
            "pack_voltage_v",
            "V",
            "minimum",
            _min_value,
        ),
        "battery_current_a": (
            electrical,
            "battery_current_a",
            "A",
            "peak_absolute",
            _max_abs,
        ),
        "left_phase_current_a": (
            electrical,
            "left_phase_current_a",
            "A",
            "peak_absolute",
            _max_abs,
        ),
        "right_phase_current_a": (
            electrical,
            "right_phase_current_a",
            "A",
            "peak_absolute",
            _max_abs,
        ),
        "left_motor_erpm": (
            electrical,
            "left_motor_erpm",
            "erpm",
            "peak_absolute",
            _max_abs,
        ),
        "right_motor_erpm": (
            electrical,
            "right_motor_erpm",
            "erpm",
            "peak_absolute",
            _max_abs,
        ),
        "left_motor_speed": (
            electrical,
            "left_motor_speed_rpm",
            "rpm",
            "peak_absolute",
            _max_abs,
        ),
        "right_motor_speed": (
            electrical,
            "right_motor_speed_rpm",
            "rpm",
            "peak_absolute",
            _max_abs,
        ),
        "left_motor_temperature_c": (
            electrical,
            "left_motor_temperature_c",
            "degC",
            "maximum",
            _max_value,
        ),
        "right_motor_temperature_c": (
            electrical,
            "right_motor_temperature_c",
            "degC",
            "maximum",
            _max_value,
        ),
        "left_controller_temperature_c": (
            electrical,
            "left_controller_temperature_c",
            "degC",
            "maximum",
            _max_value,
        ),
        "right_controller_temperature_c": (
            electrical,
            "right_controller_temperature_c",
            "degC",
            "maximum",
            _max_value,
        ),
        "ground_speed_mps": (
            motion,
            "ground_speed_mps",
            "m/s",
            "peak_absolute",
            _max_abs,
        ),
    }

    for metric_id, (source_rows, column, unit, statistic, reducer) in simple_specs.items():
        if metric_id not in required_metrics:
            continue
        value = reducer(source_rows, column)
        if value is None:
            errors.append(f"cannot derive required metric: {metric_id}")
            continue
        metrics[metric_id] = _metric(
            metric_id,
            value,
            unit,
            statistic,
            "electrical" if source_rows is electrical else "motion",
            f"{statistic} of {column} over validated session",
        )

    processing = manifest.get("processing", {})
    if "longitudinal_accel_mps2" in required_metrics:
        accel_column = processing.get("longitudinal_accel_column")
        value = _max_abs(motion, accel_column)
        if value is None:
            errors.append("cannot derive longitudinal_accel_mps2")
        else:
            metrics["longitudinal_accel_mps2"] = _metric(
                "longitudinal_accel_mps2",
                value,
                "m/s^2",
                "peak_absolute",
                "motion",
                f"peak absolute validated motion column {accel_column}",
            )

    if "longitudinal_jerk_mps3" in required_metrics:
        accel_column = processing.get("longitudinal_accel_column")
        window = processing.get("jerk_smoothing_window_samples")
        value = (
            _jerk(motion, accel_column, window)
            if isinstance(window, int) and window > 0
            else None
        )
        if value is None:
            errors.append("cannot derive longitudinal_jerk_mps3")
        else:
            metrics["longitudinal_jerk_mps3"] = _metric(
                "longitudinal_jerk_mps3",
                value,
                "m/s^3",
                "peak_absolute",
                "motion",
                (
                    f"peak absolute first difference of centered moving-average "
                    f"{accel_column}; window={window} samples"
                ),
            )

    if "remote_release_propulsion_decay_s" in required_metrics:
        threshold = processing.get("propulsion_zero_threshold_a")
        hold = processing.get("propulsion_zero_hold_s")
        value = (
            _remote_release_decay(control, events, float(threshold), float(hold))
            if isinstance(threshold, (int, float))
            and isinstance(hold, (int, float))
            and threshold > 0
            and hold > 0
            else None
        )
        if value is None:
            errors.append("cannot derive remote_release_propulsion_decay_s")
        else:
            metrics["remote_release_propulsion_decay_s"] = _metric(
                "remote_release_propulsion_decay_s",
                value,
                "s",
                "maximum_complete_event",
                "control+events",
                (
                    "maximum REMOTE_DEADMAN_RELEASE to first both-side drive-command "
                    f"below {float(threshold):g} A for at least {float(hold):g} s"
                ),
            )

    if "stopping_distance_m" in required_metrics:
        value = _stopping_distance(motion, events)
        if value is None:
            errors.append("cannot derive stopping_distance_m")
        else:
            metrics["stopping_distance_m"] = _metric(
                "stopping_distance_m",
                value,
                "m",
                "maximum_complete_event",
                "motion+events",
                (
                    "maximum trapezoidal integral of absolute ground speed between "
                    "STOPPING_START and following VEHICLE_STOPPED markers"
                ),
            )

    missing_metrics = sorted(set(required_metrics) - set(metrics))
    for metric_id in missing_metrics:
        if not any(metric_id in error for error in errors):
            errors.append(f"required metric not produced: {metric_id}")

    valid = not errors
    report = {
        "schema_version": 1,
        "authority": "x1_commissioning_telemetry_summary",
        "valid": valid,
        "errors": errors,
        "issue": 47,
        "session_id": manifest.get("session_id"),
        "board_id": manifest.get("board_id"),
        "configuration_id": manifest.get("configuration_id"),
        "commissioning_stage_id": stage_id,
        "power_architecture_fingerprint_sha256": manifest.get(
            "power_architecture_fingerprint_sha256"
        ),
        "telemetry_session_fingerprint_sha256": telemetry_authority.get(
            "authority_fingerprint_sha256"
        ),
        "required_metric_ids": required_metrics,
        "metrics": [metrics[key] for key in required_metrics if key in metrics],
        "all_required_metrics_derived": valid and not missing_metrics,
        "pass_threshold_authority": False,
        "physical_vehicle_authority": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
        "interpretation_boundary": (
            "This summary is a reproducible descriptive replay of validated private "
            "telemetry. It does not define pass thresholds or authorize operation."
        ),
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--telemetry-authority", type=Path, required=True)
    parser.add_argument("--power-architecture", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    authority = json.loads(args.telemetry_authority.read_text(encoding="utf-8"))
    power = json.loads(args.power_architecture.read_text(encoding="utf-8"))
    contract = json.loads(args.contract.read_text(encoding="utf-8"))

    report = summarize(
        manifest,
        manifest_path.parent,
        authority,
        power,
        contract,
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["valid"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
