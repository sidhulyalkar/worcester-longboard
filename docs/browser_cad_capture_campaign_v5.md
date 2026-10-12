# CAD Twin v5: field metrology campaign and source-to-interface evidence

**Status:** Unqualified source and measurement collection on stacked draft PR #114. No independently qualified physical mates, 3D OEM assets, clearance certificates, receipt of actual purchased hardware, fabrication/charging/powered use or additional purchasing authority.

## Product behavior

The collapsed **CAD asset laboratory → Measurement campaign** turns the seven-category Tangent complete-board research reference into a traceable collection worklist. The current 105 mm Dad Bod and 85 mm Caguama variants produce **separate, exact-variant-scoped** packets and known maker source links. All 20 tasks and seven mechanical interface evaluations begin unresolved.

Seven part roles:
- Deck: source-authorized 3D geometry, hole centers, deck mating surfaces, loaded deflection.
- Zee Brackets: CAD revision, deck/truck hole pattern and each bracket instance's fiducial pose.
- Trucks: Paris V2/V3 seller-package mismatch, source model, actual baseplate holes and steering articulation.
- Wheels: profile, hub/core, bearing seat, offsets and measured 85/105 mm variant identity.
- Bearings: actual JEHU V2 dimensions, spacers, revision and counted pieces.
- Deck hardware: received count, countersink/thread/stack measurements.
- Truck hardware: received count, baseplate bolt and tool/fastener interference.

Seven review edges keep separate requirements for deck-to-bracket, bracket-to-truck, truck-to-wheel, loaded wheel-bite, deck fastener stack, truck fastener stack and loaded ride-height stack. These are *interface evaluation tasks*, **not completed CAD mates or collision tests**.

## Evidence collection workflow

1. Select the exact maker kit variant in the Parts Picker and open **Measurement campaign**.
2. Expand a role to see its acquisition and measurement tasks and relevant linked manufacturer publications. These are research sources, not approval to republish proprietary geometry.
3. **Export field evidence template**; it contains `schema_version:1`, `scope:"UNREVIEWED_CAD_FIELD_OBSERVATIONS"`, the selected `kit_variant_id`, `units:"mm"`, all three authority flags false and `records:[]`.
4. For a task, add a record containing **exactly** these keys:
   ```json
   {
     "task_id": "truck-seller-revision",
     "method": "REVISION_RECONCILIATION",
     "part_revision": "ACTUAL_LABEL_AS_RECORDED_BUT_NOT_VERIFIED",
     "evidence_url": "https://example.com/path/to/your-controlled-field-notes",
     "recorded_on": "2026-10-12",
     "uncertainty_mm": null,
     "note": "Operator recorded packaging and photographed baseplate markings; independent verification still required.",
     "source_sha256": null
   }
   ```
5. **Import observation JSON** (64 KB maximum). The app checks all known task IDs, unique records, exact maker variant, the **specific method required by that task**, dated HTTPS evidence, and no forged approvals. A `METRIC_MEASUREMENT` requires a stated positive `uncertainty_mm` and a `CAD_SOURCE` claim requires a 64-hex-character SHA-256 digest; other methods may use `null` where appropriate. No sensitive photos or files are uploaded to a server by the app; the chosen local JSON is evaluated in the browser. Source links remain supplied references only.
6. **Export metrology gap report** to preserve 20 per-task statuses, original manufacturer source links, reported items and seven remaining independent interface reviews.

The displayed status `FIELD_REPORTED_NOT_INDEPENDENTLY_VERIFIED` means the operator **submitted a claim**, not that the geometry, measurement method, photo, instrument calibration, supplier revision, or real-world part is verified. Neither a submitted source URL nor a hash authorizes fabrication. On kit switch, stale observations are cleared. A malformed, cross-kit or unsafe packet is rejected, and prior unreviewed evidence is discarded, without altering CAD views or purchasing state.

## Practical measurement protocol for future hardware

- Preserve the complete kit purchase/receipt and take photographs of manufacturer markings and packaging to reconcile **Paris V2 versus V3**. Don't infer receiving counts from the source-listed seven part categories.
- For each part and instance, establish a repeatable right-handed axis frame; capture at least four independent, non-collinear fiducials and their physical or digital source-frame correspondences. Explicitly document metric units and coordinate-convention changes.
- Use a calibrated instrument with stated uncertainty; record raw measurements and the source file's SHA-256 hash, revisions, capture date and operator notes. Repeat critical measurements and reconcile asymmetric bracket/wheel geometry rather than assuming mirrored parts.
- Record bolt stackups (engagement/countersink/head protrusion), bearing-seat/axle interface, truck baseplate contacts, wheel center/offset and bushing/kingpin articulation. These are the critical interfaces that a pretty GLB alone cannot resolve.
- For actual wheel bite and steering safety, perform independent engineering checks on the received revision, including dynamic movement, loaded deck flex and tolerances. AABB proxy overlap is only a conservative research hint, not confirmation of contact; sampled non-overlap does not establish continuous safe clearance.
- Source STEP/GLB must be obtained with explicit reuse rights and processed through the existing unit-safe STEP-to-glTF conversion receipt and content-addressed registry; generated research proxies should never be relabeled OEM CAD.

## Verification and remaining gates

The seven source-listed category counts, maker-supplied dimensional evidence, candidate metric scenes and independent GLB inspector remain unchanged. This tranche deliberately does **not** add separate child purchase lines.

Relevant checks:
```bash
node --test tests/js/test_outdoor_cad_capture_campaign.mjs
node tests/browser/parts_picker_smoke.mjs
```

Only after a received-part source survey, verified exact seller revision, known mounting datums, actual geometry and specialist fit review should the project add a separate independently reviewed metric assembly authority tier. Manual real-device accessibility, screenshot/touch review and the stacked PRs' release gates are separate from automated CI.

Original maker reference pages: [Loaded Tangent](https://www.loadedboards.com/products/tangent-longboard-skateboard), [Loaded Zee Bracket](https://www.loadedboards.com/products/zee-bracket), [Paris 150 mm 50°](https://www.paristruckco.com/products/v3-150mm-50-polished), [Orangatang wheels](https://www.orangatangwheels.com/collections/race-carving).
