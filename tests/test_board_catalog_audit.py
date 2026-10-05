from datetime import date
from pathlib import Path

from tools.audit_board_catalog import audit

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_audit_passes_on_snapshot_date_and_remains_authority_false():
    report = audit(
        as_of=date(2026, 10, 4),
        max_source_age_days=30,
        strict_freshness=True,
    )

    assert report["valid"] is True, report["errors"]
    assert report["snapshot_as_of"] == "2026-10-04"
    assert report["snapshot_age_days"] == 0
    assert report["stale"] is False
    assert len(report["coverage"]["vendor_families"]) >= 3
    assert len(report["coverage"]["steering_families"]) >= 2
    assert len(report["coverage"]["drive_types"]) >= 2
    assert report["authority"] == {
        "procurement_authorized": False,
        "fabrication_authorized": False,
        "powered_operation_authorized": False,
    }


def test_catalog_audit_reports_staleness_without_granting_authority():
    report = audit(
        as_of=date(2026, 12, 15),
        max_source_age_days=30,
        strict_freshness=False,
    )

    assert report["valid"] is True
    assert report["stale"] is True
    assert report["snapshot_age_days"] > 30
    assert any("freshness limit" in warning for warning in report["warnings"])
    assert all(value is False for value in report["authority"].values())


def test_catalog_audit_can_fail_closed_on_stale_snapshot():
    report = audit(
        as_of=date(2026, 12, 15),
        max_source_age_days=30,
        strict_freshness=True,
    )

    assert report["valid"] is False
    assert report["stale"] is True
    assert any("freshness limit" in error for error in report["errors"])
