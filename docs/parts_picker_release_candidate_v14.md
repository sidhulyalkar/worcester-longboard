# Worcester Parts Picker release candidate v1.4

**Status: research-only release candidate. Do not merge, order, fabricate, perform electrical commissioning, or use as ski-binding installation instructions merely because CI is green.**

The source-bound Assembly Atlas and Parts Picker changes are **stacked draft PRs**. The product must remain understandable to a beginner while preserving the difference between a manufacturer listing, source-backed geometry, compatibility evidence, mechanically inspected parts and an actual seller cart.

## Branch and integration topology

Merge these changes only in a deliberately reviewed sequence:

| Sequence | Draft PR | Layer | Required outcome |
| --- | --- | --- | --- |
| 1 | [#110](https://github.com/sidhulyalkar/worcester-longboard/pull/110) | Graph-driven source-aware 3D Assembly Atlas | Approved assembly schematic UX, no physical mounting permission |
| 2 | [#111](https://github.com/sidhulyalkar/worcester-longboard/pull/111) | Manufacturer family catalog, 4-sport Parts Picker, ski boot/board source-linked 3D | Verify manufacturer provenance, 2D fallbacks, all 4 sport selectors |
| 3 | [#112](https://github.com/sidhulyalkar/worcester-longboard/pull/112) | Maker-code / seller-pack evidence engine | Verify package unit math, CNC 420 brake exclusion, dated partial amounts |
| 4 | [#113](https://github.com/sidhulyalkar/worcester-longboard/pull/113) | Three per-sport design studies and matched retailer product setups | Verify cross-retailer setup consistency; don't equate ski-only and bundled ski |
| 5 | [#114](https://github.com/sidhulyalkar/worcester-longboard/pull/114) | Real Chromium release QA, explanatory warnings, formal human signoff | Review source-linked screenshots, working 3D, keyboard/touch/print |

The dependency chain is:
`main` → `#110` → `#111` → `#112` → `#113` → `#114`.

**Never merge #114 alone into main as a shortcut.** After reviewing and merging #110, retarget #111 to `main`; verify that GitHub correctly shows only its own intended diff, run CI on the exact new base and merge it. Repeat for #112–#114. Rebase only where needed. Resolve and validate any conflicts rather than using the green status of an older SHA. If the SHA changes, earlier reviews and screenshots may no longer match.

This is a **research website release process**, not mechanical certification or seller checkout qualification. The main X1 power, battery, chassis and ski-binding authorization boundaries must remain unchanged.

## Automated gates already implemented

`tests/browser/parts_picker_smoke.mjs` actually starts the Python HTTP server and opens `/builder/parts.html` in Chromium:

1. All four active sports and each sport's three distinct curated studies render, switch, and preserve the source-bound order worklist and zero qualified order lines.
2. Loaded 85 mm Caguama and 105 mm Dad Bod complete setups compare **only** to matching published multi-merchant setups, never by model-name substring or package price alone.
3. Atomic Bent 90 skis-only versus skis-with-bindings seller listings remain explicitly **incomparable**. Ski release/mount requirements remain professional service holds.
4. Optional left/right foot Mondo inputs retain independent fit warnings. Rider mass outside 15–250 kg is explicitly ignored with a visible message; the chosen assembly is not silently promoted.
5. JSON and CSV are **actual browser downloads**. JSON still says `checkout_eligible=false`, `known_order_total_usd=null`, `qualified_supplier_order_lines=0`; CSV seller quantity remains unknown independently of dated maker-unit research.
6. The part tree is keyboard-selectable. At 390, 768, 1280 and 1440 px the test checks no horizontal page overflow and stores full-page screenshots.
7. When the external Three.js CDN is deliberately blocked, the interactive 3D control safely returns the user to the source-linked SVG and keeps the assembly worklist intact.

`.github/workflows/parts-picker-browser-qa.yml` installs pinned Playwright 1.56.1 and Chromium, runs the test on pushes and pull requests, and uploads screenshots plus `browser-qa.json` for 14 days. It is **independent** of the large existing `validate` workflow, which must also pass.

Locally:

```bash
npm install --no-save --no-package-lock --ignore-scripts playwright@1.56.1
npx playwright install chromium
node tests/browser/parts_picker_smoke.mjs
python tools/check_parts_picker_release.py --mode preview
```

Screenshots include `desktop-alpine_ski.png`, `desktop-snowboard.png`, `desktop-skateboard_longboard.png`, `desktop-mountainboard.png`, `mobile-390.png`, `tablet-768.png`, `desktop-1280.png` and `cdn-unavailable-svg-fallback.png`.

**The screenshot files are not a substitute for actually inspecting them.** The successful test of a blocked CDN also does **not** test successful Three.js startup or native mobile GPU WebGL. Claim those as validated only after separate real-browser verification.

## Manual human review still required

Use `docs/parts_picker_human_review.template.json` as the checklist. An authorized reviewer must inspect the exact final tested commit and provide actual evidence for:

- Screenshots at desktop 1440/1280, tablet 768 and mobile 390 px; readable pricing holds and visible selected assembly.
- Keyboard plus screen-reader hierarchy and focus operation, and physical-device touch experience, not merely scripted desktop device emulation.
- **Successful** online WebGL loading, orbit, zoom camera presets, resize, switching 85/105 mm Loaded wheels and ski boots, and SVG fallback when unavailable. CAD remains illustrative.
- Print and export readability, correct seller link destinations and current external manufacturer source/size/pack claims.
- Explicit comprehension check that the UI is not a live cart or safe fabrication, electrical commissioning, ski binding mount or DIN/release calibration tool.

When all checks are truly complete, copy the template to a **separate review record** (do not edit the template to fictitious PASS values) and evaluate:

```bash
python tools/check_parts_picker_release.py --mode candidate \
  --browser-report /path/to/browser-qa.json \
  --manual-review /path/to/completed-review.json \
  --head-sha EXACT_40_CHAR_SHA
```

`candidate_merge_ready=true` means the **source-aware research website** has the two independent kinds of QA evidence for that exact revision. It never means `live_cart_ready`, `physical_assembly_authorized` or `professional_ski_binding_release_authorized`.

## Next implementation work after the merge

- Create a normalized exact seller `Offer` contract separate from a manufacturer family, with region, size-specific manufacturer SKU, seller SKU, received package counts, seller provenance, consent/rules and bounded source freshness. Price differences cannot be treated as real until full variant and package identity match.
- Add legally authorized/measured STEP/GLB asset ingestion with millimeter units, local coordinate frames, manufacturer provenance and an explicit model-revision binding. Physical mates, fasteners, clearances, BSL and release strength require independent qualification.
- Upgrade data-driven 3D from one visual-per-family to measured boot shell/binding assembly views with selectable boot size and stance while never suggesting release settings.
- Expand source-backed complete and service-inclusive templates for touring ski/splitboard, surf, bicycle and camping shelter once the four existing sports have trustworthy depth.
- Commission external hardware, Li-ion electrical systems and ski-binding release/adjustment outside the consumer research application with qualified professionals.

**The highest-value next human input is reviewing PR #114's screenshot artifact and the actual orbiting viewer.** No new parts purchases or manufacturing are required for software preview release.
