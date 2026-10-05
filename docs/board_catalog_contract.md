# Board Builder multi-vendor catalog contract

The Board Builder catalog is a provenance-aware mechanical knowledge layer, not a product scrape and not a checkout list.

Its job is to let genuinely different board architectures share one solver without turning missing information into compatibility claims.

## Data flow

```text
dated vendor / retailer source fact
        ↓
catalog/source_snapshots_YYYY-MM-DD.json
        ↓
normalized component interface
catalog/board_components.v1.json
        +
normalized visual / dimensional geometry
catalog/board_geometry.v1.json
        ↓
explicit compatibility rule
or conservative category-pair fallback
configurator/compatibility_rules.v1.json
        ↓
architecture hypotheses + Swap Lab
        ↓
generated visual / BOM / readiness state
```

Recommendation logic must not parse or infer directly from storefront prose.

## Layer 1: dated source snapshots

`catalog/source_snapshots_YYYY-MM-DD.json` records facts observed on a specific date.

A source record may contain:

- seller and source kind;
- canonical source URL;
- dimensions and interface facts;
- compatibility lists published by a vendor;
- native-currency advertised price text;
- availability notes.

The source snapshot is evidence for a catalog reference. It is not a purchase authorization, stock guarantee, delivered-price quote, or physical qualification.

A source fact should remain as close as practical to the vendor's published meaning. If a source publishes axle-end width but not wheel-center width, the source layer stores axle-end width. A visual proxy derived from another dimension belongs in the geometry layer and must be marked as assumed.

## Layer 2: normalized component interfaces

`catalog/board_components.v1.json` converts source facts into stable component IDs and interface fields.

Examples include:

- deck family and nominal envelope;
- steering family;
- truck width and axle diameter/type;
- hub family and bearing/axle options;
- wheel class and published diameter/width;
- brake family and required wheel/truck features;
- drive type, ratios and published truck/hub compatibility;
- motor shaft class.

Every catalog component also carries:

- `evidence_state`;
- `procurement_state`;
- source provenance;
- optional USD price only when the repository has a real USD snapshot;
- a hold reason where appropriate.

Native-currency price strings are retained as source metadata. They are not silently converted into USD. A future live-price service may perform an explicit dated FX conversion, but that conversion must remain separate from interface compatibility and physical authority.

## Layer 3: normalized geometry

`catalog/board_geometry.v1.json` is the shared visual and dimensional registry consumed by the Builder and the 3D twin.

It currently normalizes:

- MBS Comp 95, Pro Warren III and Agent envelopes;
- TRAMPA Short 9/69 and HS11 9/69 envelopes;
- MBS brake-first, drive-clearance and coexistence topology branches;
- TRAMPA VERTIGO and INFINITY HS11 truck families;
- Apex Air parallel-kingpin geometry.

A geometry record may include `visual_geometry_state: ASSUMED` when a visual comparison needs a proxy that is not published as the exact desired dimension. Those values are visualization-only and may never be used as fabrication dimensions.

## Compatibility is explicit or unknown

`configurator/compatibility_rules.v1.json` has two mechanisms.

### Explicit pair rules

Use an explicit rule when a published source or existing project authority supports the pair.

Examples in the current tranche include:

- TRAMPA Short deck + VERTIGO spring truck;
- TRAMPA INFINITY HS11 hanger + Magura HS11 brake;
- TRAMPA Superstar hub family + Boardnamics M1-AT;
- Apex Air + Boardnamics M1-AT.

`REFERENCE_COMPATIBLE` means the relationship is documented strongly enough for design comparison. It does not mean the complete board is physically qualified.

### Category-pair defaults

Critical mechanical pairs fail closed when no explicit rule exists.

Current default-unknown interfaces include:

- deck ↔ truck;
- truck ↔ wheel;
- truck ↔ brake;
- wheel ↔ brake;
- truck ↔ drive;
- wheel ↔ drive;
- hub ↔ drive.

This is the core anti-hallucination rule for catalog growth. Adding a new vendor or part can never make an unmodeled cross-vendor combination green merely because no incompatibility rule was written.

## Generated architecture families

The first multi-vendor tranche intentionally spans different mechanical concepts rather than cosmetic variants:

- MBS / Worcester brake-first, coexistence, range and SnowDeck studies;
- TRAMPA Short unpowered carve core;
- TRAMPA HS11 hydraulic freeride core;
- TRAMPA + Boardnamics brake/drive coexistence study;
- TRAMPA 9-inch open-belt-drive study;
- Apex Air parallel-kingpin + Boardnamics M1-AT study.

These are design hypotheses. They do not select a winner and they never promote procurement or ride authority.

The reference manual-carver and electric-trail profiles are regression-tested so their ranking order differs and each top-three result spans at least two vendor families.

## Visually meaningful substitution

A substitution is not considered visually complete merely because a label changes.

The current visual-state contract carries:

- deck length, width, wheelbase/tip metadata and shape family;
- truck width, wheel-center reference, steering family and axle metadata;
- wheel diameter, width and hub/wheel family;
- brake family;
- drive type;
- active system layers.

The deterministic preview renderer distinguishes at least:

- MBS-style versus TRAMPA composite deck silhouettes;
- channel-spring versus parallel-kingpin truck glyphs;
- MBS versus TRAMPA wheel/hub families;
- mechanical versus TRAMPA/Magura hydraulic brake cues;
- gear-drive versus open-belt-drive cues;
- 8-inch versus 9-inch pneumatic proportions.

The 3D twin accepts the same generic deck/topology/wheel IDs. External families without generated CAD stay procedural. Missing CAD is never replaced by a fake precision model.

## Pricing boundary

The Builder's USD total is always a **known-price subtotal**.

If a sourced component only has a native-currency vendor price:

- the native source text remains visible;
- the USD subtotal excludes it;
- the candidate reports an unpriced/source-native item;
- no implicit FX conversion occurs.

Shipping, tax, duties and stock remain outside the static catalog.

## Freshness and audit

Run:

```bash
python tools/audit_board_catalog.py
```

The audit reports:

- snapshot age;
- stale component-source dates;
- orphaned snapshot references;
- source URL mismatches;
- silent native-currency/price conversion errors;
- power-category gating regressions;
- vendor/category coverage;
- deck-shape, steering, wheel, brake and drive-family breadth.

To fail closed on stale data:

```bash
python tools/audit_board_catalog.py \
  --as-of 2026-10-04 \
  --max-source-age-days 30 \
  --strict-freshness
```

The audit itself performs no web requests and grants no authority. Refreshing a source requires a deliberate new dated snapshot after the relevant pages have been checked.

## Adding a new component family

A new family should enter the platform in this order:

1. Record the dated source facts.
2. Add a stable catalog component ID.
3. Normalize only interfaces actually supported by the source.
4. Add visual geometry, marking any proxy values explicitly.
5. Add explicit compatibility rules for sourced pairs.
6. Allow unmodeled critical pairs to remain `UNKNOWN`.
7. Add Swap Lab options only after the interface record is coherent.
8. Add an architecture hypothesis only when it represents a genuinely distinct trade-space choice.
9. Add deterministic Python/browser tests.
10. Re-run catalog audit, Builder validation, engine parity, visual parity and the full repository suite.

A vendor URL, good fit score, catalog inclusion, or visual rendering never creates procurement, fabrication, charging, public-use, dog-accompanied, or powered-operation authority.
