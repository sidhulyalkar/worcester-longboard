#!/usr/bin/env python3
"""Initialize a private Worcester X1 Cart A checkout record from Day-0 inventory."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.evaluate_build_authority import evaluate
from tools.render_physical_kickoff_packet import _validate_inventory
from tools.validate_ordering_spec import validate as validate_ordering_spec
from tools.validate_procurement_manifest import validate_manifest

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "hardware/build_authority.json"
PROCUREMENT = ROOT / "hardware/procurement_manifest.json"
SOURCES = ROOT / "hardware/order_sources_2026-10-01.json"
TEMPLATE = ROOT / "hardware/x1_cart_a_checkout_template.json"


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _source_map(sources: dict) -> dict[str, dict]:
    return {
        row["manifest_id"]: row
        for row in sources.get("sources", [])
        if isinstance(row, dict) and isinstance(row.get("manifest_id"), str)
    }


def initialize(
    output_path: Path,
    inventory_path: Path,
    checkout_id: str,
) -> dict:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    procurement = json.loads(PROCUREMENT.read_text(encoding="utf-8"))
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))

    procurement_validation = validate_manifest(procurement)
    if not procurement_validation["valid"]:
        raise ValueError(
            "invalid procurement manifest: "
            + "; ".join(procurement_validation["errors"])
        )
    ordering_validation = validate_ordering_spec(
        procurement,
        sources,
        json.loads(
            (ROOT / "hardware/planned_system_bom.json").read_text(encoding="utf-8")
        ),
    )
    if not ordering_validation["valid"]:
        raise ValueError(
            "invalid ordering spec: " + "; ".join(ordering_validation["errors"])
        )

    authority = evaluate(plan, procurement, [])
    states = authority["procurement_items"]
    buy_now = [
        item
        for item in procurement["items"]
        if item["stage"] == "BUY_NOW" and states[item["id"]]["orderable"]
    ]
    buy_now_ids = {item["id"] for item in buy_now}
    inventory_rows = _validate_inventory(inventory, buy_now_ids)

    unexpectedly_open = [
        item["id"]
        for item in procurement["items"]
        if item["stage"] != "BUY_NOW" and states[item["id"]]["orderable"]
    ]
    if unexpectedly_open:
        raise ValueError(
            "refusing checkout initialization because non-BUY_NOW items are open: "
            + ", ".join(unexpectedly_open)
        )

    sources_by_id = _source_map(sources)
    refresh_ids = set(sources.get("refresh_scope_manifest_ids", []))
    rows = []
    for item in buy_now:
        item_id = item["id"]
        inv = inventory_rows.get(item_id, {})
        required_qty = int(item["qty"])
        qty_owned = int(inv.get("qty_owned_verified", 0))
        status = inv.get("status", "UNASSESSED")
        optional = item.get("optional_if_owned") is True
        exact_owned = (
            status == "OWNED_EXACT_UNUSED"
            and qty_owned >= required_qty
            and inv.get("exact_part_match") is True
            and inv.get("unused_or_known_history") is True
        )
        equivalent_owned = (
            optional
            and status in {"OWNED_EQUIVALENT", "OWNED_EXACT_UNUSED"}
            and qty_owned >= required_qty
        )

        if exact_owned and not optional:
            resolution = "USE_OWNED_EXACT"
        elif equivalent_owned:
            resolution = (
                "USE_OWNED_EXACT"
                if inv.get("exact_part_match") is True
                else "USE_OWNED_EQUIVALENT"
            )
        elif status == "NEED_BUY":
            resolution = "ORDER"
        else:
            resolution = "UNRESOLVED"

        source = sources_by_id.get(item_id, {})
        row = {
            "id": item_id,
            "required_qty": required_qty,
            "optional_if_owned": optional,
            "resolution": resolution,
            "owned_qty_verified": qty_owned,
            "ordered_qty": required_qty if resolution == "ORDER" else 0,
            "seller": source.get("seller", item.get("vendor", "")),
            "sku": source.get("sku", item.get("sku", "")),
            "source_url": source.get("url", ""),
            "source_last_verified_as_of": source.get("last_verified_as_of", ""),
            "source_snapshot_required": item_id in refresh_ids,
            "source_rechecked_at_checkout": False,
            "stock_confirmed_at_checkout": False,
            "unit_price_usd": source.get("unit_price_usd"),
            "order_confirmation_ref": "",
            "notes": "",
        }
        rows.append(row)

    rules = procurement["rules"]
    template["issue"] = rules["cart_a_checkout_issue"]
    template["source_freshness_policy"] = {
        "max_refresh_scope_age_days": rules[
            "cart_a_refresh_scope_max_age_days"
        ],
        "require_in_stock_for_refresh_scope": rules[
            "cart_a_require_stock_recheck_at_checkout"
        ],
        "price_or_stock_change_requires_snapshot_refresh": rules[
            "cart_a_price_or_stock_change_requires_source_refresh"
        ],
        "authority_source": "hardware/procurement_manifest.json",
    }

    template.update(
        {
            "checkout_id": checkout_id,
            "inventory_checked_at_utc": inventory.get("inventory_checked_at_utc", ""),
            "source_snapshot_path": procurement["rules"]["source_snapshot_path"],
            "source_snapshot_as_of": sources["as_of"],
            "source_snapshot_sha256": _digest(sources),
            "items": rows,
        }
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite checkout record: {output_path}")
    output_path.write_text(
        json.dumps(template, indent=2) + "\n",
        encoding="utf-8",
    )
    return template


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--checkout-id", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            initialize(args.output, args.inventory, args.checkout_id),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
