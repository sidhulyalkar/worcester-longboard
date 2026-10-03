#!/usr/bin/env python3
"""Validate Issue #59 pilot hardware-selection provenance."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _valid_authority(report: dict, expected: str) -> bool:
    if report.get("authority") != expected:
        return False
    actual = report.get("authority_fingerprint_sha256")
    if not isinstance(actual, str) or not actual:
        return False
    unsigned = dict(report)
    unsigned.pop("authority_fingerprint_sha256", None)
    return actual == _digest(unsigned)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _parse_time(errors: list[str], label: str, value: Any) -> datetime | None:
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


def _rows(doc: dict, key: str = "items") -> dict[str, dict]:
    return {
        row["id"]: row
        for row in doc.get(key, [])
        if isinstance(row, dict) and _nonempty(row.get("id"))
    }


def _received_units(receiving: dict, item_id: str) -> list[dict]:
    row = _rows(receiving).get(item_id, {})
    units = row.get("hardware_units", [])
    return units if isinstance(units, list) else []


def _received_role_map(receiving: dict, item_id: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for unit in _received_units(receiving, item_id):
        if not isinstance(unit, dict):
            continue
        hid = unit.get("hardware_id")
        role = unit.get("role")
        if _nonempty(hid) and _nonempty(role):
            result[hid] = role
    return result


def validate(
    selection: dict,
    inventory: dict,
    checkout: dict,
    checkout_authority: dict,
    *,
    receiving: dict | None = None,
    receiving_authority: dict | None = None,
) -> dict:
    errors: list[str] = []

    if selection.get("schema_version") != 1:
        errors.append("selection schema_version must be 1")
    if selection.get("scope") != "x1_fit_pilot_hardware_selection_record":
        errors.append("wrong pilot hardware selection scope")
    if selection.get("issue") != 59:
        errors.append("pilot hardware selection issue must be 59")
    if not _nonempty(selection.get("selection_id")):
        errors.append("selection_id must be nonempty")

    selected_at = _parse_time(errors, "selected_at_utc", selection.get("selected_at_utc"))

    for key in (
        "physical_qualification_authority",
        "four_zone_duplication_authorized",
        "fabrication_authority",
        "powered_operation_authorized",
        "public_operation_authorized",
        "dog_accompanied_operation_authorized",
    ):
        if selection.get(key) is not False:
            errors.append(f"{key} must be false")

    if not _valid_authority(checkout_authority, "x1_cart_a_checkout_evidence"):
        errors.append("checkout authority fingerprint/type is invalid")
    if checkout_authority.get("valid") is not True or checkout_authority.get("checkout_ready") is not True:
        errors.append("checkout authority must be valid and checkout_ready")
    if checkout_authority.get("checkout_record_sha256") != _digest(checkout):
        errors.append("checkout authority does not match checkout record")
    if checkout_authority.get("inventory_record_sha256") != _digest(inventory):
        errors.append("checkout authority does not match inventory record")
    if selection.get("checkout_id") != checkout.get("checkout_id"):
        errors.append("selection checkout_id does not match checkout")
    if selection.get("checkout_authority_fingerprint_sha256") != checkout_authority.get(
        "authority_fingerprint_sha256"
    ):
        errors.append("selection does not link exact checkout authority")
    if selection.get("inventory_record_sha256") != _digest(inventory):
        errors.append("selection inventory fingerprint is stale or incorrect")

    checkout_at = None
    if checkout.get("checkout_at_utc"):
        checkout_at = _parse_time(errors, "checkout.checkout_at_utc", checkout.get("checkout_at_utc"))
        if selected_at is not None and checkout_at is not None and selected_at < checkout_at:
            errors.append("hardware selection cannot predate checkout")

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

    receiving_supplied = receiving is not None or receiving_authority is not None
    if receiving_supplied and (receiving is None or receiving_authority is None):
        errors.append("receiving record and authority must be supplied together")
    if receiving is not None and receiving_authority is not None:
        if not _valid_authority(receiving_authority, "x1_cart_a_receiving_evidence"):
            errors.append("receiving authority fingerprint/type is invalid")
        if receiving_authority.get("valid") is not True or receiving_authority.get("receiving_complete") is not True:
            errors.append("receiving authority must be valid and receiving_complete")
        if receiving_authority.get("receiving_record_sha256") != _digest(receiving):
            errors.append("receiving authority does not match receiving record")
        if receiving_authority.get("checkout_authority_fingerprint_sha256") != checkout_authority.get(
            "authority_fingerprint_sha256"
        ):
            errors.append("receiving authority does not descend from checkout authority")
        if selection.get("receiving_id") != receiving.get("receiving_id"):
            errors.append("selection receiving_id does not match receiving record")
        if selection.get("receiving_authority_fingerprint_sha256") != receiving_authority.get(
            "authority_fingerprint_sha256"
        ):
            errors.append("selection does not link exact receiving authority")
        received_at = _parse_time(errors, "receiving.received_at_utc", receiving.get("received_at_utc"))
        if selected_at is not None and received_at is not None and selected_at < received_at:
            errors.append("received hardware selection cannot predate receiving")
    else:
        if selection.get("receiving_id") not in ("", None):
            errors.append("receiving_id must be empty when no receiving evidence is supplied")
        if selection.get("receiving_authority_fingerprint_sha256") not in ("", None):
            errors.append(
                "receiving_authority_fingerprint_sha256 must be empty without receiving evidence"
            )

    checkout_rows = _rows(checkout)
    inventory_rows = _rows(inventory)
    hardware = selection.get("hardware")
    if not isinstance(hardware, dict):
        errors.append("hardware must be an object")
        hardware = {}

    selected_ids: list[str] = []

    def validate_pair(name: str, item_id: str) -> None:
        entry = hardware.get(name)
        if not isinstance(entry, dict):
            errors.append(f"hardware.{name} must be an object")
            return
        if entry.get("item_id") != item_id:
            errors.append(f"hardware.{name}.item_id must be {item_id}")
        source_kind = entry.get("source_kind")
        active = entry.get("active_hardware_id")
        spare = entry.get("spare_hardware_id")
        if not _nonempty(active) or not _nonempty(spare):
            errors.append(f"{item_id}: active and spare hardware IDs must be nonempty")
            return
        if active == spare:
            errors.append(f"{item_id}: active and spare hardware IDs must differ")
        selected_ids.extend([active, spare])

        checkout_row = checkout_rows.get(item_id, {})
        resolution = checkout_row.get("resolution")
        if source_kind == "RECEIVED_ORDER":
            if resolution != "ORDER":
                errors.append(f"{item_id}: RECEIVED_ORDER requires checkout ORDER resolution")
            if receiving is None or receiving_authority is None:
                errors.append(f"{item_id}: RECEIVED_ORDER requires receiving evidence")
            else:
                role_map = _received_role_map(receiving, item_id)
                if role_map.get(active) != "PILOT_ACTIVE_CANDIDATE":
                    errors.append(
                        f"{item_id}: active ID is not the received PILOT_ACTIVE_CANDIDATE"
                    )
                if role_map.get(spare) != "SPARE_UNTOUCHED":
                    errors.append(
                        f"{item_id}: spare ID is not the received SPARE_UNTOUCHED unit"
                    )
        elif source_kind == "OWNED_EXACT_UNUSED":
            if resolution != "USE_OWNED_EXACT":
                errors.append(
                    f"{item_id}: OWNED_EXACT_UNUSED requires checkout USE_OWNED_EXACT resolution"
                )
            inv = inventory_rows.get(item_id, {})
            if (
                inv.get("status") != "OWNED_EXACT_UNUSED"
                or inv.get("exact_part_match") is not True
                or inv.get("unused_or_known_history") is not True
                or not isinstance(inv.get("qty_owned_verified"), int)
                or inv.get("qty_owned_verified", 0) < 2
            ):
                errors.append(
                    f"{item_id}: inventory does not prove >=2 exact unused/known-history units"
                )
        else:
            errors.append(
                f"{item_id}: source_kind must be RECEIVED_ORDER or OWNED_EXACT_UNUSED"
            )

    validate_pair("load_cell", "LC-3135")
    validate_pair("hx711", "ADC-HX711")

    mcu = hardware.get("mcu")
    if not isinstance(mcu, dict):
        errors.append("hardware.mcu must be an object")
    else:
        if mcu.get("item_id") != "MCU-ESP32S3":
            errors.append("hardware.mcu.item_id must be MCU-ESP32S3")
        source_kind = mcu.get("source_kind")
        active = mcu.get("active_hardware_id")
        if source_kind == "NOT_USED":
            if active not in ("", None):
                errors.append("hardware.mcu active ID must be empty when NOT_USED")
        elif source_kind == "RECEIVED_ORDER":
            if not _nonempty(active):
                errors.append("received MCU requires active_hardware_id")
            else:
                selected_ids.append(active)
            if checkout_rows.get("MCU-ESP32S3", {}).get("resolution") != "ORDER":
                errors.append("received MCU requires checkout ORDER resolution")
            if receiving is None:
                errors.append("received MCU requires receiving evidence")
            else:
                role_map = _received_role_map(receiving, "MCU-ESP32S3")
                if role_map.get(active) != "PILOT_ACTIVE_CANDIDATE":
                    errors.append(
                        "MCU active ID is not the received PILOT_ACTIVE_CANDIDATE"
                    )
        elif source_kind in {"USE_OWNED_EXACT", "USE_OWNED_EQUIVALENT"}:
            if not _nonempty(active):
                errors.append("owned MCU requires active_hardware_id")
            else:
                selected_ids.append(active)
            resolution = checkout_rows.get("MCU-ESP32S3", {}).get("resolution")
            if resolution != source_kind:
                errors.append("MCU source_kind must match checkout resolution")
            inv = inventory_rows.get("MCU-ESP32S3", {})
            if not isinstance(inv.get("qty_owned_verified"), int) or inv.get(
                "qty_owned_verified", 0
            ) < 1:
                errors.append("owned MCU requires verified quantity >=1")
        else:
            errors.append("unsupported hardware.mcu.source_kind")

    if len(selected_ids) != len(set(selected_ids)):
        errors.append("stable hardware IDs must be globally unique")

    source_kinds = {
        hardware.get("load_cell", {}).get("source_kind"),
        hardware.get("hx711", {}).get("source_kind"),
    }
    if "RECEIVED_ORDER" in source_kinds and receiving is None:
        errors.append("received pilot hardware requires receiving evidence")

    exact_verified = not any(
        error.startswith("LC-3135:")
        or error.startswith("ADC-HX711:")
        or "checkout authority" in error
        or "inventory" in error
        or "receiving" in error
        for error in errors
    )
    untouched_spares = (
        _nonempty(hardware.get("load_cell", {}).get("spare_hardware_id"))
        and _nonempty(hardware.get("hx711", {}).get("spare_hardware_id"))
        and hardware.get("load_cell", {}).get("spare_hardware_id")
        != hardware.get("load_cell", {}).get("active_hardware_id")
        and hardware.get("hx711", {}).get("spare_hardware_id")
        != hardware.get("hx711", {}).get("active_hardware_id")
        and len(selected_ids) == len(set(selected_ids))
    )

    report = {
        "schema_version": 1,
        "authority": "x1_fit_pilot_hardware_selection",
        "valid": not errors,
        "errors": errors,
        "selection_id": selection.get("selection_id"),
        "selection_record_sha256": _digest(selection),
        "checkout_id": checkout.get("checkout_id"),
        "checkout_authority_fingerprint_sha256": checkout_authority.get(
            "authority_fingerprint_sha256"
        ),
        "inventory_record_sha256": _digest(inventory),
        "receiving_id": receiving.get("receiving_id") if receiving is not None else None,
        "receiving_authority_fingerprint_sha256": (
            receiving_authority.get("authority_fingerprint_sha256")
            if receiving_authority is not None
            else None
        ),
        "hardware": hardware,
        "exact_evidence_hardware_verified": exact_verified and not errors,
        "untouched_spares_preserved": untouched_spares and not errors,
        "physical_qualification_authority": False,
        "four_zone_duplication_authorized": False,
        "fabrication_authority": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
        "interpretation_boundary": (
            "A valid selection report proves only that the chosen Issue #4 active "
            "load-cell/HX711 path and untouched spares descend from accepted Cart A "
            "checkout/receiving or exact-unused owned-stock evidence. It does not "
            "qualify sensor performance or authorize four-zone duplication."
        ),
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("selection", type=Path)
    p.add_argument("--inventory", type=Path, required=True)
    p.add_argument("--checkout", type=Path, required=True)
    p.add_argument("--checkout-authority", type=Path, required=True)
    p.add_argument("--receiving", type=Path)
    p.add_argument("--receiving-authority", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    checkout = json.loads(args.checkout.read_text(encoding="utf-8"))
    checkout_authority = json.loads(
        args.checkout_authority.read_text(encoding="utf-8")
    )
    receiving = (
        json.loads(args.receiving.read_text(encoding="utf-8"))
        if args.receiving is not None
        else None
    )
    receiving_authority = (
        json.loads(args.receiving_authority.read_text(encoding="utf-8"))
        if args.receiving_authority is not None
        else None
    )
    report = validate(
        selection,
        inventory,
        checkout,
        checkout_authority,
        receiving=receiving,
        receiving_authority=receiving_authority,
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["valid"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
