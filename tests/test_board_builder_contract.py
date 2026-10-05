import json
from pathlib import Path

from tools.validate_board_builder import validate

ROOT = Path(__file__).resolve().parents[1]


def test_board_builder_catalog_contract_is_valid():
    report = validate()
    assert report["valid"] is True, report["errors"]
    assert report["catalog_components"] >= 15
    assert report["architectures"] >= 4
    assert report["questionnaire_fields"] >= 30
    assert report["power_categories_checkout_enabled"] is False
    assert report["generic_builder_may_promote_x1_authority"] is False


def test_reference_build_0001_cannot_promote_authority():
    data = json.loads((ROOT / "configurator" / "reference_builds.v1.json").read_text())
    x1 = next(row for row in data["builds"] if row["id"] == "worcester_x1_0001")
    assert x1["generic_builder_may_promote_authority"] is False
    assert x1["status"] == "EVIDENCE_GATED_REFERENCE"


def test_every_vendor_catalog_entry_keeps_snapshot_date():
    catalog = json.loads((ROOT / "catalog" / "board_components.v1.json").read_text())
    for component in catalog["components"]:
        source = component["source"]
        if source["kind"] == "vendor":
            assert source["url"].startswith("https://")
            assert source["as_of"]


def test_builder_deep_links_only_to_known_showcase_presets():
    architectures = json.loads((ROOT / "configurator" / "architectures.v1.json").read_text())
    twin = json.loads((ROOT / "showcase" / "x1_rev_c.json").read_text())
    presets = {
        row["id"]
        for row in twin["design_studies"]["configuration_lab"]["presets"]
    }
    assert {
        row["visual_preset"]
        for row in architectures["architectures"]
    }.issubset(presets)
