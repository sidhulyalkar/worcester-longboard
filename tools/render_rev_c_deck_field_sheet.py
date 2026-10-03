#!/usr/bin/env python3
"""Render the blinded Rev-C no-parts deck-envelope field sheet."""
from __future__ import annotations

import argparse
from pathlib import Path

DEFAULT_LABELS = ("A", "B", "C")


def render(labels: tuple[str, ...] = DEFAULT_LABELS) -> str:
    lines = [
        "# Worcester X1 Rev-C blinded deck field sheet",
        "",
        "**Static, unpowered, no-parts stance experiment only.**",
        "",
        "Do not open deck_blind_key.json until the first-pass selection is complete.",
        "Use the same shoes, floor surface, and instructions for every candidate.",
        "Step fully off and reset between every remount.",
        "",
        "## Fixed sequence for every remount",
        "",
        "1. Approach without using the previous foot marks as a target.",
        "2. Settle into a natural riding stance.",
        "3. Check heel-to-toe leverage without forcing ankle position.",
        "4. Enter a comfortable deep-knee carve posture.",
        "5. Check a deliberate emergency step-off to both sides.",
        "6. Leave the template completely before the next trial.",
        "",
    ]

    for label in labels:
        lines += [
            f"## Candidate {label}",
            "",
            "| Trial | Natural stance recorded | Heel/toe checked | Deep-knee checked | Bilateral step-off checked |",
            "| --- | --- | --- | --- | --- |",
            "| 1 | [ ] | [ ] | [ ] | [ ] |",
            "| 2 | [ ] | [ ] | [ ] | [ ] |",
            "| 3 | [ ] | [ ] | [ ] | [ ] |",
            "",
            "Summary after all three independent remounts:",
            "",
            "- [ ] bilateral emergency step-off accepted",
            "- [ ] deep-knee carve position accepted",
            "- [ ] heel/toe leverage accepted",
            "- [ ] remount repeatability accepted",
            "- [ ] long-trail comfort accepted",
            "",
            "Private observations to record separately if useful:",
            "",
            "- stance-width / fore-aft reserve",
            "- left/right yaw",
            "- toe and heel overhang",
            "- edge reserve",
            "- any forced or awkward posture",
            "- why this candidate should advance or be rejected",
            "",
        ]

    lines += [
        "## First-pass selection before unblinding",
        "",
        "Selected blind candidate: ______",
        "",
        "Why: ________________________________________________________________",
        "",
        "Rejected blind candidates and reasons:",
        "",
        "- ______: ____________________________________________________________",
        "- ______: ____________________________________________________________",
        "",
        "## Only after the selection is written",
        "",
        "1. Open deck_blind_key.json.",
        "2. Translate A/B/C to the real candidate IDs.",
        "3. Enter the real candidate results into deck_comparison.json.",
        "4. Give every non-selected real candidate an explicit rejection reason.",
        "5. Run tools/qualify_rev_c_deck_comparison.py.",
        "",
        "The winner is only the preferred maximum stance envelope. It does not qualify deck flex, strength, braking, drivetrain coexistence, or powered riding.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    text = render()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
