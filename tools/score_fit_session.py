#!/usr/bin/env python3
"""Score one private X1 fit session and evaluate the Rev-B readiness gate.

Every qualifying trial must reference both its calibrated neutral-trial CSV and
the underlying raw ESP32 log. Raw/private files remain under rider/private/.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _authority_digest(report: dict) -> str:
    payload = json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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
    source_provenance = []
    for trial in manifest.get("trials", []):
        trial_id = trial.get("trial_id")
        geometry = trial["geometry"]
        csv_ref = trial["csv"]
        csv_path = resolve(base, csv_ref)
        rows = read_csv(csv_path)
        source = {
            "trial_id": trial_id,
            "csv_ref": csv_ref,
            "csv_sha256": _sha256(csv_path),
        }
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
            quality["raw_log_ref"] = raw_ref
            raw_quality.append(quality)
            source["raw_log_ref"] = raw_ref
            source["raw_log_sha256"] = _sha256(raw_path)
        source_provenance.append(source)

    if len(summaries) < 2:
        raise SystemExit("Need at least two trial CSVs to score a session")

    score = score_trials(summaries)
    gate = evaluate(profile, score, raw_quality)
    report = {
        "schema_version": 2,
        "authority": "x1_fit_session",
        "session_id": manifest.get("session_id"),
        "candidate_id": manifest.get("candidate_id"),
        "manifest_sha256": _sha256(manifest_path),
        "profile_sha256": _sha256(profile_path),
        "source_provenance": source_provenance,
        "trial_summaries": summaries,
        "raw_quality": raw_quality,
        "score": score,
        "rev_b_gate": gate,
    }
    report["authority_fingerprint_sha256"] = _authority_digest(report)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

    if not gate["ready_for_rev_b_fit_cad"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
