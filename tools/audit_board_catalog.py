#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog" / "board_components.v1.json"
GEOMETRY = ROOT / "catalog" / "board_geometry.v1.json"
ARCHITECTURES = ROOT / "configurator" / "architectures.v1.json"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_snapshot_path() -> Path:
    candidates = sorted((ROOT / "catalog").glob("source_snapshots_*.json"))
    if not candidates:
        raise FileNotFoundError("no catalog/source_snapshots_*.json file found")
    return candidates[-1]


def parse_day(value: str, label: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be YYYY-MM-DD, got {value!r}") from exc


def audit(
    *,
    as_of: date,
    max_source_age_days: int,
    strict_freshness: bool,
    snapshot_path: Path | None = None,
) -> dict[str, Any]:
    catalog = load(CATALOG)
    geometry = load(GEOMETRY)
    architectures = load(ARCHITECTURES)
    snapshot_path = snapshot_path or latest_snapshot_path()
    snapshots = load(snapshot_path)

    errors: list[str] = []
    warnings: list[str] = []

    snapshot_day = parse_day(snapshots.get("as_of"), "snapshot.as_of")
    age_days = (as_of - snapshot_day).days
    if age_days < 0:
        errors.append(
            f"source snapshot {snapshot_day.isoformat()} is in the future relative to audit date {as_of.isoformat()}"
        )
    stale = age_days > max_source_age_days
    if stale:
        message = (
            f"source snapshot is {age_days} days old; freshness limit is "
            f"{max_source_age_days} days"
        )
        if strict_freshness:
            errors.append(message)
        else:
            warnings.append(message)

    source_rows = snapshots.get("sources", [])
    source_index = {row.get("id"): row for row in source_rows if row.get("id")}
    if len(source_index) != len(source_rows):
        errors.append("source snapshot ids must be non-empty and unique")

    components = catalog.get("components", [])
    component_index = {row.get("id"): row for row in components if row.get("id")}
    if len(component_index) != len(components):
        errors.append("component ids must be non-empty and unique")

    source_backed_components: list[str] = []
    native_priced_components: list[str] = []
    missing_snapshot_components: list[str] = []
    stale_component_ids: list[str] = []
    vendors: Counter[str] = Counter()
    categories: Counter[str] = Counter()

    sourced_kinds = {"vendor", "retailer", "vendor_reference"}
    live_power_categories = {"drive", "motor", "esc", "battery", "charger"}

    for row in components:
        cid = row.get("id", "<missing>")
        category = row.get("category")
        categories[str(category)] += 1
        manufacturer = row.get("manufacturer")
        if manufacturer:
            vendors[str(manufacturer)] += 1

        source = row.get("source") or {}
        kind = source.get("kind")
        if kind in sourced_kinds:
            source_backed_components.append(cid)
            if not source.get("url") or not source.get("as_of"):
                errors.append(f"{cid}: sourced component requires source URL + source as_of")
            else:
                component_day = parse_day(source["as_of"], f"{cid}.source.as_of")
                component_age = (as_of - component_day).days
                if component_age > max_source_age_days:
                    stale_component_ids.append(cid)

            snapshot_id = source.get("snapshot_id")
            if not snapshot_id:
                missing_snapshot_components.append(cid)
            elif snapshot_id not in source_index:
                errors.append(f"{cid}: snapshot_id {snapshot_id!r} does not resolve")
            else:
                snapshot = source_index[snapshot_id]
                if source.get("url") != snapshot.get("url"):
                    errors.append(
                        f"{cid}: source URL differs from dated snapshot {snapshot_id!r}"
                    )

        native_price = source.get("native_price_snapshot")
        if native_price:
            native_priced_components.append(cid)
            if row.get("price") is not None:
                errors.append(
                    f"{cid}: native-currency price snapshot may not be silently converted into USD catalog price"
                )

        if category in live_power_categories and row.get("procurement_state") != "POWER_GATED":
            errors.append(
                f"{cid}: live-power category {category!r} must remain POWER_GATED"
            )

    if missing_snapshot_components:
        warnings.append(
            "source-backed components missing snapshot_id: "
            + ", ".join(sorted(missing_snapshot_components))
        )

    geometry_urls = {
        row.get("source_url")
        for group in ("decks", "topologies")
        for row in geometry.get(group, [])
        if row.get("source_url")
    }
    snapshot_urls = {row.get("url") for row in source_rows if row.get("url")}
    missing_geometry_sources = sorted(url for url in geometry_urls if url not in snapshot_urls)
    if missing_geometry_sources:
        errors.append(
            "generic geometry references URLs absent from the dated source snapshot: "
            + ", ".join(missing_geometry_sources)
        )

    architecture_rows = architectures.get("architectures", [])
    vendor_families = sorted(
        {row.get("vendor_family") for row in architecture_rows if row.get("vendor_family")}
    )
    if len(vendor_families) < 3:
        errors.append(
            "catalog breadth regression: fewer than three generated vendor families remain"
        )

    visual_deck_families = sorted(
        {row.get("shape_family") for row in geometry.get("decks", []) if row.get("shape_family")}
    )
    steering_families = sorted(
        {
            row.get("steering_family")
            for row in geometry.get("topologies", [])
            if row.get("steering_family")
        }
    )
    wheel_classes = sorted(
        {
            (row.get("interfaces") or {}).get("wheel_class")
            for row in components
            if row.get("category") == "wheel"
            and (row.get("interfaces") or {}).get("wheel_class")
        }
    )
    drive_types = sorted(
        {
            (row.get("interfaces") or {}).get("drive_type")
            for row in components
            if row.get("category") == "drive"
            and (row.get("interfaces") or {}).get("drive_type")
        }
    )
    brake_families = sorted(
        {
            (row.get("interfaces") or {}).get("brake_family")
            for row in components
            if row.get("category") == "brake"
            and (row.get("interfaces") or {}).get("brake_family")
        }
    )

    if len(visual_deck_families) < 3:
        warnings.append("visual deck-shape breadth is below three families")
    if len(steering_families) < 2:
        errors.append("mechanical breadth regression: fewer than two steering families")
    if len(drive_types) < 2:
        warnings.append("drive visual breadth is below two normalized drive types")

    report = {
        "schema_version": 1,
        "valid": not errors,
        "as_of": as_of.isoformat(),
        "snapshot_file": str(snapshot_path.relative_to(ROOT)),
        "snapshot_as_of": snapshot_day.isoformat(),
        "snapshot_age_days": age_days,
        "freshness_limit_days": max_source_age_days,
        "strict_freshness": strict_freshness,
        "stale": stale,
        "errors": errors,
        "warnings": warnings,
        "coverage": {
            "components": len(components),
            "source_backed_components": len(source_backed_components),
            "source_records": len(source_rows),
            "architecture_count": len(architecture_rows),
            "vendor_families": vendor_families,
            "named_manufacturers": sorted(vendors),
            "categories": dict(sorted(categories.items())),
            "visual_deck_families": visual_deck_families,
            "steering_families": steering_families,
            "wheel_classes": wheel_classes,
            "brake_families": brake_families,
            "drive_types": drive_types,
        },
        "freshness": {
            "stale_component_ids": sorted(stale_component_ids),
            "missing_snapshot_component_ids": sorted(missing_snapshot_components),
            "native_currency_price_component_ids": sorted(native_priced_components),
        },
        "authority": {
            "procurement_authorized": False,
            "fabrication_authorized": False,
            "powered_operation_authorized": False,
        },
        "note": (
            "This audit checks catalog provenance, freshness metadata and diversity contracts only. "
            "It does not perform live web refresh and cannot create purchase or physical authority."
        ),
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit Board Builder catalog provenance, freshness and mechanical breadth."
    )
    parser.add_argument(
        "--as-of",
        default=date.today().isoformat(),
        help="Audit date in YYYY-MM-DD. Defaults to today.",
    )
    parser.add_argument(
        "--max-source-age-days",
        type=int,
        default=30,
        help="Age after which dated source snapshots are reported stale.",
    )
    parser.add_argument(
        "--strict-freshness",
        action="store_true",
        help="Fail when the selected source snapshot is older than the configured limit.",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        help="Optional source snapshot path; defaults to latest catalog/source_snapshots_*.json.",
    )
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    if args.max_source_age_days < 0:
        raise SystemExit("--max-source-age-days must be >= 0")

    snapshot = args.snapshot
    if snapshot is not None and not snapshot.is_absolute():
        snapshot = ROOT / snapshot

    report = audit(
        as_of=parse_day(args.as_of, "--as-of"),
        max_source_age_days=args.max_source_age_days,
        strict_freshness=args.strict_freshness,
        snapshot_path=snapshot,
    )
    payload = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    raise SystemExit(0 if report["valid"] else 1)


if __name__ == "__main__":
    main()
