#!/usr/bin/env python3
"""Score one private X1 fit session and evaluate the Rev-B readiness gate.

Manifest format is documented in `fit/session_set.example.json`. Raw/private files
remain under rider/private/ by default.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

from fit.fit_score import score_trials
from fit.profile_schema import RiderProfile
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
    manifest = json.loads(manifest_path.read_text())
    base = manifest_path.parent

    profile_path = resolve(base, manifest["profile"])
    profile = RiderProfile.from_dict(json.loads(profile_path.read_text()))

    summaries = []
    for trial in manifest.get("trials", []):
        geometry = trial["geometry"]
        rows = read_csv(resolve(base, trial["csv"]))
        summary = summarize_neutral_trial(
            rows,
            stance_width_mm=geometry["stance_width_mm"],
            left_yaw_deg=geometry["left_yaw_deg"],
            right_yaw_deg=geometry["right_yaw_deg"],
        )
        summary["trial_id"] = trial.get("trial_id")
        summaries.append(summary)

    if len(summaries) < 2:
        raise SystemExit("Need at least two trial CSVs to score a session")

    score = score_trials(summaries)
    gate = evaluate(profile, score)
    report = {
        "schema_version": 1,
        "session_id": manifest.get("session_id"),
        "candidate_id": manifest.get("candidate_id"),
        "trial_summaries": summaries,
        "score": score,
        "rev_b_gate": gate,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
