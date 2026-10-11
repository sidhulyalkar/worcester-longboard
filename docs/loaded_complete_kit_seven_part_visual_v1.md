# Loaded complete-kit seven-child visual explorer v1

## Status

**An inspectable visualization, not measured CAD or a physical assembly plan.** This tranche extends the existing draft PR #114 and issue #117 without adding orderable parts or structural qualification.

The manufacturer claims for a selected Loaded Tangent complete 85 mm Caguama or 105 mm Dad Bod identify **one complete sellable package**, not seven independently purchasable product lines. The kit evidence ledger stores seven source-named **component categories**. The new visual graph offers seven independent selection identities linked back to that single package.

The original conservative source/source conflict remains: Loaded's maker page advertises Paris V3 trucks while Skates USA lists Paris V2. The reference package stays on **INCLUSION_REVISION_CONFLICT_HOLD**. All child receipt counts, exact option SKU, verified mating clearances, hardware fastener totals, dealer stock and actual cart amounts remain unresolved.

## Render pipeline

1. `buildPickerStudy()` creates one parent complete-package reference with no physical mount/checkout authority.
2. `auditCompleteKitClaim()` verifies the selected maker kit, returns seven inclusion-claim rows and holds the V2/V3 seller discrepancy.
3. `buildCompleteKitVisualGraph()` projects exactly those seven distinct child IDs into an optional **display-only** exploded semantic graph. It does not rewrite the underlying BOM, `report.rows`, `selected_variants` or seller units.
4. The same seven IDs drive the keyboard-accessible assembly tree, clickable SVG fallback, Three.js scene, component details and exported JSON's `display_graph`. Changing 105 mm → 85 mm invalidates every old child ID.
5. `planExplodedScene()` positions them at arbitrary visual coordinates. No geometry units, mount transformations, stresses, counterbores, clearance tolerances or prescribed assembly step order are inferred.

## Visual component semantics

| Child category | Visual only | What remains unknown |
| --- | --- | --- |
| Deck | Procedural board outline | Real deck laminate, flex and mounting tolerances |
| Zee brackets | Two symbolic bracket groups | Bracket shape, hole datums, mounting interface/load |
| Paris trucks | Two symbolic axle/hanger groups | V2 vs V3 source discrepancy, actual truck revision and fit |
| Wheels | Four visible wheel silhouettes, 85 vs 105 mm **ratio only** | Bearings, spacing, durometer/dimension tolerances and real clearance |
| Bearings | Eight conceptual rings | Received part identities/quantity/fit and installation |
| Deck hardware | One **symbol**, not a count | Actual screw count, thread, length, torque and included pieces |
| Truck hardware | One **symbol**, not a count | Actual screw count, thread, length, torque and included pieces |

Published wheel diameter is used only to show how larger/ smaller rolling outlines differ; the 3D scene does not certify wheel clearance, steering or chassis mechanics.

## Pinned local WebGL verification

Browser CI installs `playwright@1.56.1` and `three@0.180.0`. A local Python HTTP server exposes the repo's pinned `node_modules/three` module and import-map. The optional 3D loader uses it when available; otherwise it may attempt esm.sh. If neither loads, the source-linked 2D SVG and research worklist remain intact.

The extended Chromium suite tests **successful** WebGL context and frame rendering, seven scene IDs, camera preset, keyboard child selection, 100% explode slider, 2D identity parity, and export JSON. It separately blocks both local Three.js and the CDN to verify fallback. Screenshot artifact: `longboard-kit-seven-part-live-webgl.png`.

Use locally:

```bash
npm install --no-save --no-package-lock --ignore-scripts three@0.180.0 playwright@1.56.1
npx playwright install chromium
node tests/browser/parts_picker_smoke.mjs
python tools/serve_board_platform.py
# open http://127.0.0.1:8000/builder/parts.html
```

The local site still works as SVG without npm installed. Human mobile screenshots, successful target-device WebGL orbit, touch, accessibility and printed review remain release gates, and site functionality cannot grant mechanical/charging/fabrication/purchase approvals.

## Work left to finish issue #117

- Maker-authorized or measured individual CAD/GLB files with explicit license, units, stable coordinate axes, revision and content hashes.
- Verified physical mate datums and fastener lists, independent bracket, axle, wheel, bearing and clearance tests, plus source-cited torque guidance.
- Source-verified package contents and receiving evidence. The current "seven" represents **categories**, not guaranteed seven shipped physical objects.
- Camera step sequence tied to genuinely qualified maker instructions, not reverse-engineered movements.
- QA for scene memory disposal, canvas GPU budget, actual on-device touch/performance and errors when maker or seller revisions change.

**This is the next level of visual clarity, not a sign-off to purchase or assemble a vehicle.**
