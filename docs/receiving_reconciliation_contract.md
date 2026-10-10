# Build Passport v1.6: received-parts reconciliation and manufacturer references

**Scope:** UNVERIFIED_RECEIVING_RECONCILIATION. Source links, observations and review worklists remain non-authoritative. Do not order parts, assemble, charge or ride based on this output.

## What changes

The Build Passport now displays a compact **Receiving reconciliation** panel sourced from two separate inputs:

1. The existing exact-snapshot, user-entered Evidence Notebook. Receiving records include the date, marked revision and count entered by the user.
2. A new read-only index of **public official manufacturer reference pages**, reviewed on 2026-10-10. These are product-family documentation leads, not certified installation instructions for the selected or received revision.

Reconciliation is deterministic in JavaScript (`builder/receiving_reconciliation.mjs`) and Python (`configurator/receiving_reconciliation.py`). A cross-runtime fixture tests a manual and electric study, each with synthetic conflicting receiving notes.

## Evidence semantics

A single observed quantity answers only: “What count did the user report on that date?” It is not verified inventory, order quantity, needed assembly quantity or stock.

Multiple receiving records for the same component are **not summed**. If observed counts or marked revisions differ, `CONFLICTING_RECEIPT_HISTORY_REVIEW` makes the discrepancy visible. The most recently *recorded* value is displayed with its date but is not selected as an authoritative value.

An observed donor package **does not** confirm its enclosed trucks, wheels, bearings, bindings, fasteners, exact versions or counts. Donor inclusion and retrofit questions from the v1.5 source-bound audit remain unresolved. Receiving a part does not resolve any `UNKNOWN`/`MEASURE_FIRST` mechanical or electrical interface.

The existing replay-validated local evidence notebook is rebound to `study_identity_key` and each `variant_identity_key`. Stale snapshots and forged approval fields cannot be used to elevate review status. The combined user-controlled JSON export now includes the receiving discrepancy report. No upload service or real-time stock service has been added.

All `actual_assembly_quantity`, `actual_supplier_order_quantity`, `physical_revision_verified`, `received_inventory_verified` and `revision_matched_manufacturer_manual_verified` fields remain null/false as appropriate. `physical_qualification` is `NOT_QUALIFIED`; authority fields all false.

## Real source research, limited by revision uncertainty

Reviewed official public sources, all listed in `catalog/manufacturer_document_references.v1.json`:

- [MBS manuals index](https://www.mbs.com/manuals): links to the general mountainboard manual, F5/F5X binding reference, Matrix III turning chart and V5 brake manual.
- [MBS Comp 95 Silver Hex product specs](https://www.mbs.com/shop/p/comp-95-mountainboard-silver-hex): lists part number 10303 and deck/Matrix III truck/Rockstar II hub/T1 tire/F5 binding product families; *Brake Included? No* and *Assembly: Wheels Off*. This is a manufacturer **product specification reference**, not a contents receipt or assembly release.
- [MBS binding manual page](https://www.mbs.com/manuals/040) and [Matrix III adjustment page](https://www.mbs.com/manuals/020): official general family references. Actual revision and mounting applicability still unverified.
- [TRAMPA HS11 hanger hardware product reference](https://trampaboards.com/special-parts-to-assemble-the-hs11-brake-kit-to-the-trampa-hanger-p-35968.html): describes hardware categories, **not** an approved hydraulic brake installation guide.

These links have been researched as official public pages. The exact shipped hardware revisions, manufacturer document release applicability, source checksum, vendor package counts, fresh quotes and current stock have **not** been verified. Do not mistake “official page found” for “approved manual matched to component.”

To prevent source creep, `tools/validate_manufacturer_document_references.py` requires HTTPS, allows only recorded maker domains, checks catalog component IDs, roles and dates, and rejects any claim of exact-revision verification.

## Use

```bash
python tools/serve_board_platform.py
# open http://127.0.0.1:8000/builder/
# select a candidate, inspect Build Passport, record any factual receiving note
# open Receiving reconciliation and review pending questions
```

Only record a receipt for **parts actually received**. The feature works with zero receipts and shows the resulting missing-evidence checklist. Manufacturer reference links are available under the part without claiming exact installation applicability. A print of the passport opens the reconciliation section temporarily, then restores the user's disclosure state.

## Test contract

```bash
node --test tests/js/test_board_receiving_reconciliation.mjs
python -m pytest -q tests/test_board_receiving_reconciliation.py
python tools/compare_receiving_reconciliations.py
python tools/validate_manufacturer_document_references.py
```

Full CI runs those checks, the prior Build Passport/evidence/assembly-inclusion parity tests and all repository physical gating/CAD/firmware regressions.

## Next milestone

Resolve actual manufacturer part revision applicability and verified package units using independent source evidence, photograph the exact received hardware during a real bench intake, and instrument measurement/geometry authority under the separately governed physical qualification workflow. Complete first-time desktop/tablet/mobile/print accessibility QA in issue #97. No actual parts are assumed purchased.
