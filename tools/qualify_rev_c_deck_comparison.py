#!/usr/bin/env python3
"""Qualify a private Rev-C full-scale deck-envelope comparison.

The input may contain rider measurements under rider/private/. The emitted
authority is intentionally sanitized: it records pass/fail outcomes, candidate
IDs, the selected envelope, and a hash of the private source, but no raw stance,
foot, yaw, or body measurements.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REQUIRED_CANDIDATE_IDS = {
    "comp95_class",
    "pro_warren_iii_class",
    "agent_class",
}

REQUIRED_SELECTED_CHECKS = (
    "bilateral_emergency_step_off_pass",
    "deep_knee_carve_position_pass",
    "heel_toe_leverage_accepted",
    "remount_repeatability_accepted",
    "subjective_comfort_accepted",
)


def _digest(data: object) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    ).hexdigest()


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def qualify(data: dict) -> dict:
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if data.get("scope") != "rev_c_full_scale_deck_envelope_comparison":
        errors.append("wrong deck-comparison scope")
    if data.get("powered_operation_authorized") is not False:
        errors.append("deck comparison cannot authorize powered operation")

    candidates = data.get("candidates")
    if not isinstance(candidates, list) or len(candidates) < 3:
        errors.append("at least three deck-envelope candidates are required")
        candidates = []

    ids: list[str] = []
    summaries: list[dict] = []
    selected_id = data.get("selected_candidate_id")

    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            errors.append(f"candidate {index} must be an object")
            continue
        cid = candidate.get("id")
        if not _nonempty(cid):
            errors.append(f"candidate {index} missing id")
            continue
        if cid in ids:
            errors.append(f"duplicate candidate id: {cid}")
        ids.append(cid)

        trials = candidate.get("remount_trials")
        if not isinstance(trials, list) or len(trials) < 3:
            errors.append(f"{cid}: at least three remount trials are required")
            trial_count = 0 if not isinstance(trials, list) else len(trials)
        else:
            trial_count = len(trials)
            for trial_index, trial in enumerate(trials):
                if not isinstance(trial, dict):
                    errors.append(f"{cid}: trial {trial_index} must be an object")
                    continue
                for field in (
                    "natural_stance_recorded",
                    "heel_toe_leverage_checked",
                    "bilateral_step_off_checked",
                    "deep_knee_position_checked",
                ):
                    if trial.get(field) is not True:
                        errors.append(f"{cid}: trial {trial_index} missing check {field}")

        checks = candidate.get("summary_checks", {})
        if not isinstance(checks, dict):
            errors.append(f"{cid}: summary_checks must be an object")
            checks = {}

        summaries.append(
            {
                "id": cid,
                "trial_count": trial_count,
                "bilateral_emergency_step_off_pass": checks.get(
                    "bilateral_emergency_step_off_pass"
                )
                is True,
                "deep_knee_carve_position_pass": checks.get(
                    "deep_knee_carve_position_pass"
                )
                is True,
                "heel_toe_leverage_accepted": checks.get(
                    "heel_toe_leverage_accepted"
                )
                is True,
                "remount_repeatability_accepted": checks.get(
                    "remount_repeatability_accepted"
                )
                is True,
                "subjective_comfort_accepted": checks.get(
                    "subjective_comfort_accepted"
                )
                is True,
            }
        )

    if set(ids) != REQUIRED_CANDIDATE_IDS:
        errors.append(
            "deck comparison must evaluate exactly the current Rev-C candidate set: "
            + ", ".join(sorted(REQUIRED_CANDIDATE_IDS))
        )

    if not _nonempty(selected_id) or selected_id not in ids:
        errors.append("selected_candidate_id must reference one evaluated candidate")

    selected_summary = next(
        (summary for summary in summaries if summary["id"] == selected_id), None
    )
    if selected_summary is not None:
        for check in REQUIRED_SELECTED_CHECKS:
            if selected_summary.get(check) is not True:
                errors.append(f"selected candidate failed required check: {check}")

    if not _nonempty(data.get("selection_reason")):
        errors.append("selection_reason is required")

    rejected = data.get("rejected_candidates")
    if not isinstance(rejected, list):
        errors.append("rejected_candidates must be a list")
        rejected = []
    else:
        expected_rejected = {cid for cid in ids if cid != selected_id}
        actual_rejected: set[str] = set()
        for index, entry in enumerate(rejected):
            if not isinstance(entry, dict):
                errors.append(f"rejected candidate {index} must be an object")
                continue
            rid = entry.get("id")
            if not _nonempty(rid):
                errors.append(f"rejected candidate {index} missing id")
                continue
            actual_rejected.add(rid)
            if not _nonempty(entry.get("reason")):
                errors.append(f"rejected candidate {rid} missing reason")
        if expected_rejected != actual_rejected:
            errors.append("every non-selected candidate must be explicitly rejected")

    report = {
        "schema_version": 1,
        "authority": "x1_rev_c_deck_comparison",
        "scope": "sanitized_pre_purchase_deck_comparison",
        "qualified": not errors,
        "errors": errors,
        "selected_candidate_id": selected_id,
        "candidate_summaries": summaries,
        "selection_reason_recorded": _nonempty(data.get("selection_reason")),
        "private_source_sha256": _digest(data),
        "powered_operation_authorized": False,
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_manifest", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    data = json.loads(args.private_manifest.read_text(encoding="utf-8"))
    report = qualify(data)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["qualified"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
