"""Regression tests for strict research-only Parts Picker release governance."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from tools.check_parts_picker_release import (
    ROOT, REQUIRED_REVIEW_CHECKS, REQUIRED_BROWSER_CHECK_NAMES, evaluate
)


def browser_pass(sha=None):
    return {
        "status": "PASS",
        "head_sha": sha,
        "checks": [
            {"name": name, "result": "PASS"}
            for name in sorted(REQUIRED_BROWSER_CHECK_NAMES)
        ] + [
            {"name": f"additional scenario {i}", "result": "PASS"}
            for i in range(4)
        ],
        "viewport_widths": [390, 768, 1280, 1440],
    }


def signoff(commit):
    return {
        "schema_version": 1,
        "reviewed_head_sha": commit,
        "reviewer": "QA reviewer",
        "evidence_links": ["https://github.com/example/repo/actions/runs/1234"],
        "checks": {key: "PASS" for key in REQUIRED_REVIEW_CHECKS},
        "recognizes_non_procurement_status": True,
        "recognizes_no_physical_release": True,
    }


def test_research_preview_structurally_valid_but_not_merge_ready_without_reviews():
    result = evaluate(ROOT)
    assert result["structural_pass"] is True, result["issues"]
    assert result["browser_pass"] is False
    assert result["human_review_pass"] is False
    assert result["candidate_merge_ready"] is False
    assert result["live_cart_ready"] is False
    assert result["physical_assembly_authorized"] is False
    assert not any(result["authority"].values())


def test_complete_head_matched_candidate_receipts_only_qualify_software_review():
    sha = "a" * 40
    result = evaluate(ROOT, browser_report=browser_pass(sha),
                      manual_review=signoff(sha), head_sha=sha)
    assert result["structural_pass"]
    assert result["browser_pass"]
    assert result["human_review_pass"]
    assert result["candidate_merge_ready"]
    assert result["live_cart_ready"] is False
    assert result["physical_assembly_authorized"] is False
    assert result["professional_ski_binding_release_authorized"] is False


def test_incomplete_or_stale_manual_review_never_authorizes_merge():
    sha = "b" * 40
    old_review = signoff("c" * 40)
    result = evaluate(ROOT, browser_report=browser_pass(sha),
                      manual_review=old_review, head_sha=sha)
    assert not result["human_review_pass"]
    assert not result["candidate_merge_ready"]

    review = signoff(sha)
    review["checks"]["successful_webgl_orbit"] = "PENDING"
    result = evaluate(ROOT, browser_report=browser_pass(sha),
                      manual_review=review, head_sha=sha)
    assert not result["candidate_merge_ready"]

    review = signoff(sha)
    review["recognizes_non_procurement_status"] = False
    result = evaluate(ROOT, browser_report=browser_pass(sha),
                      manual_review=review, head_sha=sha)
    assert not result["candidate_merge_ready"]

    result = evaluate(ROOT, browser_report=browser_pass("c" * 40),
                      manual_review=signoff(sha), head_sha=sha)
    assert not result["candidate_merge_ready"]

    bad_browser = browser_pass(sha)
    bad_browser["checks"] = [
        x for x in bad_browser["checks"]
        if "actual local WebGL" not in x["name"]
    ]
    result = evaluate(ROOT, browser_report=bad_browser,
                      manual_review=signoff(sha), head_sha=sha)
    assert not result["candidate_merge_ready"]

    bad_browser = browser_pass(sha)
    bad_browser["viewport_widths"].remove(390)
    result = evaluate(ROOT, browser_report=bad_browser,
                      manual_review=signoff(sha), head_sha=sha)
    assert not result["candidate_merge_ready"]


def test_promoted_source_authority_or_missing_sports_fail_closed(tmp_path):
    for source in (
        "outdoor_parts_picker.v1.json",
        "outdoor_supplier_observations.v1.json",
        "outdoor_retail_comparisons.v1.json",
        "outdoor_build_studies.v1.json",
        "outdoor_complete_kit_claims.v1.json",
        "outdoor_complete_kit_cad_recipes.v1.json",
    ):
        target = tmp_path / "catalog" / source
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / "catalog" / source, target)
    (tmp_path / "builder").mkdir()
    (tmp_path / "builder" / "parts.html").write_text("<!doctype html>")
    (tmp_path / "tests" / "browser").mkdir(parents=True)
    (tmp_path / "tests" / "browser" / "parts_picker_smoke.mjs").write_text("test")
    path = tmp_path / "catalog" / "outdoor_retail_comparisons.v1.json"
    data = json.loads(path.read_text())
    data["authority"]["procurement_authorized"] = True
    path.write_text(json.dumps(data))
    result = evaluate(tmp_path)
    assert not result["structural_pass"]
    assert not result["candidate_merge_ready"]


def test_unqualified_parametric_cad_recipe_cannot_claim_physical_clearance(tmp_path):
    for source in (
        "outdoor_parts_picker.v1.json",
        "outdoor_supplier_observations.v1.json",
        "outdoor_retail_comparisons.v1.json",
        "outdoor_build_studies.v1.json",
        "outdoor_complete_kit_claims.v1.json",
        "outdoor_complete_kit_cad_recipes.v1.json",
    ):
        dest = tmp_path / "catalog" / source
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / "catalog" / source, dest)
    (tmp_path / "builder").mkdir()
    (tmp_path / "builder" / "parts.html").write_text("preview")
    (tmp_path / "tests/browser").mkdir(parents=True)
    (tmp_path / "tests/browser/parts_picker_smoke.mjs").write_text("test")
    recipe_path = tmp_path / "catalog/outdoor_complete_kit_cad_recipes.v1.json"
    recipe = json.loads(recipe_path.read_text())
    recipe["dimensional_evidence_policy"]["physical_clearances_verified"] = True
    recipe_path.write_text(json.dumps(recipe))
    result = evaluate(tmp_path)
    assert not result["structural_pass"]
    assert not result["candidate_merge_ready"]
    assert any("parametric CAD" in e for e in result["issues"])
