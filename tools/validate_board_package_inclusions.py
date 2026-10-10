#!/usr/bin/env python3
"""Static source-catalog integrity check for non-authoritative inclusion mappings."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    catalog = json.loads((ROOT / "catalog/board_components.v1.json").read_text())
    registry = json.loads((ROOT / "catalog/board_package_inclusions.v1.json").read_text())
    assert registry["schema_version"] == 1
    assert registry["scope"] == "CATALOG_INCLUSION_HYPOTHESES_NOT_PACKAGE_CERTIFICATION"
    assert registry["authority"] and not any(registry["authority"].values())
    ids = {c["id"]: c for c in catalog["components"]}
    seen = set()
    for pkg in registry["packages"]:
        package_id = pkg["component_id"]
        assert package_id not in seen, f"Duplicate package mapping: {package_id}"
        seen.add(package_id)
        donor = ids[package_id]
        assert donor["includes"], f"No included-token contract for {package_id}"
        assert pkg["catalog_snapshot_id"] == donor["source"]["snapshot_id"], (
            "Supplier source snapshot changed; re-review the registry: " + package_id
        )
        assert pkg["catalog_sku_text"] == donor.get("sku"), (
            "SKU/variant reference changed; re-review package: " + package_id
        )
        included = {x["token"]: x for x in pkg["inclusions"]}
        assert set(included) == set(donor["includes"]), (
            "Missing/stale inclusion reference token for package " + package_id
        )
        for token, entry in included.items():
            assert entry["review_question"].strip()
            assert len(entry["possible_catalog_reference_ids"]) == len(set(entry["possible_catalog_reference_ids"]))
            for possible_id in entry["possible_catalog_reference_ids"]:
                assert possible_id in ids, f"Unknown catalog reference {possible_id} for included {token}"
                assert possible_id != package_id, f"Bundle cannot be its own included reference: {package_id}"
        for warning in pkg["retrofit_warnings"]:
            assert warning["when_component_id"] in ids
            assert warning["included_token"] in included
            assert warning["question"].strip()
    print(json.dumps({
        "valid": True, "reviewed_reference_packages": len(seen),
        "catalog_part_count": len(ids),
        "meaning": "Catalog reference mappings only; exact order quantities and physical compatibility remain unqualified",
        "authority": registry["authority"],
    }, indent=2))


if __name__ == "__main__":
    main()
