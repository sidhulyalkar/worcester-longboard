# Worcester browser CAD schema and integrated Tangent board (v1)

**Scope: source-bound parametric visualization, not manufacturer CAD.**

This tranche upgrades the Loaded Tangent research pilot from independent category meshes to a **single declarative integrated model**, with consistent assembled/exploded poses, geometry source references and a browser-exportable representation. The visual positions are calculated in **arbitrary units**, not mounting millimeters.

## Architecture

| Layer | File | Authority |
| --- | --- | --- |
| Maker evidence | \`catalog/outdoor_complete_kit_claims.v1.json\` | Published complete-kit family and advertised child categories; physical receipt unknown |
| Visual recipe | \`catalog/outdoor_complete_kit_cad_recipes.v1.json\` | Seven reusable procedural prototypes, normalized deck/station layout and explosion offsets; no engineering datums |
| Compiler and validator | \`builder/complete_kit_cad_schema.mjs\` | Links seven role identities and source to exactly one selected maker kit, preserves 85/105 wheel option, checks every physical authority false |
| 3D renderer | \`builder/exploded_3d_viewer.mjs\` | Integrates deck, bracket symbols, trucks, wheels, bearings in one coordinate frame; uses instanced wheel/bearing buffers |
| 2D fallback | \`builder/complete_kit_cad_svg.mjs\` | A matching assembled top-view and separated SVG, all seven source IDs clickable |
| UI and evidence | \`builder/parts_picker_app.mjs\`, \`builder/parts.html\` | Default complete-board study, Assemble / Explode actions, orbit controls, kit-ledger highlighting, downloadable CAD-display JSON |
| Independent tests | \`tests/js/test_outdoor_complete_kit_cad_schema.mjs\`, \`tests/browser/parts_picker_smoke.mjs\` | Source identity, declared dimensions, zero approvals, malicious-input rejection, real browser WebGL/SVG parity and perf bounds |

The product still has **one parent package**, seven advertised child *categories* and **zero approved additional child purchase lines**. These category counts must never become inventory or fastener receipt counts.

## Geometry contract

The recipe stores a single normalized frame, a small number of visual layout parameters, a list of seven prototype roles and seven role-specific explosion offsets. The compiler generates repeated wheel/bearing elements from compact two-station and two-side patterns.

- X = across board; Y = nose to tail; Z = up.
- The maker-reference complete board dimensions are **914 × 248 mm**, and wheel reference diameters are **85 or 105 mm**, sourced from the selected kit reference.
- Those manufacturer-published overall values inform shape ratios, **not the physically measured deck mounting pattern, truck axle spacing, bracket profiles, wheel centerline, wheel clearance or fastener positions**.
- All visual poses, bracket locations, offsets, wheel separation and shapes are **illustrative**. Structural analysis, screw/thread/torque data, materials and measured mates are absent.
- Hardware sets have **one floating schematic glyph each**, visible only when exploded, because their shipped fastener counts and actual hole locations are unknown.
- The joined model is an integrated **design illustration**, not an assertion that the depicted physical geometry is actually compatible or sufficiently strong.

Each compiled child includes a stable \`component_id\`, \`parent_kit_id\`, maker source URL, shape type, normalized instances, a local exploded vector and explicit null \`true_mount_datum_mm\`, \`true_clearance_mm\`, received units and seller order units.

The compile step aborts on mismatched maker variant, absent original source, altered kit contents, unsupported wheel diameter or a recipe that claims any physical/financial authority.

## User experience

Upon opening the research Parts Picker, **Longboard** and the source-bound Loaded 105 mm complete study are preselected in the **integrated** position, \`0%\` explosion. The user may:

1. Orbit in 3D or continue in the integrated SVG.
2. Choose **Assemble complete board** (0%), **Explode into components** (100%) or any intermediate separation slider value.
3. Use Perspective, Top, Side and Front camera views, and select parts directly in the scene, source-bound assembly tree or kit receipt.
4. Switch to the 85 mm version; the full schema recompiles, displays smaller wheel references and invalidates all seven old child IDs.
5. Export a JSON record documenting the exact recipe, selected parent kit, published overall dimensions, generated normalized primitives, original maker page, and missing physical approvals.

If Three.js is absent, the same integrated/ exploded assembly can be explored in SVG. If Three.js is available, it loads as a locally pinned \`three@0.180.0\` package when installed and may fall back to esm.sh. No third-party content is necessary for the SVG.

## Validation

Run:

\`\`\`bash
git switch feat/parts-picker-release-gate-browser-qa-v14
npm install --no-save --no-package-lock --ignore-scripts playwright@1.56.1 three@0.180.0
npx playwright install chromium
node tests/browser/parts_picker_smoke.mjs
python tools/check_parts_picker_release.py --mode preview
python tools/serve_board_platform.py
\`\`\`

Navigate to \`http://127.0.0.1:8000/builder/parts.html\`.

Automated browser assertions now cover the **assembled** and exploded WebGL poses; the same seven source IDs in SVG, live 3D and exports; actual non-zero GL frames and draw-call/triangle bounds; camera controls; kit table selection; size switching; and recovery when both the local module and CDN are unavailable.

CI provides full-page PNGs including \`integrated-board-parametric-cad-webgl.png\` and \`longboard-kit-seven-part-live-webgl.png\`. These are machine-generated QA artifacts, **not** evidence of hand-reviewed visual fidelity or real-device touch/accessibility performance.

## What is required before this is actual engineering CAD?

1. Obtain rights-cleared *exact revision-specific* manufacturer STEP/GLB or independently measure the physical received component. Record source, licensing, file SHA256, coordinate axes, unit scale and maker revision.
2. Verify separate truck V2/V3 sources and actual seller-shipped contents. The original seller claims still conflict on Paris truck revision.
3. Recover actual mounting hole/datum coordinates, screw lengths and threads, steering sweep, axle/wheel/bearing geometries, deck/bracket stresses and clearances.
4. Store each measured interface as its own separately approved source claim and physical qualification receipt; link to the same graph IDs. Do not auto-infer physical qualification from a rendered model.
5. Only with legitimate dimensions may an independent engineer evaluate mechanical fit; unrelated ski-binding releases and any powered X1 battery/brake commissioning remain separately gated.

**The current app is now a usable integrated design study, not a manufacturing or checkout system.**
