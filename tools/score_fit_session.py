#!/usr/bin/env python3
"""Score one private X1 fit session and evaluate the Rev-B readiness gate.

Every qualifying trial must reference both its calibrated neutral-trial CSV and
the underlying raw ESP32 log. Raw/private files remain under rider/private/.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from fit.fit_score import score_trials
from fit.profile_schema import RiderProfile
from fit.raw_log import parse_text, quality_report
from fit.rev_b_gate import evaluate
from fit.trial_summary import summarize_neutral_trial


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def resolve(base: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (base / p).resolve()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("manifest", type=Path)
    p.add_argument("--out", type=Path, default=Path("rider/private/fit_session_report.json"))
    args = p.parse_args()

    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = manifest_path.parent

    profile_path = resolve(base, manifest["profile"])
    profile = RiderProfile.from_dict(json.loads(profile_path.read_text(encoding="utf-8")))

    summaries = []
    raw_quality = []
    for trial in manifest.get("trials", []):
        trial_id = trial.get("trial_id")
        geometry = trial["geometry"]
        rows = read_csv(resolve(base, trial["csv"]))
        summary = summarize_neutral_trial(
            rows,
            stance_width_mm=geometry["stance_width_mm"],
            left_yaw_deg=geometry["left_yaw_deg"],
            right_yaw_deg=geometry["right_yaw_deg"],
        )
        summary["trial_id"] = trial_id
        summaries.append(summary)

        raw_ref = trial.get("raw_log")
        if raw_ref:
            raw_path = resolve(base, raw_ref)
            quality = quality_report(parse_text(raw_path.read_text(encoding="utf-8")))
            quality["trial_id"] = trial_id
            quality["raw_log"] = str(raw_path)
            raw_quality.append(quality)

    if len(summaries) < 2:
        raise SystemExit("Need at least two trial CSVs to score a session")

    score = score_trials(summaries)
    gate = evaluate(profile, score, raw_quality)
    report = {
        "schema_version": 2,
        "session_id": manifest.get("session_id"),
        "candidate_id": manifest.get("candidate_id"),
        "trial_summaries": summaries,
        "raw_quality": raw_quality,
        "score": score,
        "rev_b_gate": gate,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

    if not gate["ready_for_rev_b_fit_cad"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
