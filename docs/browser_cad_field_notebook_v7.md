# CAD Twin v7: on-page field notebook and structured millimeter readings

**Status:** draft PR #114. This is browser-only, locally held operator evidence, never structural model alignment, mechanical approval, licensed CAD import or checkout qualification.

## Why v7

The v5 checklist established 20 revision-specific evidence tasks and seven physical interface checks. v6 established manufacturer source navigation and pinned-file receipts. A JSON-only workflow could not capture a practical measuring session, nor distinguish a real dimensional value from narrative uncertainty. v7 adds a native field notebook under **Parts Picker → CAD asset laboratory → Measurement campaign**.

For each selected Tangent 105 mm Dad Bod or 85 mm Caguama complete research kit, choose **Record / edit field evidence** from one of the 20 tasks or use the native task selector. You can enter:

- Exact task ID and **required task method**, which comes from the immutable requirements catalog, not user-submitted text.
- What revision you actually observed (unverified), the collection date, HTTPS evidence reference and a detailed note.
- For metric tasks: a **named scalar value in millimeters** or an **XYZ point in millimeters** with a named operator-local coordinate frame. Enter explicit measurement uncertainty in millimeters.
- Multiple distinct numeric features for a task, up to 16, when the revision, source URL, date, note and uncertainty are **identical**. Adding a different source requires a separate task report or merging the evidence externally before importing; the notebook never silently conflates provenance.
- For original CAD source tasks: an explicit SHA-256 of the source file. Entering a hash does not grant a model license, authenticate the manufacturer's authorship, qualify a physical revision, or register the GLB.
- Receiving, revision reconciliation and physical testing tasks as dated, unverified textual observations without fake metric measurements.

Changes are held in **memory for the current browser tab**. Save, replace or remove the selected task report. **Export complete field log JSON** to retain your notes; otherwise leaving/reloading the page loses the temporary notebook. **Import unreviewed observation JSON** (up to 64 KB) to restore exactly the same kit-scoped notes. For audit and engineering planning, **Export metrology gap report** still lists the seven physical interfaces requiring independent review, missing evidence and reported readings.

### Structured measurement contract (backward compatible)

The field JSON remains schema version 1 and scope `UNREVIEWED_CAD_FIELD_OBSERVATIONS`. The optional new field is `measurements_mm` on a `METRIC_MEASUREMENT` record:

```json
{
  "task_id": "deck-hole-centers",
  "method": "METRIC_MEASUREMENT",
  "part_revision": "REPORTED_PHYSICAL_LABEL_NOT_VERIFIED",
  "evidence_url": "https://example.org/replace-with-actual-measurement-evidence",
  "recorded_on": "2026-10-12",
  "uncertainty_mm": 0.12,
  "note": "DEMONSTRATION ONLY; this sample is not a measurement of a real Tangent deck.",
  "source_sha256": null,
  "measurements_mm": [
    {
      "feature_id": "front-left-hole",
      "kind": "SCALAR",
      "value_mm": 53.975,
      "frame_label": null
    },
    {
      "feature_id": "front-right-hole",
      "kind": "POINT_3D",
      "value_mm": [-5.25, 0, 12.4],
      "frame_label": "SYNTHETIC_ARBITRARY_OPERATOR_FRAME"
    }
  ]
}
```

These numbers are **synthetic examples**, not manufacturer holes or physical deck measurements. Do not reuse them as actual design coordinates.

- Scalar values must be finite between 0 and 10,000 mm.
- XYZ values must contain exactly three finite coordinates, each between -10,000 and +10,000 mm. The operator frame must be named. **A named operator frame does not establish a verified mounting datum or aligned assembly coordinate frame.**
- Feature IDs must be unique and bounded. The validator rejects duplicate entries, forged approval properties, other-unit claims, malformed values, fake or unqualified methods, and entries from a different kit.
- Legacy v1 records without `measurements_mm` continue to import. They are treated as narrative, unstructured field reports, not as numeric measurements. Editing a record without **Add reading** intentionally replaces that task's report, including any older readings.
- The 20 tasks, seven interface reviews, complete parent package and zero separately qualified order lines remain unchanged.

### Safety and validation

The application only displays reported values beside their corresponding task, marked **UNREVIEWED**. Report totals count typed feature readings separately from task submissions. Values are never used to scale, rotate or translate 3D meshes; never change the synthetic motion model, mating datums, safety reviews or the current shopping decision. No physical fit/clearance or revision assertions are promoted.

Regression tests include typed scalar/XYZ validation, append-with-provenance restrictions, legacy JSON import, tamper detection and per-kit isolation. Chromium exercises the actual form and JSON import/export/remove loop alongside existing source/CAD checks.

```bash
node --test tests/js/test_outdoor_cad_field_notebook.mjs
node tests/browser/parts_picker_smoke.mjs
```

## Recommended next milestone: independent-review evidence layer

After authentic samples and source data exist, create separate reviewer-signed measurement records, reference-frame calibrations and correspondence maps **with provenance**, then bind those to the imported manufacturer CAD. Only then should the integrated visual assembly use metrologically grounded coordinates. Until then, the 3D complete board remains an illustrative procedural model.
