#!/usr/bin/env python3
"""Offline Parts Picker release gate. Never treats a research preview as assembly approval.

Usage:
  python tools/check_parts_picker_release.py --mode preview
  python tools/check_parts_picker_release.py --mode candidate \
    --browser-report /path/to/browser-qa.json \
    --manual-review /path/to/authorized-review.json \
    --head-sha EXACT_TESTED_COMMIT_SHA

The candidate mode is intended for deliberate human review, not CI self-approval.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_REVIEW_CHECKS = (
    "visual_desktop_1440",
    "visual_desktop_1280",
    "visual_tablet_768",
    "visual_mobile_390",
    "keyboard_and_screen_reader",
    "real_touch_device",
    "successful_webgl_orbit",
    "print_or_export_readability",
    "external_maker_links_and_current_product_identity",
)
ACTIVE_SPORTS = {"alpine_ski", "snowboard", "skateboard_longboard", "mountainboard"}
REQUIRED_BROWSER_WIDTHS = {390, 768, 1280, 1440}
REQUIRED_BROWSER_CHECK_NAMES = {
    "Four sports render three cards, load source-bound assemblies and stay non-orderable",
    "Seven child IDs render in actual local WebGL, camera and keyboard selection work",
    "Unavailable pinned-local and CDN Three.js both fall back to SVG without losing parts",
    "Actual browser JSON/CSV downloads preserve zero approved order lines",
    "390, 768, 1280 and 1440 px screenshots captured with overflow checks",
}
ZERO_AUTHORITY = (
    "procurement_authorized",
    "fabrication_authorized",
    "charging_authorized",
    "powered_operation_authorized",
    "generic_builder_may_promote_x1_authority",
)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def evaluate(
    root: Path,
    *,
    browser_report: dict[str, Any] | None = None,
    manual_review: dict[str, Any] | None = None,
    head_sha: str | None = None,
) -> dict[str, Any]:
    issues: list[str] = []
    passed: list[str] = []
    try:
        parts = load_json(root / "catalog/outdoor_parts_picker.v1.json")
        supplier = load_json(root / "catalog/outdoor_supplier_observations.v1.json")
        retail = load_json(root / "catalog/outdoor_retail_comparisons.v1.json")
        builds = load_json(root / "catalog/outdoor_build_studies.v1.json")
        maker_kits = load_json(root / "catalog/outdoor_complete_kit_claims.v1.json")
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        return {
            "scope": "PARTS_PICKER_RESEARCH_PREVIEW_RELEASE_GATE",
            "structural_pass": False,
            "browser_pass": False,
            "human_review_pass": False,
            "candidate_merge_ready": False,
            "issues": [f"Required source registry unreadable: {exc}"],
            "authority": {key: False for key in ZERO_AUTHORITY},
        }

    for name, registry in (
        ("parts", parts), ("supplier", supplier), ("retail", retail), ("builds", builds),
        ("maker_kits", maker_kits)
    ):
        authority = registry.get("authority", registry.get("policy"))
        if not isinstance(authority, dict) or any(
            authority.get(key) is not False for key in ZERO_AUTHORITY
            if key in authority
        ):
            issues.append(f"{name}: suspicious or missing authority gate")
        if name != "parts" and (
            not isinstance(authority, dict)
            or not all(authority.get(key) is False for key in ZERO_AUTHORITY)
        ):
            issues.append(f"{name}: incomplete zero-approval authority")
    parts_policy = parts.get("policy", {})
    if not isinstance(parts_policy, dict) or not parts_policy or any(
        value is not False for value in parts_policy.values()
    ):
        issues.append("parts registry must have all policy flags false")

    domains = {x.get("domain_id") for x in parts.get("assembly_templates", [])}
    studies = builds.get("studies", [])
    if domains != ACTIVE_SPORTS:
        issues.append("unexpected set of supported source-bound sport templates")
    if len(studies) != 12 or {x.get("domain_id") for x in studies} != ACTIVE_SPORTS:
        issues.append("exactly twelve research presets across the four sports required")
    if len(maker_kits.get("kits", [])) != 2 or sum(
        len(x.get("children", [])) for x in maker_kits.get("kits", [])
    ) != 14:
        issues.append("two maker-declared seven-child complete kits are required")
    if any(
        kit.get("actual_received_kit_verified") is not False
        or kit.get("seller_checkout_option_verified") is not False
        or any(
            child.get("actual_received_units") is not None
            or child.get("direct_seller_purchase_required") is not False
            for child in kit.get("children", [])
        )
        for kit in maker_kits.get("kits", [])
    ):
        issues.append("unconfirmed seller package contents were promoted to received/order items")
    for sport in ACTIVE_SPORTS:
        subset = [x for x in studies if x.get("domain_id") == sport]
        if len(subset) != 3:
            issues.append(f"{sport}: not three source-bound alternatives")
        if any(x.get("authority") != "UNQUALIFIED_VISUAL_AND_SOURCING_STUDY"
               for x in subset):
            issues.append(f"{sport}: physical or ordering authority was promoted")
    if any(x.get("checkout_eligible") is not False
           for x in retail.get("offers", [])):
        issues.append("retailer observation claims a checkout authorization")
    if any(x.get("financial_checkout_authorized") is not False
           for x in supplier.get("listing_observations", [])):
        issues.append("supplier observation claims checkout authorization")
    if not (root / "builder/parts.html").is_file() or not (
        root / "tests/browser/parts_picker_smoke.mjs"
    ).is_file():
        issues.append("interactive builder or real-browser gate is missing")
    if not issues:
        passed.append("Four sports, twelve research studies and source authority locks")
    structural_pass = not issues

    browser_pass = False
    if browser_report is not None:
        browser_pass = (
            browser_report.get("status") == "PASS"
            and isinstance(browser_report.get("checks"), list)
            and len(browser_report["checks"]) >= 7
            and REQUIRED_BROWSER_WIDTHS.issubset(
                set(browser_report.get("viewport_widths", []))
            )
            and (head_sha is None or browser_report.get("head_sha") == head_sha)
            and all(
                isinstance(x, dict)
                and isinstance(x.get("name"), str)
                and len(x["name"]) >= 5
                and x.get("result") == "PASS"
                for x in browser_report["checks"]
            )
            and REQUIRED_BROWSER_CHECK_NAMES.issubset({
                x["name"] for x in browser_report["checks"]
                if isinstance(x, dict) and isinstance(x.get("name"), str)
            })
        )
        if browser_pass:
            passed.append("Actual Chromium flow, responsive and fallback receipts")
        else:
            issues.append("Chromium report lacks passing scenario and viewport evidence")

    human_pass = False
    if manual_review is not None:
        reviews = manual_review.get("checks")
        match = bool(
            head_sha
            and re.fullmatch(r"[0-9a-f]{40}", head_sha)
            and manual_review.get("reviewed_head_sha") == head_sha
        )
        human_pass = (
            match
            and manual_review.get("schema_version") == 1
            and isinstance(manual_review.get("reviewer"), str)
            and len(manual_review["reviewer"].strip()) >= 3
            and isinstance(manual_review.get("evidence_links"), list)
            and len(manual_review["evidence_links"]) >= 1
            and isinstance(reviews, dict)
            and all(reviews.get(key) == "PASS" for key in REQUIRED_REVIEW_CHECKS)
            and manual_review.get("recognizes_non_procurement_status") is True
            and manual_review.get("recognizes_no_physical_release") is True
        )
        if human_pass:
            passed.append("Head-matched, explicit visual and human review receipt")
        else:
            issues.append("Human review is incomplete, untraceable or for another commit")

    return {
        "schema_version": 1,
        "scope": "PARTS_PICKER_RESEARCH_PREVIEW_RELEASE_GATE",
        "structural_pass": structural_pass,
        "browser_pass": browser_pass,
        "human_review_pass": human_pass,
        "candidate_merge_ready": structural_pass and browser_pass and human_pass,
        "live_cart_ready": False,
        "physical_assembly_authorized": False,
        "professional_ski_binding_release_authorized": False,
        "passed": passed,
        "issues": issues,
        "authority": {key: False for key in ZERO_AUTHORITY},
        "note": (
            "Candidate merge readiness is a research website/software signoff, "
            "never authorization to buy parts, mount ski bindings, fabricate parts, "
            "charge batteries or ride the machine."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preview", "candidate"), default="preview")
    parser.add_argument("--browser-report", type=Path)
    parser.add_argument("--manual-review", type=Path)
    parser.add_argument("--head-sha")
    args = parser.parse_args()
    try:
        result = evaluate(
            ROOT,
            browser_report=load_json(args.browser_report) if args.browser_report else None,
            manual_review=load_json(args.manual_review) if args.manual_review else None,
            head_sha=args.head_sha,
        )
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Parts Picker release gate: invalid review evidence: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.mode == "preview":
        return 0 if result["structural_pass"] else 1
    return 0 if result["candidate_merge_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
