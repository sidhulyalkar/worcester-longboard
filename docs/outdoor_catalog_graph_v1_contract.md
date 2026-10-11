# Outdoor Catalog Graph v1: lossless mountainboard adapter

**Status, October 10, 2026:** experimental and read-only. This graph never authorizes orders, assembly, stock claims, mechanical fit, charging or operation. It does not yet ingest real snowboard, ski, surfboard, bicycle or camping products.

## Implemented core

Two deterministic adapters transform the existing 37-component mountainboard v1 catalog and its domain and inclusion registries into a generalized product graph:

- JavaScript: builder/outdoor_catalog_graph.mjs
- Python: configurator/outdoor_catalog_graph.py
- Source domain vocabulary: catalog/outdoor_equipment_domains.v0.json
- Source-bounded donor contents hypotheses: catalog/board_package_inclusions.v1.json

The graph returns separate records for:

| Entity | Meaning | Deliberately unknown |
|---|---|---|
| families | Provisional family per old component | Shared model-family equivalence |
| variants | Old component as source-aware provisional variant | Exact received SKU/revision, assembly fit |
| source_snapshots | Supplier/placeholder source IDs, URL, date, provenance | Live seller state or independent truth |
| supplier_offer_references | Dated vendor/retailer listing references | Quote, live stock, supplier packaging |
| engineering_claims | Raw legacy interface fields with source/variant binding | Actual measurement and physical fit |
| sellable_package_hypotheses | Donor included tokens and possible counterpart refs | Actual contents, variants or counts |
| source_holds | Components lacking qualifying dated supplier references | Any buyable listing |
| legacy_catalog_snapshot | Unmodified v1 input for round-trip replay | Inferring revised physical interfaces |

This design intentionally uses **one provisional product family for every legacy row**, not a guessed grouping by brand or label. A model-family SKU such as 12302 / 12300 family is not a confirmed individual product variant. No record claims a verified exact SKU, qualified part revision, complete kit or professional release.

## Engineering claims and supplier offers

Legacy interface fields are kept with raw values, suffix units and dated reference binding. These claims are **not automatically normalized into fit approvals**, tolerances or complete multi-component constraints.

Only dated, credential-free HTTPS vendor/retailer sources create historical supplier offer *references*. Unsourced placeholders, repository references and vendor reference mentions never become shopping listings. Old price.qty values are **reference pricing multipliers**, not seller order units or physical assembly quantities.

For every historical offer, the following remain unconfirmed: true supplier pack unit, assembly units per pack, live availability, current seller quote, manufacturing revision and checkout authorization.

Bundled donor equipment is recorded only as source-matched research hypotheses. Inclusions neither delete standalone BOM lines nor reduce prices automatically.

## Lossless v1 replay and safety tests

The graph stores the complete v1 catalog unchanged. The replay adapter checks complete family/variant/source record membership and a deterministic source identity binding that includes catalog ID, source URL/snapshot/date, seller and price reference values.

The source binding detects stale partial edits; it is **not a cryptographically signed manufacturer certificate**.

Cross-runtime validation (tools/compare_outdoor_catalog_graphs.py) checks:

1. Exact Python/JavaScript graph equality.
2. Exact legacy catalog replay.
3. Existing board design-space result equality when the engine is given the replayed catalog.
4. Build Passport equality for several unchanged architectures.
5. All graph qualification, current stock, orderable kit and authority statuses remain unverified/false.

Negative tests cover unknown categories, duplicate IDs, stale SKU, changed source snapshot, tampered price, source URLs with credentials, invalid source dates, donor inclusion revision mismatch and missing graph identity records.

Full GitHub Actions runs those tests alongside the existing CAD, firmware, physical qualification and mechanical authority regressions.

## Catalog Lab

Use the local server and visit http://127.0.0.1:8000/builder/catalog.html .

This new, read-only page is linked from the existing Board Builder header. It displays the nine planned outdoor equipment domains, clearly marks the single currently imported domain, and lets users search/filter the imported mountainboard catalog by text, role and source type.

Component cards show model references, SKU ambiguity, source dates, raw engineering attributes and donor inclusion uncertainties. Supplier links are provenance leads, not checkout links. Zero orderable kits are reported.

The interface uses semantic form controls, a live results status, keyboard-operable native disclosure sections, a responsive grid and a print fallback. A full manual responsive/keyboard/print visual review is still an open action under issue #97.

## Local reproducibility

    node --test tests/js/test_outdoor_catalog_graph.mjs
    python -m pytest -q tests/test_outdoor_catalog_graph.py
    python tools/compare_outdoor_catalog_graphs.py
    python tools/serve_board_platform.py

## Next execution: Issue #106

- Implement canonical multi-domain product-family, variant and sellable package contracts with reviewed original-source variant evidence.
- Pilot real snowboard mounting systems, binding discs and size-specific boot/binding matching with source-verified adapters. Unsupported and unknown cases remain held.
- Introduce snowboard-specific visual and preference scoring adapters, rather than exporting mountainboard carve/range traits.
- Add alpine ski fit, boot-sole/binding and professional mounting/release workflows only with independently sourced norms and qualified safety handoffs.
- Complete responsive/keyboard/print/browser usability review before launch.

This tranche establishes the graph and its migration correctness. It is **not yet** a fully populated multi-sport store or configurable ski/snowboard builder.
