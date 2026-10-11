# CAD geometry staging: source-first browser twin, v1

**Status:** implemented on draft PR #114, stacked on #110–#113; preview-only. No new maker geometry or validated physical mating is claimed. The complete Loaded Tangent remains one parent maker package with seven **source-listed categories**, not seven purchase lines. Seller Paris V2 versus Paris V3 truck revision discrepancy, inventory receipt, mounting datums and mechanical qualification remain unresolved.

## What the browser can do now

1. Default to the integrated, seven-category, 0% separated board and the existing SVG fallback. Orbit, select, explode, export and switch the 85/105 mm source identities without changing checkout state.
2. Open **CAD asset laboratory** beneath the board to see exactly which roles have registered file-backed geometry, and export a machine-readable coverage report. The initial honest result is **0 of 7 file-backed categories**, **0 qualified datums**, **clearance NOT EVALUATED**, and **0 extra orders**.
3. Inspect a self-contained **local GLB v2** in an *isolated*, orbitable viewport. The selected category is displayed as the inspection label, but the model **never replaces an assembled part**, even if the file visually resembles the part. There is no invented scale, alignment or part-fit claim.
4. Reject malformed, remotely dependent or over-budget GLB inputs before invoking the optional Three.js loader. If WebGL or dependencies fail, the existing integrated 2D view remains usable.
5. Stage an exact revision candidate locally by SHA-256 and record the dated source, file rights and revision in `catalog/outdoor_cad_asset_registry.v1.json`. The candidate remains unaligned, unverified and unapproved.

## Staging your first manufacturer or independently measured CAD file

A manufacturer STEP requires an **explicit offline conversion** into a *binary GLB* (for example, via a CAD application or a headless FreeCAD/CadQuery conversion pipeline). Record the source revision, part number, source URL, license or permission, and coordinate units. Do not assume a model downloaded from a third-party library has an authentic manufacturer revision or licensed redistribution. Compare source values with a physical received sample before claiming measured accuracy.

An example for a locally held, permission-cleared GLB, using the exact selected parent variant ID from the catalog:

```bash
node tools/stage_cad_asset.mjs \
  --file /path/to/permission-cleared-deck.glb \
  --kit-variant-id REPLACE_WITH_EXACT_CATALOG_VARIANT_ID \
  --role deck \
  --part-number deck-revision-code \
  --revision revision-code \
  --source-url https://example.com/original-evidence-page \
  --license explicit-licensed-reuse \
  --origin MANUFACTURER_PUBLISHED \
  --evidence-date 2026-10-11
```

The staging utility reads the local GLB, performs structural preflight and digest verification, copies the file to `assets/cad/<sha256>.glb` and updates the JSON registry. It does not upload private files, transform the geometry or claim that the metadata provided by the operator was audited. Review the generated JSON and binary size in Git before committing. Do not stage third-party files without legal redistribution rights. SHA-256 pins the bytes; it is **not proof of their maker, dimensional accuracy or right to publish**.

The registry deliberately rejects untrusted external URLs as executable model sources, unpinned GLB filenames, duplicate roles for one kit revision, claims of verified mounting datums, metric assembly transforms, qualified clearances, extra child order lines or release permissions.

## Geometry data maturity ladder

| Stage | Viewer behavior | Allowed conclusions |
| --- | --- | --- |
| Procedural source-named reference | Seven assembled/exploded category proxies | Diagram only |
| File-backed candidate, dated and hashed | Standalone GLB inspection; default board unchanged | A byte-for-byte identifiable candidate exists |
| Independently measured and inspected physical revision | Separate measured geometry and datum capture *in a future schema* | Dimensional comparison, subject to error budget |
| Fully reconciled multi-part datum graph | Future metric-coordinate assembly and conservative contact candidates | Geometry-specific interference hypotheses, not product release |
| Physical test and appropriate engineering assessment | Independent evidence and signoff | Case-by-case release decision, never from browser alone |

**Do not** calculate clearances from the current `ARBITRARY_VISUAL_UNITS` model or treat spatial overlap of symbols as interference. Before enabling physical collision testing, each participating shape must share a traceable metric coordinate system with verified mating features, tolerances, axle/hanger/fastener revisions and independent source evidence. Use a conservative signed-distance or mesh collision library with broad-phase acceleration, tolerance envelopes, and explicit unknown/unmeasured regions. A non-overlap on a rendering is not a safety certificate.

## Release checks and unresolved work

- Node: `node --test tests/js/test_outdoor_cad_assets.mjs tests/js/test_outdoor_complete_kit_cad_schema.mjs`
- Structural parser: malformed GLB, external URI, header corruption and safety-lock mutation fixtures.
- Chromium: CAD laboratory renders seven categories, export reports no datums, corrupt file remains isolated.
- Still required: a **legally licensed** source artifact for a specific revision, GLB conversion fidelity versus STEP, physical datums and tolerance metrology, received contents and V2/V3 seller conflict resolution, actual-device touch/keyboard/screen-reader and screenshot signoff, and human release review.

No merge to `main`, fabrication, electric motor/battery use, ski retention approval or product ordering is authorized by this tranche.
