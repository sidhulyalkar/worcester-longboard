#!/usr/bin/env python3
"""Validate Worcester X1 Cart A receiving/reconciliation evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TRACKED_ROLES = {
    "LC-3135": ("PILOT_ACTIVE_CANDIDATE", "SPARE_UNTOUCHED"),
    "ADC-HX711": ("PILOT_ACTIVE_CANDIDATE", "SPARE_UNTOUCHED"),
    "MCU-ESP32S3": ("PILOT_ACTIVE_CANDIDATE",),
}
ALLOWED_STATUS = {"DRAFT", "PARTIAL", "COMPLETE"}


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


def _valid_authority(report: dict) -> bool:
    actual = report.get("authority_fingerprint_sha256")
    if not isinstance(actual, str) or not actual:
        return False
    unsigned = dict(report)
    unsigned.pop("authority_fingerprint_sha256", None)
    return actual == _digest(unsigned)


def validate(receiving: dict, checkout: dict, checkout_authority: dict) -> dict:
    errors: list[str] = []

    if receiving.get("schema_version") != 1:
        errors.append("receiving schema_version must be 1")
    if receiving.get("scope") != "x1_cart_a_receiving_record":
        errors.append("wrong receiving scope")
    if receiving.get("issue") != 56:
        errors.append("receiving issue must be 56")
    status = receiving.get("status")
    if status not in ALLOWED_STATUS:
        errors.append("receiving status must be DRAFT, PARTIAL, or COMPLETE")
    if not _nonempty(receiving.get("receiving_id")):
        errors.append("receiving_id must be nonempty")

    for key in (
        "physical_qualification_authority",
        "fabrication_authority",
        "powered_operation_authorized",
        "public_operation_authorized",
        "dog_accompanied_operation_authorized",
    ):
        if receiving.get(key) is not False:
            errors.append(f"{key} must be false")

    if checkout_authority.get("authority") != "x1_cart_a_checkout_evidence":
        errors.append("wrong checkout authority type")
    if not _valid_authority(checkout_authority):
        errors.append("checkout authority fingerprint is invalid")
    if checkout_authority.get("valid") is not True:
        errors.append("checkout authority must be valid")
    if checkout_authority.get("order_record_complete") is not True:
        errors.append("checkout authority must have order_record_complete=true")
    if checkout_authority.get("checkout_within_existing_buy_now_authority") is not True:
        errors.append("checkout authority must remain within existing BUY_NOW authority")
    for key in (
        "procurement_authority",
        "physical_qualification_authority",
        "fabrication_authority",
        "powered_operation_authorized",
        "public_operation_authorized",
        "dog_accompanied_operation_authorized",
    ):
        if checkout_authority.get(key) is not False:
            errors.append(f"checkout authority boundary violated: {key}")
    if checkout_authority.get("checkout_record_sha256") != _digest(checkout):
        errors.append("checkout authority does not match checkout record")
    if receiving.get("checkout_authority_fingerprint_sha256") != checkout_authority.get(
        "authority_fingerprint_sha256"
    ):
        errors.append("receiving record does not link exact checkout authority")
    if receiving.get("checkout_id") != checkout.get("checkout_id"):
        errors.append("receiving checkout_id does not match checkout")

    checkout_at = None
    if checkout.get("checkout_at_utc"):
        checkout_at = _parse_timestamp(errors, "checkout.checkout_at_utc", checkout.get("checkout_at_utc"))
    received_at = None
    if status in {"PARTIAL", "COMPLETE"}:
        received_at = _parse_timestamp(errors, "received_at_utc", receiving.get("received_at_utc"))
        if checkout_at is not None and received_at is not None and received_at < checkout_at:
            errors.append("receiving timestamp cannot predate checkout")

    ordered = {
        row["id"]: row
        for row in checkout.get("items", [])
        if isinstance(row, dict) and row.get("resolution") == "ORDER"
    }
    rows = receiving.get("items")
    if not isinstance(rows, list):
        errors.append("receiving items must be a list")
        rows = []

    by_id: dict[str, dict] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"receiving item {index} must be an object")
            continue
        item_id = row.get("id")
        if item_id not in ordered:
            errors.append(f"receiving may contain only ordered checkout items: {item_id}")
            continue
        if item_id in by_id:
            errors.append(f"duplicate receiving item: {item_id}")
            continue
        by_id[item_id] = row

    if set(by_id) != set(ordered):
        missing = sorted(set(ordered) - set(by_id))
        if missing:
            errors.append("receiving missing ordered items: " + ", ".join(missing))

    hardware_ids: set[str] = set()
    incomplete: list[str] = []
    tracked_ready: list[str] = []

    for item_id, checkout_row in ordered.items():
        row = by_id.get(item_id)
        if row is None:
            continue
        expected_qty = int(checkout_row.get("ordered_qty", 0))
        if row.get("expected_qty") != expected_qty:
            errors.append(f"{item_id}: expected_qty does not match checkout")
        if row.get("seller") != checkout_row.get("seller"):
            errors.append(f"{item_id}: seller does not match checkout")
        if row.get("expected_sku") != checkout_row.get("sku"):
            errors.append(f"{item_id}: expected_sku does not match checkout")
        if row.get("source_snapshot_required") is not (
            checkout_row.get("source_snapshot_required") is True
        ):
            errors.append(f"{item_id}: source_snapshot_required mismatch")

        qty_received = row.get("qty_received")
        if not isinstance(qty_received, int) or isinstance(qty_received, bool) or qty_received < 0:
            errors.append(f"{item_id}: qty_received must be a nonnegative integer")
            qty_received = 0
        if qty_received > expected_qty:
            errors.append(f"{item_id}: qty_received exceeds expected quantity")
        if qty_received < expected_qty:
            incomplete.append(item_id)
            if status == "COMPLETE":
                errors.append(f"{item_id}: COMPLETE receiving requires full quantity")
            if status == "PARTIAL" and not _nonempty(row.get("missing_or_backorder_note")):
                errors.append(
                    f"{item_id}: partial quantity requires missing_or_backorder_note"
                )

        if status == "COMPLETE":
            if row.get("substitution_observed") is not False:
                errors.append(f"{item_id}: substitution must be resolved before COMPLETE")
            if row.get("visible_damage_observed") is not False:
                errors.append(f"{item_id}: damaged shipment cannot be COMPLETE")

        if checkout_row.get("source_snapshot_required") is True and qty_received > 0:
            if row.get("package_sku_observed") != checkout_row.get("sku"):
                errors.append(f"{item_id}: observed package SKU does not match checkout")
            if row.get("substitution_observed") is not False:
                errors.append(f"{item_id}: refreshed exact-source item cannot be substituted")

        units = row.get("hardware_units")
        if not isinstance(units, list):
            errors.append(f"{item_id}: hardware_units must be a list")
            units = []

        required_roles = TRACKED_ROLES.get(item_id)
        if required_roles is not None:
            if len(units) != qty_received:
                errors.append(
                    f"{item_id}: tracked hardware_units count must equal qty_received"
                )
            roles: list[str] = []
            for unit_index, unit in enumerate(units):
                if not isinstance(unit, dict):
                    errors.append(f"{item_id}: hardware unit {unit_index} must be an object")
                    continue
                hid = unit.get("hardware_id")
                if not _nonempty(hid):
                    errors.append(f"{item_id}: hardware_id must be nonempty")
                elif hid in hardware_ids:
                    errors.append(f"duplicate hardware_id across receiving record: {hid}")
                else:
                    hardware_ids.add(hid)
                role = unit.get("role")
                if not _nonempty(role):
                    errors.append(f"{item_id}/{hid or unit_index}: role must be nonempty")
                else:
                    roles.append(role)
                if unit.get("exact_part_match") is not True:
                    errors.append(f"{item_id}/{hid or unit_index}: exact_part_match must be true")
                if unit.get("visible_damage_observed") is not False:
                    errors.append(f"{item_id}/{hid or unit_index}: visible damage is not acceptable")
                if unit.get("packaging_and_markings_recorded") is not True:
                    errors.append(
                        f"{item_id}/{hid or unit_index}: packaging_and_markings_recorded must be true"
                    )
                if not _nonempty(unit.get("condition_note")):
                    errors.append(f"{item_id}/{hid or unit_index}: condition_note must be nonempty")

            if qty_received == expected_qty and tuple(sorted(roles)) != tuple(sorted(required_roles)):
                errors.append(
                    f"{item_id}: full tracked receipt must assign roles "
                    + ", ".join(required_roles)
                )
            elif (
                qty_received == expected_qty
                and status == "COMPLETE"
                and not any(role == "SPARE_UNTOUCHED" for role in roles)
                and "SPARE_UNTOUCHED" in required_roles
            ):
                errors.append(f"{item_id}: one untouched spare must be preserved")
            if qty_received == expected_qty and not any(
                error.startswith(f"{item_id}:") or error.startswith(f"{item_id}/")
                for error in errors
            ):
                tracked_ready.append(item_id)
        else:
            # Generic tools/materials do not need serialized hardware units.
            for unit in units:
                if isinstance(unit, dict) and _nonempty(unit.get("hardware_id")):
                    hid = unit["hardware_id"]
                    if hid in hardware_ids:
                        errors.append(f"duplicate hardware_id across receiving record: {hid}")
                    hardware_ids.add(hid)

    receiving_complete = (
        not errors
        and status == "COMPLETE"
        and not incomplete
    )
    issue4_materials_accounted_for = receiving_complete

    report = {
        "schema_version": 1,
        "authority": "x1_cart_a_receiving_evidence",
        "valid": not errors,
        "errors": errors,
        "receiving_id": receiving.get("receiving_id"),
        "checkout_id": receiving.get("checkout_id"),
        "checkout_authority_fingerprint_sha256": checkout_authority.get(
            "authority_fingerprint_sha256"
        ),
        "receiving_record_sha256": _digest(receiving),
        "receiving_status": status,
        "incomplete_item_ids": sorted(incomplete),
        "tracked_hardware_item_ids_ready": sorted(tracked_ready),
        "receiving_complete": receiving_complete,
        "issue4_materials_accounted_for": issue4_materials_accounted_for,
        "physical_qualification_authority": False,
        "fabrication_authority": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
        "interpretation_boundary": (
            "A complete receiving report proves only that the recorded Cart A "
            "shipment matches the fingerprinted checkout and passed receiving "
            "inspection. It does not qualify the load cell, HX711, MCU, fixture, "
            "fit rig, chassis, or any riding hardware."
        ),
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receiving", type=Path)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--checkout-authority", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    receiving = json.loads(args.receiving.read_text(encoding="utf-8"))
    checkout = json.loads(args.checkout.read_text(encoding="utf-8"))
    checkout_authority = json.loads(
        args.checkout_authority.read_text(encoding="utf-8")
    )
    report = validate(receiving, checkout, checkout_authority)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["valid"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
