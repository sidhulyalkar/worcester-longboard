"""Offline integrity and honest coverage checks for multi-sport Parts Picker."""
import json
import shutil

from tools.audit_parts_picker_readiness import ROOT, assess


def test_reference_breadth_is_never_confused_with_sku_or_physical_qualification():
    result = assess(as_of="2026-10-11")
    assert result["integrity_valid"], result["integrity_errors"]
    s = result["summary"]
    assert s["domains_in_taxonomy"] == 9
    assert s["domains_with_research_template"] == 4
    assert s["domains_taxonomy_only"] == 5
    assert s["product_families"] == 24
    assert s["reference_variant_choices"] == 41
    assert s["curated_unqualified_studies"] == 12
    assert s["maker_observations_total"] == 7
    assert s["retail_observations_total"] == 6
    assert s["different_variant_comparisons_with_2_merchants"] == 0
    assert s["named_variant_comparisons_blocked_by_inclusion_revision"] == 2
    assert any(x["code"] == "RETAILER_INCLUDED_TRUCK_REVISION_CONFLICT"
               for x in result["blockers"])
    assert s["seller_exact_checkout_variants_qualified"] == 0
    assert s["physical_connections_qualified"] == 0
    assert s["procurement_authorized_builds"] == 0
    assert not any(result["authority"].values())


def test_only_real_active_sports_receive_research_workflows():
    result = assess(as_of="2026-10-11")
    domains = {x["domain_id"]: x for x in result["domains"]}
    for domain_id in ("alpine_ski", "snowboard", "skateboard_longboard", "mountainboard"):
        d = domains[domain_id]
        assert d["active_research_template"]
        assert d["curated_studies"] == 3
        assert d["qualified_orderable_builds"] == 0
        assert d["qualified_physical_mates"] == 0
    for domain_id in ("touring_ski", "splitboard", "surfboard", "bicycle", "camping_shelter"):
        assert domains[domain_id]["taxonomy_only"]
        assert domains[domain_id]["manufacturer_product_families"] == 0
        assert domains[domain_id]["curated_studies"] == 0


def test_historical_source_freshness_expires_without_fabricated_live_refresh():
    result = assess(as_of="2026-11-11")
    summary = result["summary"]
    assert summary["retail_observations_within_30d"] == 0
    assert summary["maker_observations_within_30d"] == 0
    assert summary["different_variant_comparisons_with_2_merchants"] == 0
    assert summary["manufacturer_pages_due_refresh"] >= 15
    assert any(x["code"] == "STALE_MANUFACTURER_REFERENCES" for x in result["blockers"])
    assert summary["procurement_authorized_builds"] == 0


def test_corrupted_retail_relationship_or_approval_fails_closed(tmp_path):
    for name in (
        "outdoor_parts_picker.v1.json", "outdoor_supplier_observations.v1.json",
        "outdoor_retail_comparisons.v1.json", "outdoor_build_studies.v1.json",
    ):
        target = tmp_path / "catalog" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / "catalog" / name, target)
    p = tmp_path / "catalog" / "outdoor_retail_comparisons.v1.json"
    data = json.loads(p.read_text())
    data["offers"][4]["related_product_family_id"] = "unrelated_not_in_catalog"
    p.write_text(json.dumps(data))
    result = assess(tmp_path, as_of="2026-10-11")
    assert not result["integrity_valid"]
    assert any("ambiguous related family" in e for e in result["integrity_errors"])
    data["offers"][4]["related_product_family_id"] = "atomic-bent90"
    data["authority"]["procurement_authorized"] = True
    p.write_text(json.dumps(data))
    result = assess(tmp_path, as_of="2026-10-11")
    assert not result["integrity_valid"]
    assert any("authority lock" in e for e in result["integrity_errors"])


def test_missing_required_sport_preset_refuses_readiness(tmp_path):
    for name in (
        "outdoor_parts_picker.v1.json", "outdoor_supplier_observations.v1.json",
        "outdoor_retail_comparisons.v1.json", "outdoor_build_studies.v1.json",
    ):
        target = tmp_path / "catalog" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / "catalog" / name, target)
    p = tmp_path / "catalog" / "outdoor_build_studies.v1.json"
    data = json.loads(p.read_text())
    data["studies"].pop()
    p.write_text(json.dumps(data))
    r = assess(tmp_path, as_of="2026-10-11")
    assert not r["integrity_valid"]
    assert any("expected 3" in e for e in r["integrity_errors"])
