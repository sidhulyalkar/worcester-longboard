#!/usr/bin/env python3
"""Validate a Worcester X1 Cart A checkout record.

This validates that a private checkout record stays inside the already-existing
BUY_NOW authority. It does not grant procurement, fabrication, or operation authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.evaluate_build_authority import evaluate
from tools.render_physical_kickoff_packet import _validate_inventory
from tools.validate_ordering_spec import validate as validate_ordering_spec
from tools.validate_procurement_manifest import validate_manifest

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "hardware/build_authority.json"
PROCUREMENT = ROOT / "hardware/procurement_manifest.json"
SOURCES = ROOT / "hardware/order_sources_2026-10-01.json"
PLANNED = ROOT / "hardware/planned_system_bom.json"

ALLOWED_STATUS = {"DRAFT", "READY_TO_ORDER", "ORDERED"}
ALLOWED_RESOLUTION = {
    "UNRESOLVED",
    "ORDER",
    "USE_OWNED_EXACT",
    "USE_OWNED_EQUIVALENT",
}


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _finite_nonnegative(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) >= 0
    )


def _max_unit_price(item: dict) -> float:
    if "unit_price_usd" in item:
        return float(item["unit_price_usd"])
    if "unit_price_ceiling_usd" in item:
        return float(item["unit_price_ceiling_usd"])
    return float(item["unit_price_range_usd"][1])


def _parse_timestamp(errors: list[str], label: str, value: Any) -> datetime | None:
    if not _nonempty(value):
        errors.append(f"{label} must be a nonempty timezone-aware ISO-8601 timestamp")
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{label} is not valid ISO-8601")
        return None
    if dt.tzinfo is None or dt.utcoffset() is None:
        errors.append(f"{label} must include a timezone offset")
        return None
    return dt.astimezone(timezone.utc)


def validate(
    checkout: dict,
    inventory: dict,
    plan: dict | None = None,
    procurement: dict | None = None,
    sources: dict | None = None,
    planned: dict | None = None,
) -> dict:
    plan = plan or json.loads(PLAN.read_text(encoding="utf-8"))
    procurement = procurement or json.loads(PROCUREMENT.read_text(encoding="utf-8"))
    sources = sources or json.loads(SOURCES.read_text(encoding="utf-8"))
    planned = planned or json.loads(PLANNED.read_text(encoding="utf-8"))
    errors: list[str] = []

    procurement_validation = validate_manifest(procurement)
    if not procurement_validation["valid"]:
        errors.extend(
            "procurement manifest: " + item
            for item in procurement_validation["errors"]
        )
    ordering_validation = validate_ordering_spec(procurement, sources, planned)
    if not ordering_validation["valid"]:
        errors.extend(
            "ordering spec: " + item
            for item in ordering_validation["errors"]
        )

    if checkout.get("schema_version") != 1:
        errors.append("checkout schema_version must be 1")
    if checkout.get("scope") != "x1_cart_a_checkout_record":
        errors.append("wrong checkout scope")
    expected_issue = procurement.get("rules", {}).get("cart_a_checkout_issue")
    if checkout.get("issue") != expected_issue:
        errors.append("checkout issue does not match procurement authority")
    status = checkout.get("status")
    if status not in ALLOWED_STATUS:
        errors.append("checkout status must be DRAFT, READY_TO_ORDER, or ORDERED")
    if not _nonempty(checkout.get("checkout_id")):
        errors.append("checkout_id must be nonempty")

    for key in (
        "fabrication_authority",
        "powered_operation_authorized",
        "public_operation_authorized",
        "dog_accompanied_operation_authorized",
    ):
        if checkout.get(key) is not False:
            errors.append(f"{key} must be false")

    expected_source_path = procurement.get("rules", {}).get("source_snapshot_path")
    if checkout.get("source_snapshot_path") != expected_source_path:
        errors.append("checkout source_snapshot_path does not match procurement authority")
    if checkout.get("source_snapshot_as_of") != sources.get("as_of"):
        errors.append("checkout source_snapshot_as_of does not match source snapshot")
    if checkout.get("source_snapshot_sha256") != _digest(sources):
        errors.append("checkout source snapshot fingerprint is stale or incorrect")

    authority = evaluate(plan, procurement, [])
    states = authority["procurement_items"]
    buy_now = [
        item
        for item in procurement.get("items", [])
        if item.get("stage") == "BUY_NOW"
        and states.get(item.get("id"), {}).get("orderable") is True
    ]
    buy_ids = {item["id"] for item in buy_now}
    unexpectedly_open = [
        item["id"]
        for item in procurement.get("items", [])
        if item.get("stage") != "BUY_NOW"
        and states.get(item.get("id"), {}).get("orderable") is True
    ]
    if unexpectedly_open:
        errors.append(
            "public no-evidence state unexpectedly opens non-BUY_NOW items: "
            + ", ".join(sorted(unexpectedly_open))
        )

    try:
        inventory_rows = _validate_inventory(inventory, buy_ids)
    except ValueError as exc:
        errors.append(f"inventory: {exc}")
        inventory_rows = {}

    inventory_at = None
    if status in {"READY_TO_ORDER", "ORDERED"}:
        inventory_at = _parse_timestamp(
            errors,
            "inventory.inventory_checked_at_utc",
            inventory.get("inventory_checked_at_utc"),
        )
        if checkout.get("inventory_checked_at_utc") != inventory.get("inventory_checked_at_utc"):
            errors.append("checkout inventory_checked_at_utc does not match inventory")

    checkout_at = None
    if status in {"READY_TO_ORDER", "ORDERED"}:
        checkout_at = _parse_timestamp(
            errors,
            "checkout_at_utc",
            checkout.get("checkout_at_utc"),
        )
        if (
            checkout_at is not None
            and inventory_at is not None
            and inventory_at > checkout_at
        ):
            errors.append("inventory cannot be checked after checkout timestamp")

    source_by_id = {
        row["manifest_id"]: row
        for row in sources.get("sources", [])
        if isinstance(row, dict) and _nonempty(row.get("manifest_id"))
    }
    refresh_ids = set(sources.get("refresh_scope_manifest_ids", []))

    policy = checkout.get("source_freshness_policy")
    if not isinstance(policy, dict):
        errors.append("source_freshness_policy must be an object")
        policy = {}
    procurement_rules = procurement.get("rules", {})
    expected_policy = {
        "max_refresh_scope_age_days": procurement_rules.get(
            "cart_a_refresh_scope_max_age_days"
        ),
        "require_in_stock_for_refresh_scope": procurement_rules.get(
            "cart_a_require_stock_recheck_at_checkout"
        ),
        "price_or_stock_change_requires_snapshot_refresh": procurement_rules.get(
            "cart_a_price_or_stock_change_requires_source_refresh"
        ),
        "authority_source": "hardware/procurement_manifest.json",
    }
    if policy != expected_policy:
        errors.append(
            "source_freshness_policy does not match procurement authority"
        )
    max_age = expected_policy["max_refresh_scope_age_days"]
    if not isinstance(max_age, int) or isinstance(max_age, bool) or max_age < 0:
        errors.append(
            "procurement cart_a_refresh_scope_max_age_days must be nonnegative"
        )
        max_age = 0
    if expected_policy["require_in_stock_for_refresh_scope"] is not True:
        errors.append(
            "procurement authority must require refresh-scope stock recheck"
        )
    if (
        expected_policy["price_or_stock_change_requires_snapshot_refresh"]
        is not True
    ):
        errors.append(
            "procurement authority must require refresh after price/stock change"
        )

    rows = checkout.get("items")
    if not isinstance(rows, list):
        errors.append("checkout items must be a list")
        rows = []
    checkout_rows: dict[str, dict] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"checkout item {index} must be an object")
            continue
        item_id = row.get("id")
        if item_id not in buy_ids:
            errors.append(f"checkout may contain only orderable BUY_NOW ids: {item_id}")
            continue
        if item_id in checkout_rows:
            errors.append(f"duplicate checkout item: {item_id}")
            continue
        checkout_rows[item_id] = row

    if set(checkout_rows) != buy_ids:
        missing = sorted(buy_ids - set(checkout_rows))
        extra = sorted(set(checkout_rows) - buy_ids)
        if missing:
            errors.append("checkout missing BUY_NOW items: " + ", ".join(missing))
        if extra:
            errors.append("checkout has unexpected items: " + ", ".join(extra))

    merchandise_total = 0.0
    unresolved: list[str] = []
    ordered_ids: list[str] = []
    owned_ids: list[str] = []
    manifest_by_id = {item["id"]: item for item in buy_now}

    for item_id, item in manifest_by_id.items():
        row = checkout_rows.get(item_id)
        if row is None:
            continue
        resolution = row.get("resolution")
        if resolution not in ALLOWED_RESOLUTION:
            errors.append(f"{item_id}: invalid resolution {resolution}")
            continue
        if resolution == "UNRESOLVED":
            unresolved.append(item_id)

        required_qty = int(item["qty"])
        if row.get("required_qty") != required_qty:
            errors.append(f"{item_id}: required_qty does not match procurement manifest")
        if row.get("optional_if_owned") is not (item.get("optional_if_owned") is True):
            errors.append(f"{item_id}: optional_if_owned does not match procurement manifest")

        inv = inventory_rows.get(item_id, {})
        owned_qty = int(inv.get("qty_owned_verified", 0))
        if row.get("owned_qty_verified") != owned_qty:
            errors.append(f"{item_id}: owned_qty_verified does not match inventory")

        if resolution == "USE_OWNED_EXACT":
            owned_ids.append(item_id)
            if (
                inv.get("status") != "OWNED_EXACT_UNUSED"
                or owned_qty < required_qty
                or inv.get("exact_part_match") is not True
                or inv.get("unused_or_known_history") is not True
            ):
                errors.append(
                    f"{item_id}: USE_OWNED_EXACT requires exact quantity and known history"
                )
            if row.get("ordered_qty") != 0:
                errors.append(f"{item_id}: owned resolution must have ordered_qty=0")

        elif resolution == "USE_OWNED_EQUIVALENT":
            owned_ids.append(item_id)
            if item.get("optional_if_owned") is not True:
                errors.append(
                    f"{item_id}: non-optional evidence hardware cannot use owned equivalent"
                )
            if (
                inv.get("status") not in {"OWNED_EQUIVALENT", "OWNED_EXACT_UNUSED"}
                or owned_qty < required_qty
            ):
                errors.append(
                    f"{item_id}: owned equivalent resolution is not supported by inventory"
                )
            if row.get("ordered_qty") != 0:
                errors.append(f"{item_id}: owned resolution must have ordered_qty=0")

        elif resolution == "ORDER":
            ordered_ids.append(item_id)
            if row.get("ordered_qty") != required_qty:
                errors.append(f"{item_id}: ordered_qty must equal required_qty")
            if not _nonempty(row.get("seller")):
                errors.append(f"{item_id}: seller must be nonempty")
            if not _nonempty(row.get("sku")):
                errors.append(f"{item_id}: sku must be nonempty")
            price = row.get("unit_price_usd")
            if not _finite_nonnegative(price):
                errors.append(f"{item_id}: unit_price_usd must be finite and nonnegative")
                price_value = 0.0
            else:
                price_value = float(price)
                if price_value > _max_unit_price(item) + 1e-9:
                    errors.append(
                        f"{item_id}: checkout price exceeds procurement unit-price authority"
                    )
            merchandise_total += required_qty * price_value

            if row.get("stock_confirmed_at_checkout") is not True and status in {"READY_TO_ORDER", "ORDERED"}:
                errors.append(f"{item_id}: stock must be confirmed at checkout")

            if item_id in refresh_ids:
                source = source_by_id.get(item_id)
                if source is None:
                    errors.append(f"{item_id}: refreshed source entry is missing")
                else:
                    for key, source_key in (
                        ("seller", "seller"),
                        ("sku", "sku"),
                        ("source_url", "url"),
                        ("source_last_verified_as_of", "last_verified_as_of"),
                    ):
                        if row.get(key) != source.get(source_key):
                            errors.append(
                                f"{item_id}: {key} does not match refreshed source snapshot"
                            )
                    if row.get("source_snapshot_required") is not True:
                        errors.append(f"{item_id}: source_snapshot_required must be true")
                    if status in {"READY_TO_ORDER", "ORDERED"}:
                        if row.get("source_rechecked_at_checkout") is not True:
                            errors.append(
                                f"{item_id}: refreshed source must be rechecked at checkout"
                            )
                        if source.get("availability_status") != "IN_STOCK":
                            errors.append(
                                f"{item_id}: refreshed source is not recorded IN_STOCK"
                            )
                        if checkout_at is not None:
                            try:
                                verified_date = datetime.fromisoformat(
                                    str(source.get("last_verified_as_of"))
                                ).date()
                            except ValueError:
                                errors.append(
                                    f"{item_id}: invalid last_verified_as_of date"
                                )
                            else:
                                age_days = (
                                    checkout_at.date() - verified_date
                                ).days
                                if age_days < 0:
                                    errors.append(
                                        f"{item_id}: source verification is dated after checkout"
                                    )
                                elif age_days > max_age:
                                    errors.append(
                                        f"{item_id}: refreshed source is {age_days} days old; "
                                        "refresh snapshot before checkout"
                                    )
                        source_price = source.get("unit_price_usd")
                        if source_price is not None and _finite_nonnegative(price):
                            if abs(float(price) - float(source_price)) > 1e-9:
                                errors.append(
                                    f"{item_id}: checkout price changed; refresh source snapshot"
                                )
            else:
                if row.get("source_snapshot_required") is not False:
                    errors.append(f"{item_id}: source_snapshot_required must be false")

            if status == "ORDERED" and not _nonempty(row.get("order_confirmation_ref")):
                errors.append(
                    f"{item_id}: ORDERED checkout requires order_confirmation_ref"
                )

    if status in {"READY_TO_ORDER", "ORDERED"} and unresolved:
        errors.append(
            "checkout has unresolved BUY_NOW items: " + ", ".join(sorted(unresolved))
        )

    ceiling = float(procurement["rules"]["buy_now_max_total_usd"])
    if merchandise_total > ceiling + 1e-9:
        errors.append(
            f"Cart A merchandise total ${merchandise_total:.2f} exceeds "
            f"${ceiling:.2f} BUY_NOW ceiling"
        )

    recorded_merchandise = checkout.get("merchandise_total_usd")
    if status in {"READY_TO_ORDER", "ORDERED"}:
        if not _finite_nonnegative(recorded_merchandise):
            errors.append("merchandise_total_usd must be recorded")
        elif abs(float(recorded_merchandise) - merchandise_total) > 0.01:
            errors.append("merchandise_total_usd does not match ordered lines")

    shipping = checkout.get("shipping_usd")
    tax = checkout.get("tax_usd")
    order_total = checkout.get("order_total_usd")
    if status == "ORDERED":
        for label, value in (
            ("shipping_usd", shipping),
            ("tax_usd", tax),
            ("order_total_usd", order_total),
        ):
            if not _finite_nonnegative(value):
                errors.append(f"{label} must be recorded for ORDERED checkout")
        if all(_finite_nonnegative(v) for v in (shipping, tax, order_total)):
            expected_total = merchandise_total + float(shipping) + float(tax)
            if abs(float(order_total) - expected_total) > 0.01:
                errors.append("order_total_usd does not match merchandise + shipping + tax")

    checkout_ready = (
        not errors
        and status in {"READY_TO_ORDER", "ORDERED"}
        and not unresolved
    )
    order_record_complete = not errors and status == "ORDERED"

    report = {
        "schema_version": 1,
        "authority": "x1_cart_a_checkout_evidence",
        "valid": not errors,
        "errors": errors,
        "checkout_id": checkout.get("checkout_id"),
        "checkout_status": status,
        "checkout_record_sha256": _digest(checkout),
        "source_snapshot_sha256": _digest(sources),
        "ordered_item_ids": sorted(ordered_ids),
        "owned_item_ids": sorted(owned_ids),
        "unresolved_item_ids": sorted(unresolved),
        "merchandise_total_usd": round(merchandise_total, 2),
        "buy_now_ceiling_usd": ceiling,
        "checkout_ready": checkout_ready,
        "order_record_complete": order_record_complete,
        "checkout_within_existing_buy_now_authority": checkout_ready,
        "procurement_authority": False,
        "physical_qualification_authority": False,
        "fabrication_authority": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
        "interpretation_boundary": (
            "This report validates a Cart A checkout against existing BUY_NOW "
            "authority. It does not create new procurement authority, qualify "
            "received hardware, authorize fabrication, or authorize operation."
        ),
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    checkout = json.loads(args.checkout.read_text(encoding="utf-8"))
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    report = validate(checkout, inventory)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["valid"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
