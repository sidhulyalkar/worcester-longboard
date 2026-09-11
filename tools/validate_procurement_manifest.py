#!/usr/bin/env python3
"""Validate Worcester X1 staged procurement authority."""
from __future__ import annotations

import json
import sys
from pathlib import Path

STAGES = {"BUY_NOW", "MEASURE_FIRST", "POWER_GATED"}


def _max_item_cost(item: dict) -> float:
    qty = int(item["qty"])
    if "unit_price_usd" in item:
        return qty * float(item["unit_price_usd"])
    if "unit_price_ceiling_usd" in item:
        return qty * float(item["unit_price_ceiling_usd"])
    if "unit_price_range_usd" in item:
        return qty * float(item["unit_price_range_usd"][1])
    raise ValueError(f"item {item['id']} has no price authority")


def validate_manifest(data: dict) -> dict:
    errors: list[str] = []
    ids: set[str] = set()
    buy_now_total = 0.0

    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    for item in data.get("items", []):
        item_id = item.get("id")
        if not item_id or item_id in ids:
            errors.append(f"duplicate or missing item id: {item_id}")
            continue
        ids.add(item_id)
        stage = item.get("stage")
        if stage not in STAGES:
            errors.append(f"{item_id}: invalid stage {stage}")
            continue
        try:
            max_cost = _max_item_cost(item)
        except Exception as exc:
            errors.append(str(exc))
            continue
        if max_cost < 0:
            errors.append(f"{item_id}: negative cost")
        if stage == "BUY_NOW":
            buy_now_total += max_cost
        if stage == "POWER_GATED" and data.get("rules", {}).get("power_gated_authorized") is True:
            errors.append("power-gated procurement cannot be globally authorized in this tranche")

    ceiling = float(data.get("rules", {}).get("buy_now_max_total_usd", 0))
    if buy_now_total > ceiling:
        errors.append(f"BUY_NOW ceiling exceeded: ${buy_now_total:.2f} > ${ceiling:.2f}")

    stages = {item["stage"] for item in data.get("items", []) if item.get("stage") in STAGES}
    if stages != STAGES:
        errors.append(f"manifest must exercise all stages, got {sorted(stages)}")

    return {
        "valid": not errors,
        "errors": errors,
        "buy_now_maximum_usd": round(buy_now_total, 2),
        "buy_now_ceiling_usd": ceiling,
        "item_count": len(ids),
        "power_gated_authorized": data.get("rules", {}).get("power_gated_authorized") is True,
    }


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "hardware/procurement_manifest.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    report = validate_manifest(data)
    print(json.dumps(report, indent=2))
    if not report["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
