#!/usr/bin/env python3
"""Validate the dated source snapshot and complete planned BOM against procurement authority."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

POWER_TBD_IDS = {"ESC-DUAL", "MOTOR-6374", "BATTERY-12S4P"}


def _price(item: dict) -> float | None:
    if "unit_price_usd" in item:
        return float(item["unit_price_usd"])
    return None


def validate(procurement: dict, sources: dict, planned: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    if procurement.get("schema_version") != 1:
        errors.append("procurement schema_version must be 1")
    if sources.get("schema_version") != 1:
        errors.append("source snapshot schema_version must be 1")
    if planned.get("schema_version") != 1:
        errors.append("planned BOM schema_version must be 1")

    if sources.get("as_of") != procurement.get("as_of"):
        errors.append("source snapshot date must match procurement snapshot date")
    if sources.get("currency") != procurement.get("currency"):
        errors.append("source snapshot currency must match procurement currency")
    if sources.get("refresh_live_price_and_stock_before_checkout") is not True:
        errors.append("source snapshot must require live refresh before checkout")

    manifest = {item["id"]: item for item in procurement.get("items", []) if item.get("id")}
    seen: set[str] = set()
    for source in sources.get("sources", []):
        manifest_id = source.get("manifest_id")
        if manifest_id not in manifest:
            errors.append(f"source references unknown manifest item: {manifest_id}")
            continue
        if manifest_id in seen:
            errors.append(f"duplicate source entry for manifest item: {manifest_id}")
        seen.add(manifest_id)

        url = source.get("url")
        if url is not None and not (isinstance(url, str) and url.startswith("https://")):
            errors.append(f"{manifest_id}: source URL must be https")

        src_price = source.get("unit_price_usd")
        manifest_price = _price(manifest[manifest_id])
        if src_price is not None:
            try:
                src_price = float(src_price)
            except Exception:
                errors.append(f"{manifest_id}: source unit price is not numeric")
            else:
                if not math.isfinite(src_price) or src_price < 0:
                    errors.append(f"{manifest_id}: invalid source unit price")
                if manifest_price is not None and abs(src_price - manifest_price) > 1e-9:
                    errors.append(
                        f"{manifest_id}: source price ${src_price:.2f} disagrees with manifest ${manifest_price:.2f}"
                    )

        if manifest[manifest_id].get("stage") == "POWER_GATED" and source.get("recommended") is True:
            errors.append(f"{manifest_id}: POWER_GATED source cannot be recommended for purchase")

    expected_source_ids = {
        item_id
        for item_id, item in manifest.items()
        if item_id not in POWER_TBD_IDS
    }
    missing = sorted(expected_source_ids - seen)
    if missing:
        errors.append("dated source snapshot missing manifest IDs: " + ", ".join(missing))

    if "TIRE-T2-9" in manifest:
        tire = manifest["TIRE-T2-9"]
        if not tire.get("defer_until"):
            errors.append("TIRE-T2-9 must remain explicitly deferred")
        notes = str(tire.get("notes", ""))
        if "Rockstar II" not in notes:
            errors.append("TIRE-T2-9 must record the standard Rockstar II compatibility caveat")

    subsystems = planned.get("subsystems", [])
    ids = [x.get("id") for x in subsystems]
    if len(ids) != len(set(ids)):
        errors.append("planned BOM subsystem IDs must be unique")
    if "FIT-PILOT" not in ids or "TRACTION-BATTERY" not in ids or "DRIVE" not in ids:
        errors.append("planned BOM must span fit pilot, drive, and traction battery")

    for subsystem in subsystems:
        sid = subsystem.get("id")
        status = subsystem.get("status")
        if sid in {"DRIVE", "MOTOR-CONTROL", "TRACTION-BATTERY"} and status == "ORDER_NOW":
            errors.append(f"{sid}: powered subsystem cannot be ORDER_NOW")
        if not subsystem.get("contents"):
            errors.append(f"{sid}: subsystem must list contents")

    if planned.get("rules", {}).get("no_powered_operation_authorized") is not True:
        errors.append("planned BOM must explicitly keep powered operation unauthorized")
    if planned.get("rules", {}).get("professional_traction_battery_only") is not True:
        errors.append("planned BOM must preserve professional traction-battery requirement")

    buy_now_sources = [
        s for s in sources.get("sources", [])
        if manifest.get(s.get("manifest_id"), {}).get("stage") == "BUY_NOW"
    ]
    priced_buy_now = [float(s["unit_price_usd"]) * int(s.get("qty", 1)) for s in buy_now_sources if "unit_price_usd" in s]
    if priced_buy_now:
        warnings.append(
            f"dated source snapshot has ${sum(priced_buy_now):.2f} of exact-priced BUY_NOW examples before ceiling-priced local items"
        )

    return {"valid": not errors, "errors": errors, "warnings": warnings}


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    procurement_path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "hardware/procurement_manifest.json"
    sources_path = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "hardware/order_sources_2026-09-11.json"
    planned_path = Path(sys.argv[3]) if len(sys.argv) > 3 else root / "hardware/planned_system_bom.json"
    report = validate(
        json.loads(procurement_path.read_text(encoding="utf-8")),
        json.loads(sources_path.read_text(encoding="utf-8")),
        json.loads(planned_path.read_text(encoding="utf-8")),
    )
    print(json.dumps(report, indent=2))
    if not report["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
