#!/usr/bin/env python3
"""Summarize a private four-zone SnowDeck bench force log without ranking setups."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from fit.static_load import summarize as summarize_static

REQUIRED_POSES = ("NEUTRAL", "DEEP_KNEE", "HEEL_BIASED", "TOE_BIASED")
REQUIRED_COLUMNS = (
    "trial_id",
    "pose",
    "left_heel",
    "left_forefoot",
    "right_heel",
    "right_forefoot",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [name for name in REQUIRED_COLUMNS if name not in (reader.fieldnames or [])]
        if missing:
            raise ValueError("force log missing columns: " + ", ".join(missing))
        rows = list(reader)
    if not rows:
        raise ValueError("force log is empty")
    return rows


def pose_summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    summary = summarize_static(rows)
    sensor_means = summary["sensor_means"]
    return {
        "samples": summary["samples"],
        "mean_total_load": sum(sensor_means.values()),
        "left_load_fraction": summary["left_load_fraction"],
        "right_load_fraction": summary["right_load_fraction"],
        "left_forefoot_fraction": summary["left_forefoot_fraction"],
        "right_forefoot_fraction": summary["right_forefoot_fraction"],
    }


def _mean_sd(values: list[float]) -> dict[str, float]:
    return {
        "mean": mean(values),
        "sd": pstdev(values) if len(values) > 1 else 0.0,
    }


def mechanical_rejects(session: dict[str, Any] | None) -> list[str]:
    if session is None:
        return []
    rejects: list[str] = []
    for trial in session.get("trials", []):
        tid = str(trial.get("id", "trial"))
        if trial.get("emergency_step_off_clear") is not True:
            rejects.append(f"{tid}: emergency step-off not confirmed clear")
        for key, label in (
            ("unexpected_rocking_observed", "unexpected rocking"),
            ("insert_or_fastener_migration_observed", "insert/fastener migration"),
            ("fixture_interference_observed", "fixture interference"),
            ("persistent_deformation_observed", "persistent deformation"),
            ("overload_stop_contact_observed", "overload-stop contact"),
        ):
            if trial.get(key) is True:
                rejects.append(f"{tid}: {label}")

    inspection = session.get("post_trial_inspection", {})
    for key, label in (
        ("fastener_migration_observed", "post-trial fastener migration"),
        ("insert_shift_observed", "post-trial insert shift"),
        ("fixture_damage_observed", "fixture damage"),
        ("residual_deformation_observed", "residual deformation"),
    ):
        if inspection.get(key) is True:
            rejects.append(label)
    return rejects


def summarize(
    force_log: Path,
    session_path: Path | None = None,
    *,
    synthetic_fixture: bool = False,
) -> dict[str, Any]:
    rows = load_rows(force_log)
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        trial_id = str(row["trial_id"]).strip()
        pose = str(row["pose"]).strip().upper()
        if not trial_id:
            raise ValueError("trial_id must be nonempty")
        grouped.setdefault((trial_id, pose), []).append(row)

    trials = sorted({trial_id for trial_id, _ in grouped})
    if len(trials) < 3:
        raise ValueError("SnowDeck signature requires at least three independent trials")

    missing = [
        f"{trial_id}:{pose}"
        for trial_id in trials
        for pose in REQUIRED_POSES
        if (trial_id, pose) not in grouped
    ]
    if missing:
        raise ValueError("missing required trial/pose groups: " + ", ".join(missing))

    per_trial: dict[str, dict[str, dict[str, Any]]] = {}
    for trial_id in trials:
        per_trial[trial_id] = {
            pose: pose_summary(grouped[(trial_id, pose)])
            for pose in REQUIRED_POSES
        }

    neutral = [per_trial[t]["NEUTRAL"] for t in trials]
    deep = [per_trial[t]["DEEP_KNEE"] for t in trials]
    heel = [per_trial[t]["HEEL_BIASED"] for t in trials]
    toe = [per_trial[t]["TOE_BIASED"] for t in trials]

    neutral_metrics = {
        "left_load_fraction": _mean_sd([x["left_load_fraction"] for x in neutral]),
        "left_forefoot_fraction": _mean_sd([x["left_forefoot_fraction"] for x in neutral]),
        "right_forefoot_fraction": _mean_sd([x["right_forefoot_fraction"] for x in neutral]),
        "total_load": _mean_sd([x["mean_total_load"] for x in neutral]),
    }

    left_edge = [
        toe[i]["left_forefoot_fraction"] - heel[i]["left_forefoot_fraction"]
        for i in range(len(trials))
    ]
    right_edge = [
        toe[i]["right_forefoot_fraction"] - heel[i]["right_forefoot_fraction"]
        for i in range(len(trials))
    ]
    deep_left = [
        deep[i]["left_load_fraction"] - neutral[i]["left_load_fraction"]
        for i in range(len(trials))
    ]
    deep_left_forefoot = [
        deep[i]["left_forefoot_fraction"] - neutral[i]["left_forefoot_fraction"]
        for i in range(len(trials))
    ]
    deep_right_forefoot = [
        deep[i]["right_forefoot_fraction"] - neutral[i]["right_forefoot_fraction"]
        for i in range(len(trials))
    ]

    session = (
        json.loads(session_path.read_text(encoding="utf-8"))
        if session_path is not None
        else None
    )
    if session is not None and session.get("scope") != "x1_snowdeck_reversible_bench_observation":
        raise ValueError("linked session has wrong SnowDeck bench scope")

    rejects = mechanical_rejects(session)
    return {
        "schema_version": 1,
        "scope": "x1_snowdeck_bench_signature",
        "source_force_log_sha256": sha256_file(force_log),
        "source_session_sha256": sha256_file(session_path) if session_path else None,
        "session_id": session.get("session_id") if session else None,
        "condition_id": session.get("condition_id") if session else None,
        "synthetic_fixture": bool(synthetic_fixture),
        "physical_evidence_eligible": not bool(synthetic_fixture),
        "trial_count": len(trials),
        "required_poses": list(REQUIRED_POSES),
        "neutral": neutral_metrics,
        "heel_to_toe_forefoot_transfer": {
            "left": _mean_sd(left_edge),
            "right": _mean_sd(right_edge),
        },
        "deep_knee_delta_from_neutral": {
            "left_load_fraction": _mean_sd(deep_left),
            "left_forefoot_fraction": _mean_sd(deep_left_forefoot),
            "right_forefoot_fraction": _mean_sd(deep_right_forefoot),
        },
        "mechanical_rejects": rejects,
        "eligible_for_further_bench_comparison": not rejects,
        "interpretation": (
            "Descriptive response vector only. Stable asymmetry is not penalized and "
            "larger transfer is not automatically better."
        ),
        "physical_authority": False,
        "fabrication_authority": False,
        "ride_authority": False,
        "powered_operation_authorized": False,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("force_log", type=Path)
    p.add_argument("--session", type=Path)
    p.add_argument("--synthetic-fixture", action="store_true")
    p.add_argument("--out", type=Path)
    args = p.parse_args()

    report = summarize(
        args.force_log,
        args.session,
        synthetic_fixture=args.synthetic_fixture,
    )
    text = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
