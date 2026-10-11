"""Offline source scanner and browser-workflow quality gates. No external requests."""
import json
from pathlib import Path
from tools.scan_outdoor_parts_sources import (
    Metadata, MAX_HTML_BYTES, robot_permission, safe_https_url, scan_sources
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / "catalog/outdoor_parts_picker.v1.json").read_text())
HTML = (ROOT / "builder/parts.html").read_text()
APP = (ROOT / "builder/parts_picker_app.mjs").read_text()
CSS = (ROOT / "builder/parts.css").read_text()
ENGINE = (ROOT / "builder/parts_picker_engine.mjs").read_text()


def test_scanner_defaults_offline_and_never_promotes_new_website_claims():
    result = scan_sources(REGISTRY, do_fetch=False, limit=4)
    assert result["fetch_enabled"] is False
    assert result["requested_source_count"] == 4
    assert result["approved_for_sourcing"] is False
    assert len(result["rows"]) == 4
    assert all(x["scan_state"] == "NOT_FETCHED_REVIEW_REQUIRED"
               for x in result["rows"])
    assert all(not x["live_stock_verified"] for x in result["rows"])


def test_scanner_rejects_unsafe_origins_and_unavailable_robots():
    assert safe_https_url("https://www.atomic.com/en-us/products/bent-90-aa7367-202600")
    for value in ["http://www.atomic.com", "javascript:alert(1)",
                  "https://user:password@atomic.com/a",
                  "https://localhost/a", "https://atomic.com:8443/a",
                  "https://atomic.com/a#fragment"]:
        assert not safe_https_url(value)
    assert not robot_permission("", "https://www.atomic.com/en-us/products/abc")
    robots = "User-agent: *\nDisallow: /private\nAllow: /"
    assert robot_permission(robots, "https://www.atomic.com/en-us/products/abc")
    assert not robot_permission(robots, "https://www.atomic.com/private/item")


def test_html_reader_limits_text_to_metadata_no_bulk_product_scraping():
    p = Metadata()
    p.feed("<html><head><title>Official skis</title>"
           "<meta name='description' content='Product model reference'></head>"
           "<body><p>Secret prices / addresses</p></body></html>")
    assert p.title == "Official skis"
    assert p.description == "Product model reference"
    assert "Secret" not in p.title
    assert MAX_HTML_BYTES <= 512 * 1024


def test_picker_ui_exposes_3d_svg_keyboard_and_source_driven_order_exports():
    for id_ in ("picker-domain", "picker-slots", "picker-3d", "picker-2d",
                "picker-visual-svg", "picker-visual-3d",
                "picker-left", "picker-right", "picker-part-tree",
                "picker-order-table", "picker-export-csv", "picker-export-json",
                "picker-vendors", "picker-print"):
        assert f'id="{id_}"' in HTML
    assert 'renderExplodedAssemblySvg' in APP
    assert 'createExploded3DViewer' in APP
    assert 'state.viewer.update(' in APP
    assert 'aria-pressed' in HTML and 'aria-pressed' in APP
    assert 'rel="noopener noreferrer"' in APP
    assert "quoteCsv" in APP and '"UNKNOWN"' in APP
    assert 'exact_seller_order_units:null' in ENGINE
    assert "UNQUALIFIED_SEMANTIC_ASSEMBLY_EXPLODED_VIEW" in ENGINE
    assert "body" in CSS and "@media print" in CSS
    assert 'href="./parts.html"' in (ROOT / "builder/index.html").read_text()
    assert 'href="./parts.html"' in (ROOT / "builder/catalog.html").read_text()


def test_consumer_3d_printing_prohibits_release_and_primary_retention():
    categories = {x["id"]: x for x in REGISTRY["print_guidance"]}
    assert categories["critical-hardware"]["classification"] == (
        "DO_NOT_SUBSTITUTE_WITH_GENERIC_FDM_PRINT")
    assert categories["binding-alignment-template"]["classification"] == "DISPLAY_ONLY"
    assert all(not x["checkout_eligible"] for x in REGISTRY["products"])
