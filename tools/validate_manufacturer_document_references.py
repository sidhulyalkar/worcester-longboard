#!/usr/bin/env python3
"""Fail closed if manufacturer reference links or scopes become unreviewed."""
from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import urlsplit
from datetime import date

ROOT=Path(__file__).resolve().parents[1]
ACCEPTED_ROLES={
 "OFFICIAL_MANUAL_INDEX",
 "OFFICIAL_GENERAL_ADJUSTMENT_REFERENCE",
 "OFFICIAL_GENERAL_BINDING_REFERENCE",
 "MANUFACTURER_PRODUCT_REFERENCE_NOT_MANUAL",
}
DOMAINS={"www.mbs.com","trampaboards.com"}

def main():
    catalog=json.loads((ROOT/"catalog/board_components.v1.json").read_text())
    docs=json.loads((ROOT/"catalog/manufacturer_document_references.v1.json").read_text())
    ids={c["id"] for c in catalog["components"]}
    assert docs["schema_version"]==1
    assert docs["scope"]=="PUBLIC_MANUFACTURER_REFERENCES_NOT_EXACT_VARIANT_INSTRUCTIONS"
    assert date.fromisoformat(docs["reviewed_as_of"]).isoformat()==docs["reviewed_as_of"]
    assert not any(docs["authority"].values())
    seen=set()
    for entry in docs["entries"]:
        assert entry["id"] not in seen
        seen.add(entry["id"])
        assert entry["manufacturer"] in ("MBS","TRAMPA")
        assert entry["document_role"] in ACCEPTED_ROLES
        assert entry["exact_revision_verified"] is False
        assert entry["title"].strip() and entry["scope_note"].strip()
        assert entry["component_ids"] and len(entry["component_ids"])==len(set(entry["component_ids"]))
        assert all(x in ids for x in entry["component_ids"])
        url=urlsplit(entry["url"])
        assert url.scheme=="https" and url.hostname in DOMAINS
        assert not url.username and not url.password
    print(json.dumps({"public_manufacturer_references":len(seen),
        "exact_revision_matched_manuals":0,"physical_authority":False,
        "reviewed_as_of":docs["reviewed_as_of"]},indent=2))

if __name__=="__main__":
    main()
