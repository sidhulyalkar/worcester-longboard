#!/usr/bin/env python3
"""Render the current X1 conservative checkout/source packet from repository authority."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.evaluate_build_authority import evaluate
from tools.validate_procurement_manifest import validate_manifest


def _max_cost(item: dict) -> float:
    qty = int(item["qty"])
    if "unit_price_usd" in item:
        return qty * float(item["unit_price_usd"])
    if "unit_price_ceiling_usd" in item:
        return qty * float(item["unit_price_ceiling_usd"])
    return qty * float(item["unit_price_range_usd"][1])


def render_packet(plan: dict, procurement: dict) -> str:
    validation = validate_manifest(procurement)
    if not validation["valid"]:
        raise ValueError("invalid procurement manifest: " + "; ".join(validation["errors"]))

    authority = evaluate(plan, procurement, [])
    states = authority["procurement_items"]
    items = procurement["items"]
    buy_now = [x for x in items if x["stage"] == "BUY_NOW" and states[x["id"]]["orderable"]]
    measure = [x for x in items if x["stage"] == "MEASURE_FIRST" and states[x["id"]]["orderable"]]
    blocked = [x for x in items if not states[x["id"]]["orderable"]]
    buy_total = sum(_max_cost(x) for x in buy_now)

    lines = [
        "# Worcester X1 current procurement packet",
        "",
        f"Manifest date: {procurement.get('as_of')}",
        "",
        "This packet is generated from repository authority. It is not ride or fabrication authorization.",
        "",
        "## Issue #4 bench checkout",
        "",
        f"Maximum if every BUY_NOW convenience item must be purchased: **${buy_total:.2f}**.",
        "Items marked `skip-if-owned` still require an equivalent tool/part for the procedure.",
        "",
        "| ID | Qty | Vendor/reference | Max subtotal | Purchase note |",
        "|---|---:|---|---:|---|",
    ]
    for item in buy_now:
        note = "skip-if-owned" if item.get("optional_if_owned") else "required new evidence hardware"
        lines.append(
            f"| {item['id']} | {item['qty']} | {item['vendor']} / {item['sku']} | ${_max_cost(item):.2f} | {note} |"
        )

    lines.extend([
        "",
        "## Eligible measurement-stage sourcing",
        "",
        "These are allowed to source/quote for their named evidence issues, but are **not part of the <$125 pilot checkout**.",
        "",
        "| ID | Qty | Vendor/reference | Max subtotal | Required for |",
        "|---|---:|---|---:|---|",
    ])
    for item in measure:
        lines.append(
            f"| {item['id']} | {item['qty']} | {item['vendor']} / {item['sku']} | ${_max_cost(item):.2f} | {item.get('required_for', '')} |"
        )

    lines.extend([
        "",
        "## Blocked candidates",
        "",
        "| ID | Stage | Why blocked |",
        "|---|---|---|",
    ])
    for item in blocked:
        reason = "; ".join(states[item["id"]]["blockers"])
        lines.append(f"| {item['id']} | {item['stage']} | {reason} |")

    lines.extend([
        "",
        "## Build capability boundary",
        "",
        f"- four-zone duplication: **{'OPEN' if authority['capabilities']['duplicate_four_fit_zones']['allowed'] else 'BLOCKED'}**",
        f"- unpowered chassis fabrication: **{'OPEN' if authority['capabilities']['fabricate_unpowered_chassis']['allowed'] else 'BLOCKED'}**",
        f"- power ordering: **{'OPEN' if authority['capabilities']['order_power_hardware']['allowed'] else 'BLOCKED'}**",
        f"- powered operation: **{'OPEN' if authority['capabilities']['powered_operation']['allowed'] else 'BLOCKED'}**",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", type=Path, default=Path("hardware/build_authority.json"))
    p.add_argument("--procurement", type=Path, default=Path("hardware/procurement_manifest.json"))
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    procurement = json.loads(args.procurement.read_text(encoding="utf-8"))
    text = render_packet(plan, procurement) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
