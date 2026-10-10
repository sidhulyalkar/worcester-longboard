# Board Builder

`builder/` is the browser product surface for the generic Worcester Board Builder.

It consumes the versioned data under `configurator/` and `catalog/`. `builder/engine.mjs` keeps the curated reference scorer, `builder/composer.mjs` synthesizes bounded catalog combinations, and `builder/platform_engine.mjs` merges both into one deterministic design space. `builder/swap_engine.mjs` powers component evaluation, while `builder/visual_state.mjs` + `builder/preview_renderer.mjs` generate deterministic Hero/Top/Side visuals.

## Run

From the repository root:

```bash
python tools/serve_board_platform.py
```

Or rebuild the twin first:

```bash
python tools/serve_board_platform.py --prepare-showcase --synthetic-snowdeck-demo
```

Open `http://127.0.0.1:8000/builder/`.

No separate build step is required.

## Validate

```bash
python tools/validate_board_builder.py
python -m pytest -q tests/test_board_builder_engine.py tests/test_board_builder_contract.py tests/test_board_builder_ui_contract.py
node --test tests/js/test_board_builder_engine.mjs tests/js/test_board_catalog_composer.mjs tests/js/test_board_builder_swap_lab.mjs tests/js/test_board_builder_visuals.mjs
```

The full repository validator also checks Python/browser parity.

## Boundary

The Builder generates planning requirements, candidate architecture comparisons, compatibility findings and source-aware BOMs. It does not create procurement, fabrication, charging, ride or powered-operation authority.


## Swap Lab

Choose any generated candidate, then edit deck envelope, truck/axle topology, wheel study, mechanical brake, drive, battery class, rider interface, armor, and passive dock.

The baseline candidate remains immutable. Every edit creates a separate non-authoritative custom-design state that:

- rebuilds the source-aware BOM;
- reports known-price delta versus the baseline;
- reruns pairwise compatibility rules;
- rechecks the mission's friction-brake and energy requirements;
- preserves power-gated parts as blocked;
- shows blockers and measure-first items independently;
- can be exported as JSON;
- can be opened in the 3D twin with edited deck/topology/layer state.

A Swap Lab design is not an order, fabrication release, or powered-operation permit.


## Auto-generated visual gallery

Candidate visuals regenerate automatically whenever the rider profile changes. A shared **Hero / Top / Side** control changes every candidate to the same view for direct comparison.

The preview state is not inferred from marketing art. It is derived from normalized catalog facts:

- the generated candidate's deck candidate ID;
- the generated truck/topology branch;
- the rider-profile stance center;
- the candidate's actual wheel study;
- the candidate BOM's brake, drive, battery, SnowDeck, armor and dock contents;
- the current compatibility/readiness result.

The dimensional source for deck and topology geometry is now `catalog/board_geometry.v1.json`, the same generic registry consumed by the 3D twin. Candidate visuals therefore support MBS, TRAMPA, Apex and Lacroix geometry without inheriting extra systems from a convenient X1 showcase preset.

Every card can export its current preview as SVG. Headless export is also available:

```bash
node tools/render_board_candidate_previews.mjs \
  configurator/examples/trail_rider_profile.json \
  --out-dir /tmp/board-previews
```

This writes Hero, Top and Side SVGs plus a visualization-only manifest.

Swap Lab edits regenerate a separate custom preview live. Opening the edited design in the 3D twin carries deck, topology, wheel study, stance and visible-system state in the URL.

The SVGs are comparison illustrations, not fabrication drawings. In particular, a larger-wheel visual study does not itself recompute loaded clearance, tire deformation, gearing, structural loads or braking performance.


## Multi-vendor catalog

The first real cross-vendor tranche includes MBS/Worcester, TRAMPA, Apex Boards, Boardnamics and Lacroix Boards families. Generated candidates and Swap Lab edits can now produce visibly and mechanically different deck, truck, wheel, brake and drive combinations.

Catalog growth follows `docs/board_catalog_contract.md`. Critical cross-category interfaces default to `UNKNOWN` unless an explicit sourced rule exists.

Audit structural catalog integrity with:

```bash
python tools/audit_board_catalog.py --as-of 2026-10-07
```

Build the per-component source-health report and refresh queue with:

```bash
python tools/build_catalog_source_health.py \
  --as-of 2026-10-07 \
  --out /tmp/catalog-health.json \
  --worklist /tmp/catalog-refresh-worklist.md \
  --fail-on-integrity
```

The Builder loads `catalog/catalog_health.v1.json` and shows evidence freshness next to vendor source links. `SOURCE_FRESH` means the recorded source evidence is recent under the maintenance policy; it is **not** live stock confirmation or checkout permission.

