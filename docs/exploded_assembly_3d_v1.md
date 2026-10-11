# Exploded Assembly Atlas v1.1: graph-driven 3D + fit intake

**Status:** interactive 3D _visual proxy_ and conservative cross-sport intake. **Not** measured CAD, a sport-specific complete configurator, a fit certification, a release setting, an order form, or a physical build permit.

## Use

```bash
python tools/serve_board_platform.py
# Open http://127.0.0.1:8000/builder/
```

1. Generate and inspect a mountainboard candidate, or choose a **concept** / **manufacturer reference study** under **Inside the build**.
2. Toggle **Orbitable 3D**. Orbit/zoom with mouse or touch, use the Perspective/Top/Side/Front camera presets, and change the existing separation slider.
3. Select a colored proxy to synchronize the selected assembly component, or select the same component via the keyboard-accessible **Assembly tree**. **2D diagram** keeps the deterministic SVG for accessibility, export, printing and browsers without WebGL/network access.
4. Expand **Personalize snowboard or ski fit research**. Record measured height/mass and **separate left/right foot lengths** in Mondo millimeters. Choose declared mounting families or ski sole interface norms, then review a conservative conflict/unknown worklist. Export the review separately from the source-bound graph if needed.

**Browser dependency:** 3D loads Three.js 0.180.0 on user action via the same esm.sh modules already used by the existing Digital Twin. No extra client install. If remote modules, WebGL or the GPU fail, users retain the 2D SVG, tree and exports. Test offline explicitly; 3D is not guaranteed to load offline.

## Architectural boundary

- `builder/assembly_graph.mjs` remains the **only** source of semantic part identities and manufacturer evidence; `configurator/assembly_graph.py` remains cross-runtime equivalent.
- `builder/exploded_scene_model.mjs` converts that **exact graph** into a deterministic, validated scene plan: arbitrary visual units, grouped offsets, stable BOM/component IDs. It rejects duplicate or unknown graph groups, spoofed physical qualification and any already-claimed verified part geometry.
- Selected mountainboard candidates now reuse their Board Builder visual envelope **ratios** for deck length, deck width and wheel diameter. These reference proportions can vary across designs, but original catalog reference values may include visual assumptions; they are not verified exact component geometry, clearances or mate coordinates.
- `builder/exploded_3d_viewer.mjs` is the optional browser rendering adapter. Meshes are **role-specific procedural approximations**, not measured dimensions; 3D picking is linked to the same semantic tree and evidence detail as SVG. The simulator must never read 3D placement as installation geometry.
- `builder/sport_fit_intake.mjs` reviews **user declarations**. Snowboard checks reuse existing `evaluateSnowboardMountReference`; ski checks reject explicit mismatches among declared boot-sole and binding-accepted standards. They do not infer manufacturer fit, DIN/release settings, boot retention, or compatible part SKUs. Asymmetric foot lengths explicitly trigger separate boot/retention review.
- All `authority` fields remain false. A maker-family reference match remains **REVIEW_REQUIRED**, not physical fit. Recorded Mondo measurements are not a boot-size recommendation.

## What would constitute genuinely dimensional 3D

Current coverage: **0 revision-bound measured component meshes** and **0 physically qualified mate/clearance relationships**. The only current dimensional registry contains *reference envelopes* and known visualization assumptions for specific mountainboard studies. Those cannot be promoted to exact mount-hole or assembly coordinates.

Before claiming dimensional accuracy, a future revision must establish for each scene part:

1. An **exact vendor model, size and revision**, distinct from family marketing labels and seller order unit, with dated source/inspection provenance.
2. Measured or published `mm` geometry in a named coordinate frame, qualified mating features and mounting-hole pattern, plus uncertainty and tolerance. No auto-inferred centerline offsets.
3. Match graph `component_id` and source fingerprint to the exact revision geometry. If a part changes, invalidate dependent placements and verification receipts.
4. Independently reviewed mate transforms, fastener/stack constraints, cable/steering/brake/wheel travel envelopes and collision/clearance checks. Missing data returns `UNKNOWN`, not a clean intersection.
5. Interactive comparison against an assembly-specific CAD/GLB asset using verified metadata, validation fixtures for swapped variants, and an explicit **visual-only** status independent of physical assembly/power/release gates.

Snowboard inputs must add maker-cited board lengths, insert pattern positions, binding model **size** and board/disc/hardware revision, actual boot model and size for each foot. Ski inputs must add exact ski length/waist/revision, boot sole length/norm, manufacturer binding model and accepted norms, brake model and technical mounting verification. Alpine binding mount, adjustment and release must be handled by a qualified ski technician.

## Tests and visual QA

```bash
node --test tests/js/test_board_exploded_3d.mjs tests/js/test_board_sport_fit_intake.mjs
node --check builder/exploded_3d_viewer.mjs
python -m pytest -q tests/test_board_builder_ui_contract.py
```

The CI suite adds model-evidence safety tests, negative cross-sport fit scenarios and JS parsing. **Manual browser QA remains open in issue #97**, including mobile 375/390 px, desktop 1280/1440 px, keyboard and screen-reader focus, touch orbit, CDN-offline fallback, print SVG, GPU context loss, and visual occlusion at 0/50/100 separation. No screenshots or live-browser approvals have been claimed.

## Next tranche

- Add measured, revision-specific product-variant geometry and negative dimension-contract tests.
- Add reproducible mobile/keyboard/print screenshot baseline tests and conduct human visual verification.
- Add verified manufacturer boot/binding size tables and actual reference variants for ski and snowboard. Keep procurement, manufacturing, electronics, mounting and release decisions outside these informational previews.
