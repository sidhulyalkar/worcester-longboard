#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "catalog" / "board_components.v1.json"
GEOMETRY_PATH = ROOT / "catalog" / "board_geometry.v1.json"

POWER_CATEGORIES = {"drive", "motor", "esc", "battery", "charger"}
SOURCED_KINDS = {"vendor", "retailer", "vendor_reference"}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_day(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be YYYY-MM-DD, got {value!r}") from exc


def latest_snapshot_path() -> Path:
    paths = sorted((ROOT / "catalog").glob("source_snapshots_*.json"))
    if not paths:
        raise FileNotFoundError("no catalog/source_snapshots_*.json file found")
    return paths[-1]


def classify_age(age_days: int, fresh_days: int, refresh_due_days: int) -> str:
    if age_days <= fresh_days:
        return "SOURCE_FRESH"
    if age_days <= refresh_due_days:
        return "REFRESH_DUE"
    return "STALE"


def build_health(
    *,
    as_of: date,
    fresh_days: int = 14,
    refresh_due_days: int = 30,
    snapshot_path: Path | None = None,
) -> dict[str, Any]:
    if fresh_days < 0:
        raise ValueError("fresh_days must be >= 0")
    if refresh_due_days < fresh_days:
        raise ValueError("refresh_due_days must be >= fresh_days")

    catalog = load(CATALOG_PATH)
    geometry = load(GEOMETRY_PATH)
    snapshot_path = snapshot_path or latest_snapshot_path()
    snapshots = load(snapshot_path)

    snapshot_rows = snapshots.get("sources", [])
    snapshot_index = {
        row["id"]: row for row in snapshot_rows if row.get("id")
    }

    integrity_errors: list[str] = []
    component_health: list[dict[str, Any]] = []

    for component in catalog.get("components", []):
        cid = component["id"]
        source = component.get("source") or {}
        url = source.get("url")
        snapshot_id = source.get("snapshot_id")
        seller = source.get("seller") or component.get("manufacturer") or "Unknown"
        verified_as_of: str | None = None
        age_days: int | None = None
        reasons: list[str] = []
        status = "PLANNING_ONLY"

        category = component.get("category")
        if category in POWER_CATEGORIES and component.get("procurement_state") != "POWER_GATED":
            message = f"{cid}: live-power category {category!r} escaped POWER_GATED"
            integrity_errors.append(message)
            reasons.append(message)

        if source.get("native_price_snapshot") and component.get("price") is not None:
            message = (
                f"{cid}: source-native price snapshot coexists with normalized price; "
                "currency provenance would be ambiguous"
            )
            integrity_errors.append(message)
            reasons.append(message)

        if url:
            status = "MISSING_PROVENANCE"
            if not snapshot_id:
                message = f"{cid}: sourced component has no snapshot_id"
                integrity_errors.append(message)
                reasons.append(message)
            elif snapshot_id not in snapshot_index:
                message = f"{cid}: snapshot_id {snapshot_id!r} does not resolve"
                integrity_errors.append(message)
                reasons.append(message)
            else:
                snapshot = snapshot_index[snapshot_id]
                if snapshot.get("url") != url:
                    message = f"{cid}: catalog URL differs from snapshot {snapshot_id!r}"
                    integrity_errors.append(message)
                    reasons.append(message)
                else:
                    verified_as_of = (
                        snapshot.get("verified_as_of")
                        or source.get("as_of")
                        or snapshots.get("as_of")
                    )
                    if not verified_as_of:
                        message = f"{cid}: snapshot {snapshot_id!r} has no verification date"
                        integrity_errors.append(message)
                        reasons.append(message)
                    else:
                        verified_day = parse_day(verified_as_of, f"{cid}.verified_as_of")
                        age_days = (as_of - verified_day).days
                        if age_days < 0:
                            message = (
                                f"{cid}: verification date {verified_as_of} is after "
                                f"audit date {as_of.isoformat()}"
                            )
                            integrity_errors.append(message)
                            reasons.append(message)
                        else:
                            status = classify_age(age_days, fresh_days, refresh_due_days)
                            if status == "REFRESH_DUE":
                                reasons.append(
                                    f"source is {age_days} days old; refresh before relying on current stock or price"
                                )
                            elif status == "STALE":
                                reasons.append(
                                    f"source is {age_days} days old; refresh before recommendation or sourcing"
                                )

        elif source.get("kind") in SOURCED_KINDS:
            message = f"{cid}: source kind {source.get('kind')!r} requires a URL"
            integrity_errors.append(message)
            reasons.append(message)
            status = "MISSING_PROVENANCE"

        component_health.append(
            {
                "component_id": cid,
                "label": component.get("label"),
                "category": category,
                "manufacturer": component.get("manufacturer"),
                "seller": seller,
                "procurement_state": component.get("procurement_state"),
                "source_kind": source.get("kind"),
                "source_url": url,
                "snapshot_id": snapshot_id,
                "verified_as_of": verified_as_of,
                "age_days": age_days,
                "status": status,
                "reasons": reasons,
            }
        )

    geometry_proxies: list[dict[str, Any]] = []
    for kind, rows in (
        ("deck", geometry.get("decks", [])),
        ("topology", geometry.get("topologies", [])),
    ):
        for row in rows:
            if row.get("visual_geometry_state") == "ASSUMED":
                geometry_proxies.append(
                    {
                        "kind": kind,
                        "id": row["id"],
                        "manufacturer": row.get("manufacturer"),
                        "label": row.get("label"),
                        "note": row.get("visual_geometry_note"),
                        "fabrication_authority": False,
                    }
                )

    counts = Counter(row["status"] for row in component_health)
    refresh_rows = [
        row for row in component_health
        if row["status"] in {"REFRESH_DUE", "STALE", "MISSING_PROVENANCE"}
    ]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in refresh_rows:
        grouped[row["seller"]].append(row)

    refresh_worklist = []
    priority = {"MISSING_PROVENANCE": 0, "STALE": 1, "REFRESH_DUE": 2}
    for seller in sorted(grouped):
        rows = sorted(
            grouped[seller],
            key=lambda row: (
                priority.get(row["status"], 9),
                row["snapshot_id"] or "",
                row["component_id"],
            ),
        )
        refresh_worklist.append({"seller": seller, "components": rows})

    warnings: list[str] = []
    for status, label in (
        ("REFRESH_DUE", "refresh-due"),
        ("STALE", "stale"),
    ):
        if counts.get(status):
            warnings.append(f"{counts[status]} source-linked component(s) are {label}")
    if geometry_proxies:
        warnings.append(
            f"{len(geometry_proxies)} geometry reference(s) use visualization-only proxies"
        )

    return {
        "schema_version": 1,
        "scope": "board_catalog_source_health",
        "as_of": as_of.isoformat(),
        "source_snapshot_file": str(snapshot_path.relative_to(ROOT)),
        "thresholds": {
            "fresh_max_age_days": fresh_days,
            "refresh_due_max_age_days": refresh_due_days,
        },
        "valid": not integrity_errors,
        "integrity_errors": sorted(set(integrity_errors)),
        "warnings": warnings,
        "summary": {
            "catalog_components": len(component_health),
            "source_linked_components": sum(
                1 for row in component_health if row["source_url"]
            ),
            "planning_only_components": counts.get("PLANNING_ONLY", 0),
            "source_fresh": counts.get("SOURCE_FRESH", 0),
            "refresh_due": counts.get("REFRESH_DUE", 0),
            "stale": counts.get("STALE", 0),
            "missing_provenance": counts.get("MISSING_PROVENANCE", 0),
            "geometry_visual_proxies": len(geometry_proxies),
            "source_snapshots": len(snapshot_index),
        },
        "component_health": component_health,
        "geometry_visual_proxies": geometry_proxies,
        "refresh_worklist": refresh_worklist,
        "authority": {
            "stock_currently_verified": False,
            "procurement_authorized": False,
            "fabrication_authorized": False,
            "powered_operation_authorized": False,
            "source_health_may_promote_x1_authority": False,
        },
    }


def render_worklist(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Board catalog source-refresh worklist",
        "",
        f"Audit date: **{report['as_of']}**",
        "",
        (
            "This is a catalog-evidence maintenance queue. It is not stock "
            "confirmation, checkout authorization, fabrication authority, or "
            "powered-operation authority."
        ),
        "",
        "## Health summary",
        "",
        f"- source-linked components: **{summary['source_linked_components']}**",
        f"- fresh: **{summary['source_fresh']}**",
        f"- refresh due: **{summary['refresh_due']}**",
        f"- stale: **{summary['stale']}**",
        f"- missing provenance: **{summary['missing_provenance']}**",
        f"- planning-only components: **{summary['planning_only_components']}**",
        f"- visualization-only geometry proxies: **{summary['geometry_visual_proxies']}**",
        "",
        "## Refresh queue",
        "",
    ]

    if not report["refresh_worklist"]:
        lines.extend(
            [
                "No sources are refresh-due, stale, or missing provenance for this audit date.",
                "",
            ]
        )
    else:
        for group in report["refresh_worklist"]:
            lines.extend([f"### {group['seller']}", ""])
            seen_sources: set[str] = set()
            for row in group["components"]:
                source_key = row["snapshot_id"] or row["component_id"]
                if source_key in seen_sources:
                    continue
                seen_sources.add(source_key)
                same_source = [
                    item
                    for item in group["components"]
                    if (item["snapshot_id"] or item["component_id"]) == source_key
                ]
                component_ids = ", ".join(
                    item["component_id"] for item in same_source
                )
                age = (
                    "unknown age"
                    if row["age_days"] is None
                    else f"{row['age_days']} days old"
                )
                lines.append(
                    f"- **{row['status']}** · {source_key} · {age} · {component_ids}"
                )
                if row["source_url"]:
                    lines.append(f"  - source: {row['source_url']}")
                if row["reasons"]:
                    lines.append(f"  - reason: {row['reasons'][0]}")
            lines.append("")

    if report["geometry_visual_proxies"]:
        lines.extend(["## Visualization-only geometry proxies", ""])
        for row in report["geometry_visual_proxies"]:
            note = row["note"] or "Visualization proxy; do not use for fit or fabrication."
            lines.append(f"- {row['id']} ({row['label']}): {note}")
        lines.append("")

    lines.extend(
        [
            "## Refresh procedure",
            "",
            (
                "For each queued source, re-open the official vendor or named retailer "
                "page, verify the exact interface facts used by the catalog, record "
                "availability or price only as a dated snapshot, and update the "
                "component source date plus snapshot verification date. A source refresh "
                "never creates purchase, fabrication, charging, or powered-operation authority."
            ),
            "",
        ]
    )
    return "\\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build deterministic per-component Board Builder source health."
    )
    parser.add_argument("--as-of", required=True, help="Audit date YYYY-MM-DD.")
    parser.add_argument("--fresh-days", type=int, default=14)
    parser.add_argument("--refresh-due-days", type=int, default=30)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--worklist", type=Path)
    parser.add_argument("--fail-on-integrity", action="store_true")
    args = parser.parse_args()

    snapshot = args.snapshot
    if snapshot is not None and not snapshot.is_absolute():
        snapshot = ROOT / snapshot

    report = build_health(
        as_of=parse_day(args.as_of, "--as-of"),
        fresh_days=args.fresh_days,
        refresh_due_days=args.refresh_due_days,
        snapshot_path=snapshot,
    )
    payload = json.dumps(report, indent=2) + "\\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")

    if args.worklist:
        args.worklist.parent.mkdir(parents=True, exist_ok=True)
        args.worklist.write_text(render_worklist(report), encoding="utf-8")

    if args.fail_on_integrity and not report["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
