#!/usr/bin/env python3
"""Initialize a Worcester X1 Cart A receiving record from completed checkout evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "hardware/x1_cart_a_receiving_template.json"


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _valid_authority(report: dict) -> bool:
    actual = report.get("authority_fingerprint_sha256")
    if not isinstance(actual, str) or not actual:
        return False
    unsigned = dict(report)
    unsigned.pop("authority_fingerprint_sha256", None)
    return actual == _digest(unsigned)


def initialize(
    output_path: Path,
    checkout_path: Path,
    checkout_authority_path: Path,
    receiving_id: str,
) -> dict:
    checkout = json.loads(checkout_path.read_text(encoding="utf-8"))
    authority = json.loads(checkout_authority_path.read_text(encoding="utf-8"))

    if authority.get("authority") != "x1_cart_a_checkout_evidence":
        raise ValueError("checkout authority must be x1_cart_a_checkout_evidence")
    if not _valid_authority(authority):
        raise ValueError("checkout authority fingerprint is invalid")
    if authority.get("valid") is not True or authority.get("order_record_complete") is not True:
        raise ValueError("checkout authority must be valid and order-record complete")
    if authority.get("checkout_within_existing_buy_now_authority") is not True:
        raise ValueError("checkout authority must remain within existing BUY_NOW authority")
    for key in (
        "procurement_authority",
        "physical_qualification_authority",
        "fabrication_authority",
        "powered_operation_authorized",
        "public_operation_authorized",
        "dog_accompanied_operation_authorized",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"checkout authority boundary violated: {key}")
    if authority.get("checkout_record_sha256") != _digest(checkout):
        raise ValueError("checkout authority does not match supplied checkout record")
    if authority.get("checkout_id") != checkout.get("checkout_id"):
        raise ValueError("checkout authority checkout_id mismatch")

    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    rows = []
    for item in checkout.get("items", []):
        if item.get("resolution") != "ORDER":
            continue
        expected_qty = int(item.get("ordered_qty", 0))
        rows.append(
            {
                "id": item["id"],
                "expected_qty": expected_qty,
                "qty_received": 0,
                "seller": item.get("seller", ""),
                "expected_sku": item.get("sku", ""),
                "package_sku_observed": "",
                "source_snapshot_required": item.get("source_snapshot_required") is True,
                "substitution_observed": False,
                "visible_damage_observed": False,
                "hardware_units": [],
                "missing_or_backorder_note": "",
                "notes": "",
            }
        )

    template.update(
        {
            "receiving_id": receiving_id,
            "checkout_authority_fingerprint_sha256": authority[
                "authority_fingerprint_sha256"
            ],
            "checkout_id": checkout["checkout_id"],
            "items": rows,
        }
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite receiving record: {output_path}")
    output_path.write_text(
        json.dumps(template, indent=2) + "\n",
        encoding="utf-8",
    )
    return template


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--checkout-authority", type=Path, required=True)
    parser.add_argument("--receiving-id", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            initialize(
                args.output,
                args.checkout,
                args.checkout_authority,
                args.receiving_id,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
