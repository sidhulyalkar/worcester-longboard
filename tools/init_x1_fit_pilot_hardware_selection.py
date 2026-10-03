#!/usr/bin/env python3
"""Initialize Issue #59 pilot hardware selection from Cart A evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "hardware/x1_fit_pilot_hardware_selection_template.json"


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _valid_authority(report: dict, authority: str) -> bool:
    if report.get("authority") != authority:
        return False
    actual = report.get("authority_fingerprint_sha256")
    if not isinstance(actual, str) or not actual:
        return False
    unsigned = dict(report)
    unsigned.pop("authority_fingerprint_sha256", None)
    return actual == _digest(unsigned)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _checkout_rows(checkout: dict) -> dict[str, dict]:
    return {
        row["id"]: row
        for row in checkout.get("items", [])
        if isinstance(row, dict) and _nonempty(row.get("id"))
    }


def _inventory_rows(inventory: dict) -> dict[str, dict]:
    return {
        row["id"]: row
        for row in inventory.get("items", [])
        if isinstance(row, dict) and _nonempty(row.get("id"))
    }


def _received_units(receiving: dict, item_id: str) -> list[dict]:
    for row in receiving.get("items", []):
        if isinstance(row, dict) and row.get("id") == item_id:
            units = row.get("hardware_units", [])
            return units if isinstance(units, list) else []
    return []


def _pick_received(units: list[dict], role: str) -> str:
    matches = [
        unit.get("hardware_id")
        for unit in units
        if isinstance(unit, dict)
        and unit.get("role") == role
        and _nonempty(unit.get("hardware_id"))
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one received unit with role {role}")
    return matches[0]


def initialize(
    output_path: Path,
    inventory_path: Path,
    checkout_path: Path,
    checkout_authority_path: Path,
    selection_id: str,
    selected_at_utc: str,
    *,
    receiving_path: Path | None = None,
    receiving_authority_path: Path | None = None,
    owned_load_cell_active_id: str | None = None,
    owned_load_cell_spare_id: str | None = None,
    owned_hx711_active_id: str | None = None,
    owned_hx711_spare_id: str | None = None,
    mcu_id: str | None = None,
) -> dict:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    checkout = json.loads(checkout_path.read_text(encoding="utf-8"))
    checkout_authority = json.loads(checkout_authority_path.read_text(encoding="utf-8"))

    if not _valid_authority(checkout_authority, "x1_cart_a_checkout_evidence"):
        raise ValueError("checkout authority is missing, wrong type, or fingerprint-invalid")
    if checkout_authority.get("valid") is not True or checkout_authority.get("checkout_ready") is not True:
        raise ValueError("checkout authority must be valid and checkout_ready")
    if checkout_authority.get("checkout_record_sha256") != _digest(checkout):
        raise ValueError("checkout authority does not match supplied checkout")
    if checkout_authority.get("inventory_record_sha256") != _digest(inventory):
        raise ValueError("checkout authority does not match supplied inventory")
    for key in (
        "procurement_authority",
        "physical_qualification_authority",
        "fabrication_authority",
        "powered_operation_authorized",
        "public_operation_authorized",
        "dog_accompanied_operation_authorized",
    ):
        if checkout_authority.get(key) is not False:
            raise ValueError(f"checkout authority boundary violated: {key}")

    receiving = None
    receiving_authority = None
    if receiving_path is not None or receiving_authority_path is not None:
        if receiving_path is None or receiving_authority_path is None:
            raise ValueError("receiving record and receiving authority must be supplied together")
        receiving = json.loads(receiving_path.read_text(encoding="utf-8"))
        receiving_authority = json.loads(
            receiving_authority_path.read_text(encoding="utf-8")
        )
        if not _valid_authority(
            receiving_authority, "x1_cart_a_receiving_evidence"
        ):
            raise ValueError("receiving authority is missing, wrong type, or fingerprint-invalid")
        if receiving_authority.get("valid") is not True or receiving_authority.get("receiving_complete") is not True:
            raise ValueError("receiving authority must be valid and receiving_complete")
        if receiving_authority.get("receiving_record_sha256") != _digest(receiving):
            raise ValueError("receiving authority does not match supplied receiving record")
        if receiving_authority.get("checkout_authority_fingerprint_sha256") != checkout_authority.get(
            "authority_fingerprint_sha256"
        ):
            raise ValueError("receiving authority does not descend from supplied checkout")
        if receiving_authority.get("checkout_id") != checkout.get("checkout_id"):
            raise ValueError("receiving authority checkout_id mismatch")
        for key in (
            "physical_qualification_authority",
            "fabrication_authority",
            "powered_operation_authorized",
            "public_operation_authorized",
            "dog_accompanied_operation_authorized",
        ):
            if receiving_authority.get(key) is not False:
                raise ValueError(f"receiving authority boundary violated: {key}")

    checkout_rows = _checkout_rows(checkout)
    inventory_rows = _inventory_rows(inventory)
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))

    def select_pair(
        item_id: str,
        active_owned_id: str | None,
        spare_owned_id: str | None,
    ) -> dict:
        row = checkout_rows.get(item_id)
        if row is None:
            raise ValueError(f"checkout missing required pilot item {item_id}")
        resolution = row.get("resolution")
        if resolution == "ORDER":
            if receiving is None or receiving_authority is None:
                raise ValueError(f"{item_id}: ORDER resolution requires complete receiving evidence")
            units = _received_units(receiving, item_id)
            return {
                "item_id": item_id,
                "source_kind": "RECEIVED_ORDER",
                "active_hardware_id": _pick_received(units, "PILOT_ACTIVE_CANDIDATE"),
                "spare_hardware_id": _pick_received(units, "SPARE_UNTOUCHED"),
            }
        if resolution == "USE_OWNED_EXACT":
            inv = inventory_rows.get(item_id, {})
            if (
                inv.get("status") != "OWNED_EXACT_UNUSED"
                or inv.get("exact_part_match") is not True
                or inv.get("unused_or_known_history") is not True
                or int(inv.get("qty_owned_verified", 0)) < 2
            ):
                raise ValueError(
                    f"{item_id}: owned pilot evidence requires >=2 exact unused/known-history units"
                )
            if not _nonempty(active_owned_id) or not _nonempty(spare_owned_id):
                raise ValueError(
                    f"{item_id}: owned exact path requires explicit active and spare hardware IDs"
                )
            if active_owned_id == spare_owned_id:
                raise ValueError(f"{item_id}: active and spare hardware IDs must differ")
            return {
                "item_id": item_id,
                "source_kind": "OWNED_EXACT_UNUSED",
                "active_hardware_id": active_owned_id,
                "spare_hardware_id": spare_owned_id,
            }
        raise ValueError(
            f"{item_id}: required pilot evidence must resolve to ORDER or USE_OWNED_EXACT, got {resolution!r}"
        )

    load_cell = select_pair(
        "LC-3135",
        owned_load_cell_active_id,
        owned_load_cell_spare_id,
    )
    hx711 = select_pair(
        "ADC-HX711",
        owned_hx711_active_id,
        owned_hx711_spare_id,
    )

    mcu = {
        "item_id": "MCU-ESP32S3",
        "source_kind": "NOT_USED",
        "active_hardware_id": "",
    }
    if _nonempty(mcu_id):
        mcu_row = checkout_rows.get("MCU-ESP32S3")
        if mcu_row is None:
            raise ValueError("MCU ID supplied but checkout has no MCU-ESP32S3 row")
        resolution = mcu_row.get("resolution")
        if resolution == "ORDER":
            if receiving is None:
                raise ValueError("ordered MCU requires complete receiving evidence")
            units = _received_units(receiving, "MCU-ESP32S3")
            received_id = _pick_received(units, "PILOT_ACTIVE_CANDIDATE")
            if received_id != mcu_id:
                raise ValueError("supplied MCU ID does not match received pilot candidate")
            source_kind = "RECEIVED_ORDER"
        elif resolution in {"USE_OWNED_EXACT", "USE_OWNED_EQUIVALENT"}:
            inv = inventory_rows.get("MCU-ESP32S3", {})
            if int(inv.get("qty_owned_verified", 0)) < 1:
                raise ValueError("owned MCU path requires verified owned quantity")
            source_kind = resolution
        else:
            raise ValueError(f"MCU cannot be selected from checkout resolution {resolution!r}")
        mcu = {
            "item_id": "MCU-ESP32S3",
            "source_kind": source_kind,
            "active_hardware_id": mcu_id,
        }

    selected_ids = [
        load_cell["active_hardware_id"],
        load_cell["spare_hardware_id"],
        hx711["active_hardware_id"],
        hx711["spare_hardware_id"],
    ]
    if _nonempty(mcu["active_hardware_id"]):
        selected_ids.append(mcu["active_hardware_id"])
    if len(selected_ids) != len(set(selected_ids)):
        raise ValueError("all selected stable hardware IDs must be globally unique")

    template.update(
        {
            "selection_id": selection_id,
            "selected_at_utc": selected_at_utc,
            "checkout_id": checkout.get("checkout_id", ""),
            "checkout_authority_fingerprint_sha256": checkout_authority.get(
                "authority_fingerprint_sha256", ""
            ),
            "inventory_record_sha256": _digest(inventory),
            "receiving_id": (
                receiving.get("receiving_id", "") if receiving is not None else ""
            ),
            "receiving_authority_fingerprint_sha256": (
                receiving_authority.get("authority_fingerprint_sha256", "")
                if receiving_authority is not None
                else ""
            ),
            "hardware": {
                "load_cell": load_cell,
                "hx711": hx711,
                "mcu": mcu,
            },
        }
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite hardware selection: {output_path}")
    output_path.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
    return template


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    p.add_argument("--inventory", type=Path, required=True)
    p.add_argument("--checkout", type=Path, required=True)
    p.add_argument("--checkout-authority", type=Path, required=True)
    p.add_argument("--selection-id", required=True)
    p.add_argument("--selected-at-utc", required=True)
    p.add_argument("--receiving", type=Path)
    p.add_argument("--receiving-authority", type=Path)
    p.add_argument("--owned-load-cell-active-id")
    p.add_argument("--owned-load-cell-spare-id")
    p.add_argument("--owned-hx711-active-id")
    p.add_argument("--owned-hx711-spare-id")
    p.add_argument("--mcu-id")
    args = p.parse_args()

    print(
        json.dumps(
            initialize(
                args.output,
                args.inventory,
                args.checkout,
                args.checkout_authority,
                args.selection_id,
                args.selected_at_utc,
                receiving_path=args.receiving,
                receiving_authority_path=args.receiving_authority,
                owned_load_cell_active_id=args.owned_load_cell_active_id,
                owned_load_cell_spare_id=args.owned_load_cell_spare_id,
                owned_hx711_active_id=args.owned_hx711_active_id,
                owned_hx711_spare_id=args.owned_hx711_spare_id,
                mcu_id=args.mcu_id,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