Native-currency source prices are displayed as source metadata and excluded from the USD subtotal until an explicit dated USD/FX layer exists.


## Catalog Composer

`configurator/composer.v1.json` controls runtime synthesis from the normalized deck, truck, wheel, brake, drive and battery catalog.

The product keeps curated references and synthesized boards separate:

- curated candidates remain stable engineering anchors;
- synthesized candidates are marked **catalog composed**;
- each composed candidate exposes its exact slot selection and compatibility-state counts;
- opening Swap Lab reproduces the composed board exactly before the user edits anything.

The composer reuses Swap Lab compatibility evaluation and the standard rider-fit scorer. It prunes hard blockers and incompatible combinations, caps unresolved interfaces and candidate count, removes exact-BOM duplicates, and never promotes authority.


### Evidence-driven explorer (v1.1)

Select **Inspect evidence + BOM** for an interface-by-interface rule matrix, underlying component/source links and dates, and exact-revision measurement questions for every unresolved interface. The **Export worklist** JSON is a non-authoritative study artifact. Swap Lab recalculates the same evidence for edited configurations. Source freshness, unknown prices and hard mechanical holds are deliberately separate; a high profile-fit score never grants safety or checkout permission.

### Example rides, comparison, and assembly onboarding

Six default ride briefs in `configurator/example_rides.v1.json` provide a sensible first screen: manual dirt carving, brake-first mixed trail, manual city carving, mixed-terrain electric concept, nine-inch rollover study, and a cross-vendor coexistence lab. The **budget amounts are questionnaire goals, not catalog quotes**. Each brief uses an existing curated reference for its visual preview. Loading one regenerates candidates using the normal model; it never asserts that the reference is the best, purchasable, or mechanically approved.

The comparison workbench displays two selectable candidates from the same rider profile in matched views. It distinguishes actual physical configurations, normalized geometry (including reference/visual-only status), known USD subtotal, unpriced items, source-maintenance findings, explicit compatibility blockers, and unresolved interface measurement tasks. The export remains planning-only with all authority fields false.

The Assembly Readiness area translates a selected design into a learning/handoff roadmap. Deck/truck/wheel integration requires exact revision and manufacturer torque/fastener instructions. Drive/brake coexistence requires dimensional evidence. High-energy battery, BMS, charger, controller, enclosure and power commissioning require appropriately qualified specialists and independent validation; the generic Builder cannot authorize them. Do not assemble a loose-cell pack using catalog placeholders. Assembly labor, tools, shipping, tax, protective equipment and tests are outside known subtotals.

Sources for safety context: CPSC micromobility charging guidance (https://www.cpsc.gov/Safety-Education/Safety-Education-Centers/Micromobility-Information-Center) and UL personal e-mobility electrical systems testing (https://www.ul.com/services/personal-e-mobility-evaluation-testing-and-certification). These do not confer certification or mechanical qualification upon generated candidates.

## Review-first ride brief (v1)

Above the sample rides, the Builder now accepts a short free-text ride description. A deterministic **local** parser proposes questionnaire edits, displaying current and proposed values. Explicit measurements and budgets are preselected for review; inferred terrain percentages or carving priorities are off until checked. Users must click **Apply checked changes + regenerate**. The normal candidate synthesis, previews, BOM, compatibility explorer and assembly-learning roadmap then update together.

This is intentionally a narrow parser, not a general-purpose LLM chat agent. Unsupported and contradictory inputs surface questions, never fabrication instructions or purchase permission. See [customization roadmap](../docs/ride_brief_customization_roadmap.md).


## Multi-turn state core (v1.1, staged)

\`builder/conversation_state.mjs\` now provides a versioned, deterministic and non-authoritative session model around the existing review-first parser. It records explicit accepted field changes, reviewed relative preference changes, rejections, question suggestions, per-field provenance, revision history, exact undo and JSON export. This tranche is **an engine contract, not yet a connected chat interface**; \`builder/app.js\` still exposes the single-brief review workflow. UI integration and profile/manual-edit reconciliation are the next stage.

A request such as "make it lighter" or "less expensive" creates only a suggested constraint delta. It does not assert a matching board exists, silently update the profile, alter source BOM authority or qualify a vehicle.

Run the state regression suite:

\`\`\`bash
node --check builder/conversation_state.mjs
node --test tests/js/test_board_conversation_state.mjs
\`\`\`

See [October development roadmap](../docs/board_builder_development_plan_2026-10-10.md) for the staged UI, mechanical search, Build Passport and physical qualification roadmap.
