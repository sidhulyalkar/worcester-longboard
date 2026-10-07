import json
from datetime import date
from pathlib import Path

from tools import build_catalog_source_health as health

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str):
    return json.loads((ROOT / relative).read_text())


def by_id(report):
    return {row["component_id"]: row for row in report["component_health"]}


def test_catalog_source_health_matches_expected_2026_10_07_state():
    report = health.build_health(as_of=date(2026, 10, 7))
    assert report["valid"] is True
    assert report["integrity_errors"] == []
    assert report["summary"] == {
        "catalog_components": 37,
        "source_linked_components": 22,
        "planning_only_components": 15,
        "source_fresh": 15,
        "refresh_due": 7,
        "stale": 0,
        "missing_provenance": 0,
        "geometry_visual_proxies": 3,
        "source_snapshots": 18,
    }
    assert report["authority"] == {
        "stock_currently_verified": False,
        "procurement_authorized": False,
        "fabrication_authorized": False,
        "powered_operation_authorized": False,
        "source_health_may_promote_x1_authority": False,
    }


def test_older_mbs_sources_are_refresh_due_while_october_sources_are_fresh():
    report = health.build_health(as_of=date(2026, 10, 7))
    rows = by_id(report)

    for component_id in {
        "DONOR-COMP95",
        "BRAKE-V5",
        "TRUCK-M3-400",
        "HUB-RSII",
        "TIRE-T2-9",
        "AXLE-M3-70",
        "DRIVE-G1-DUAL",
    }:
        assert rows[component_id]["status"] == "REFRESH_DUE"
        assert rows[component_id]["verified_as_of"] == "2026-09-11"
        assert rows[component_id]["age_days"] == 26

    for component_id in {
        "DECK-TRAMPA-SHORT-969",
        "TRUCK-APEX-AIR",
        "DRIVE-BOARDNAMICS-M1-AT",
        "DECK-LACROIX-BARREL-REF",
    }:
        assert rows[component_id]["status"] == "SOURCE_FRESH"
        assert rows[component_id]["verified_as_of"] == "2026-10-04"
        assert rows[component_id]["age_days"] == 3


def test_planning_only_components_do_not_pretend_to_have_source_freshness():
    report = health.build_health(as_of=date(2026, 10, 7))
    rows = by_id(report)
    assert rows["BATTERY-TRAIL-CLASS"]["status"] == "PLANNING_ONLY"
    assert rows["BATTERY-TRAIL-CLASS"]["source_url"] is None
    assert rows["MOTOR-63XX-CLASS"]["status"] == "PLANNING_ONLY"


def test_visual_geometry_proxies_are_explicitly_non_fabrication():
    report = health.build_health(as_of=date(2026, 10, 7))
    proxy_ids = {row["id"] for row in report["geometry_visual_proxies"]}
    assert proxy_ids == {
        "trampa_vertigo_406",
        "apex_air_434",
        "lacroix_hyperlite_381",
    }
    assert all(
        row["fabrication_authority"] is False
        for row in report["geometry_visual_proxies"]
    )


def test_refresh_worklist_deduplicates_shared_matrix_source():
    report = health.build_health(as_of=date(2026, 10, 7))
    assert [group["seller"] for group in report["refresh_worklist"]] == ["MBS"]
    rows = report["refresh_worklist"][0]["components"]
    matrix_rows = [
        row for row in rows
        if row["snapshot_id"] == "mbs_matrixiii_2026_09_11"
    ]
    assert {row["component_id"] for row in matrix_rows} == {
        "TRUCK-M3-400",
        "AXLE-M3-70",
    }

    markdown = health.render_worklist(report)
    assert markdown.count("mbs_matrixiii_2026_09_11") == 1
    assert "TRUCK-M3-400, AXLE-M3-70" in markdown or "AXLE-M3-70, TRUCK-M3-400" in markdown
    assert "not stock confirmation" in markdown
    assert "never creates purchase" in markdown


def test_missing_snapshot_is_integrity_failure(monkeypatch, tmp_path):
    catalog = load("catalog/board_components.v1.json")
    broken = next(row for row in catalog["components"] if row["id"] == "BRAKE-V5")
    broken["source"].pop("snapshot_id", None)

    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog))
    monkeypatch.setattr(health, "CATALOG_PATH", path)

    report = health.build_health(as_of=date(2026, 10, 7))
    rows = by_id(report)
    assert report["valid"] is False
    assert rows["BRAKE-V5"]["status"] == "MISSING_PROVENANCE"
    assert any("BRAKE-V5" in text for text in report["integrity_errors"])


def test_power_hardware_cannot_escape_power_gate(monkeypatch, tmp_path):
    catalog = load("catalog/board_components.v1.json")
    broken = next(row for row in catalog["components"] if row["id"] == "DRIVE-G1-DUAL")
    broken["procurement_state"] = "SOURCE_ONLY"

    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog))
    monkeypatch.setattr(health, "CATALOG_PATH", path)

    report = health.build_health(as_of=date(2026, 10, 7))
    assert report["valid"] is False
    assert any("escaped POWER_GATED" in text for text in report["integrity_errors"])


def test_freshness_transitions_do_not_themselves_invalidate_integrity():
    refresh_due = health.build_health(as_of=date(2026, 10, 20))
    stale = health.build_health(as_of=date(2026, 11, 20))

    assert refresh_due["valid"] is True
    assert refresh_due["summary"]["refresh_due"] > 0
    assert stale["valid"] is True
    assert stale["summary"]["stale"] > 0
