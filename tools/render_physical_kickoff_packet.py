#!/usr/bin/env python3
"""Render a Worcester X1 Day-0 physical kickoff packet."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.evaluate_build_authority import evaluate
from tools.validate_procurement_manifest import validate_manifest

ALLOWED_STATUS = {
    "UNASSESSED",
    "NEED_BUY",
    "OWNED_EQUIVALENT",
    "OWNED_EXACT_UNUSED",
}


def _max_cost(item: dict) -> float:
    qty = int(item["qty"])
    if "unit_price_usd" in item:
        return qty * float(item["unit_price_usd"])
    if "unit_price_ceiling_usd" in item:
        return qty * float(item["unit_price_ceiling_usd"])
    return qty * float(item["unit_price_range_usd"][1])


def _validate_inventory(inventory: dict, buy_now_ids: set[str]) -> dict[str, dict]:
    if inventory.get("schema_version") != 1:
        raise ValueError("inventory schema_version must be 1")
    if inventory.get("scope") != "x1_physical_kickoff_inventory":
        raise ValueError("wrong kickoff inventory scope")

    rows = inventory.get("items")
    if not isinstance(rows, list):
        raise ValueError("inventory items must be a list")

    out: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("inventory item must be an object")
        item_id = row.get("id")
        if item_id not in buy_now_ids:
            raise ValueError(f"inventory may contain only current BUY_NOW ids: {item_id}")
        if item_id in out:
            raise ValueError(f"duplicate inventory id: {item_id}")
        status = row.get("status")
        if status not in ALLOWED_STATUS:
            raise ValueError(f"{item_id}: invalid status {status}")
        qty = row.get("qty_owned_verified")
        if not isinstance(qty, int) or qty < 0:
            raise ValueError(f"{item_id}: qty_owned_verified must be a nonnegative integer")
        out[item_id] = row
    return out


def render(plan: dict, procurement: dict, inventory: dict | None = None) -> str:
    validation = validate_manifest(procurement)
    if not validation["valid"]:
        raise ValueError("invalid procurement manifest: " + "; ".join(validation["errors"]))

    authority = evaluate(plan, procurement, [])
    states = authority["procurement_items"]
    buy_now = [
        item for item in procurement["items"]
        if item["stage"] == "BUY_NOW" and states[item["id"]]["orderable"]
    ]
    buy_now_ids = {item["id"] for item in buy_now}
    inventory_rows = (
        _validate_inventory(inventory, buy_now_ids)
        if inventory is not None
        else {}
    )

    unexpectedly_open = [
        item["id"]
        for item in procurement["items"]
        if item["stage"] != "BUY_NOW" and states[item["id"]]["orderable"]
    ]
    if unexpectedly_open:
        raise ValueError(
            "public/no-evidence kickoff refuses unexpectedly open non-BUY_NOW items: "
            + ", ".join(unexpectedly_open)
        )

    lines = [
        "# Worcester X1 Day-0 physical kickoff",
        "",
        "This packet is generated from the public/no-private-evidence repository state.",
        "It is an execution checklist, not fabrication or ride authority.",
        "",
        "## 1. Do before ordering anything",
        "",
        "- [ ] Inventory optional tools/materials before buying duplicates.",
        "- [ ] Generate/print the three full-scale Rev-C deck envelopes.",
        "- [ ] Build cardboard/foam-board stance mockups for Comp 95, Pro Warren III, and Agent.",
        "- [ ] Perform only the zero-cost stance/remount comparison in docs/rev_c_no_parts_chassis_experiment.md.",
        "- [ ] Do not order chassis, brake, wheel upgrades, drivetrain, ESC, traction battery, charger, or powered-board hardware.",
        "",
        "## 2. Current Cart A status",
        "",
        "| ID | Qty | Vendor/reference | Max subtotal | Inventory | Action |",
        "|---|---:|---|---:|---|---|",
    ]

    remaining_max = 0.0
    for item in buy_now:
        row = inventory_rows.get(item["id"], {})
        status = row.get("status", "UNASSESSED")
        qty_owned = int(row.get("qty_owned_verified", 0))
        exact = row.get("exact_part_match") is True
        known = row.get("unused_or_known_history") is True
        required_qty = int(item["qty"])
        optional = item.get("optional_if_owned") is True

        action = "ORDER_OR_VERIFY"
        charge = _max_cost(item)
        if optional and status in {"OWNED_EQUIVALENT", "OWNED_EXACT_UNUSED"} and qty_owned >= required_qty:
            action = "VERIFY_OWNED_AND_SKIP_DUPLICATE"
            charge = 0.0
        elif (
            not optional
            and status == "OWNED_EXACT_UNUSED"
            and qty_owned >= required_qty
            and exact
            and known
        ):
            action = "VERIFY_EXACT_UNUSED_WITH_ISSUE4_GUIDE"
            charge = 0.0
        elif status == "NEED_BUY":
            action = "ORDER"
        elif status == "UNASSESSED":
            action = "INVENTORY_FIRST"

        remaining_max += charge
        lines.append(
            f"| {item['id']} | {required_qty} | {item['vendor']} / {item['sku']} | "
            f"${_max_cost(item):.2f} | {status} | {action} |"
        )

    lines.extend([
        "",
        f"Current maximum remaining checkout after recorded owned items: **${remaining_max:.2f}** before shipping/tax.",
        "",
        "Required evidence hardware cannot be skipped merely because a vaguely similar part is in a drawer.",
        "For a required exact item, only an exact, physically verified, unused/known-history match can move it to verification instead of purchase.",
        "",
        "## 3. Zero-cost parallel chassis work",
        "",
        "Run:",
        "",
        "    python tools/init_rev_c_chassis_release_session.py rider/private/rev_c_release",
        "",
        "Then use the generated full-scale deck-envelope SVGs for the three-way stance/remount experiment.",
        "Do not fabricate structural chassis parts from those envelope templates.",
        "",
        "## 4. When Cart A arrives",
        "",
        "1. Photograph packaging/SKU/revision privately.",
        "2. Assign stable hardware IDs before assembly.",
        "3. Inspect for shipping damage.",
        "4. Verify received load-cell mounting pattern and fixed/loaded orientation.",
        "5. Verify HX711 board revision and RATE state.",
        "6. Measure the real screw/washer stack before choosing M5 screw length.",
        "7. Generate the one-zone CAD package with python cad/generate_one_zone_pilot.py.",
        "8. Assemble only one active sensor path plus one untouched spare.",
        "9. Create and validate Issue #61 calibration-mass reference evidence before creating the Issue #4 session.",
        "10. Initialize the private pilot session from both the Issue #59 hardware authority and Issue #61 mass authority.",
        "",
        "## 5. What remains blocked",
        "",
        "| Item | Stage | State |",
        "|---|---|---|",
    ])

    for item in procurement["items"]:
        if item["stage"] == "BUY_NOW":
            continue
        state = states[item["id"]]
        lines.append(
            f"| {item['id']} | {item['stage']} | "
            f"{'OPEN' if state['orderable'] else 'BLOCKED'} |"
        )

    measure_open = any(
        states[item["id"]]["orderable"]
        for item in procurement["items"]
        if item["stage"] == "MEASURE_FIRST"
    )
    lines.extend([
        "",
        "## 6. Authority boundary",
        "",
        f"- Issue #4 / BUY_NOW checkout: **{'OPEN' if buy_now else 'BLOCKED'}**",
        f"- chassis/brake MEASURE_FIRST purchase: **{'OPEN' if measure_open else 'BLOCKED'}**",
        f"- power ordering: **{'OPEN' if authority['capabilities']['order_power_hardware']['allowed'] else 'BLOCKED'}**",
        f"- powered operation: **{'OPEN' if authority['capabilities']['powered_operation']['allowed'] else 'BLOCKED'}**",
        f"- public operation: **{'OPEN' if authority['capabilities']['public_operation']['allowed'] else 'BLOCKED'}**",
        f"- dog-accompanied operation: **{'OPEN' if authority['capabilities']['dog_accompanied_operation']['allowed'] else 'BLOCKED'}**",
        "",
        "If any expensive or powered stage unexpectedly opens in this no-evidence packet, stop and treat it as a repository regression.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=Path("hardware/build_authority.json"))
    parser.add_argument("--procurement", type=Path, default=Path("hardware/procurement_manifest.json"))
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    procurement = json.loads(args.procurement.read_text(encoding="utf-8"))
    inventory = (
        json.loads(args.inventory.read_text(encoding="utf-8"))
        if args.inventory
        else None
    )
    text = render(plan, procurement, inventory) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
