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

`builder/conversation_state.mjs` now provides a versioned, deterministic and non-authoritative session model around the existing review-first parser. It records explicit accepted field changes, reviewed relative preference changes, rejections, question suggestions, per-field provenance, revision history, exact undo and JSON export. This tranche is **an engine contract, not yet a connected chat interface**; `builder/app.js` still exposes the single-brief review workflow. UI integration and profile/manual-edit reconciliation are the next stage.

A request such as "make it lighter" or "less expensive" creates only a suggested constraint delta. It does not assert a matching board exists, silently update the profile, alter source BOM authority or qualify a vehicle.

Run the state regression suite:

```bash
node --check builder/conversation_state.mjs
node --test tests/js/test_board_conversation_state.mjs
```

See [October development roadmap](../docs/board_builder_development_plan_2026-10-10.md) for the staged UI, mechanical search, Build Passport and physical qualification roadmap.


## Browser conversation integration (v1.1b)

The browser ride brief now uses the deterministic session model. A rider can submit a new brief, inspect accepted-vs-inferred proposal groups, apply approved changes, compare regenerated boards, and undo the last recorded specification edit. The **Design conversation** panel shows recent revision history and exports a versioned local JSON session.

Questionnaire input invalidates any pending proposal immediately. The completed manual form is reconciled as a tracked change; incomplete terrain percentages, contradicting budget or mileage and invalid values pause conversational edits until corrected. A second free-text turn cannot replace an unreviewed proposal without explicitly discarding it.

The session snapshot stays in browser storage beside the existing profile; stale or mismatched local snapshots are not replayed. Loading one of the six example ride briefs saves the previous in-memory personal conversation so **Restore my previous profile** returns it. User-entered fit notes can appear in exported JSON; the UI does not upload them.

This is still a deterministic, narrow local language parser. It does not promise general LLM understanding or automatically authorize physical compatibility, ordering, electrical work, charging or riding.

Run:
`node --test tests/js/test_board_ride_brief.mjs tests/js/test_board_conversation_state.mjs`
and:
`python -m pytest -q tests/test_board_builder_ui_contract.py`

The next stage is conflict-directed feasibility and mechanically diverse candidate selection (Issue #95).

## v1.2: physically diverse candidate directions (first slice)

Board Builder now computes a **three-direction planning shortlist** from the full catalog/curated result. The implementation lives in `builder/diversity.mjs` and `configurator/diversity.py`, with deterministic Python/browser parity added to the comparator. A shortlist candidate must not have an explicit hard blocker, incompatible interface, or a known minimum parts subtotal already exceeding the rider's hard budget.

The first design is the highest-scoring eligible study. Later designs must each differ from every previously selected design on at least two physical axes and must change either deck or truck topology. Novelty is calculated from exact deck, truck, wheel, brake and drive selections, not paint or vendor names. If there are fewer than three such studies, the UI says so; the tool does not invent another. Candidates with unresolved `UNKNOWN`/`MEASURE_FIRST` interfaces can remain **planning hypotheses only**, with their interface counts visible.

No shortlist entry is a build, fabrication release, compatible kit, complete price or ride permit. Known-price values exclude labor, tools, validation, tax, shipping and unknown component costs. The full gallery and detailed evidence remain available beneath the shortlist. This is the first tranche of [Issue #95](https://github.com/sidhulyalkar/worcester-longboard/issues/95), not physical qualification.

Run:

```bash
node --test tests/js/test_board_diversity.mjs
python -m pytest -q tests/test_board_diversity.py
```


## v1.2 feasibility receipt explorer

The Builder now exposes an expandable per-candidate feasibility receipt and JSON export. The Python and browser engines independently derive a deterministic `feasibility_report` containing:

- recorded mission/mechanical blockers and catalog `INCOMPATIBLE` interfaces (hard stops);
- `UNKNOWN` / `MEASURE_FIRST` interface work remaining (never silently compatible);
- component source-refresh work and unpriced entries (separate uncertainty);
- a known parts minimum against the rider's hard budget. Passing this screen **cannot** establish an all-in budget because tax, shipping, tools, professional integration, validation and missing quotes are not captured;
- the reason a candidate did not appear in the three-direction shortlist, without falsely treating diversity omission as an engineering failure;
- next measurement/supplier-document tasks and `NOT_QUALIFIED` physical status.

`PLANNING_STUDY`, `UNRESOLVED_STUDY` and `BLOCKED` are explanatory software states only. None permits procurement, fabrication, charging or powered use. For every candidate, the receipt carries an all-false authority object.

Run `node --test tests/js/test_board_feasibility.mjs` and `python -m pytest -q tests/test_board_feasibility.py`; the full CI also tests Python/browser exact parity.


## v1.3: Build Passport (revision-aware planning handoff)

A selected candidate now offers a [Build Passport contract](../docs/build_passport_contract.md) with SKU text, explicit unverified revision, dated source/health, historical price basis, native-currency snapshots, unknown stock, and *unknown assembly purchase quantities*. It links to real supplier evidence but does not relabel any storefront as a manufacturer installation manual. It exposes donor-inclusion checks, interface measurement work, skill-gated receiving/assembly stages, JSON export, and print layout.

A **revision what-if** invalidates every directly dependent pairwise interface claim and creates a separate non-authoritative change receipt. It never modifies the actual catalog. Python/JS implement matching packages and CI enforces manual and electric example parity with `tools/compare_build_passports.py`.

```bash
node --test tests/js/test_board_build_passport.mjs
python -m pytest -q tests/test_board_build_passport.py
python tools/generate_build_passport.py configurator/examples/trail_rider_profile.json brake_first_trail_core
```

This is the first auditable learning/sourcing tranche for [Issue #96](https://github.com/sidhulyalkar/worcester-longboard/issues/96), **not** a qualified ordering guide, self-assembly instruction sheet, electrical design, current quote or live checkout.


## v1.4: Evidence notebook for exact Build Passport snapshots

Under a selected Build Passport, expand the **Evidence notebook** to record a dated supplier reference, received part identity/count, candidate manufacturer instructions or an unresolved interface measurement note. The notebook is bound to the passport's source/variant identity and saved locally; it does **not** upload notes. Export **evidence + passport** to retain a user-controlled JSON snapshot including the review queue. Previous evidence is not silently applied after a source, part or design revision change.

A received count is not a verified BOM quantity; candidate manual links and shop listings are not independent manufacturer-document verification; measurement notes do not clear interface states. Record content remains self-reported and unverified, and donor revision changes conservatively invalidate all catalog pair claims. No buying, mechanical assembly, battery integration, charging or powered operation is released.

The [evidence notebook contract](../docs/evidence_notebook_contract.md) describes the trust boundaries, storage, required fields and remaining source/physical measurements. Tests and cross-runtime parity:

```bash
node --test tests/js/test_board_evidence_notebook.mjs
python -m pytest -q tests/test_board_evidence_notebook.py
python tools/compare_evidence_notebooks.py
```

This is a useful research and receiving handoff, but not a verified digital twin of received hardware.


## v1.5: donor parts-inclusion and supplier-order-unit audit

The selected **Build Passport** now contains a compact, expandable **Parts-inclusion audit**. It distinguishes historical donor package claims from independently priced catalog references so riders can identify possible double-counted truck, hub, tire and deck references without deleting lines or inventing savings.

A dated source-bound inclusion registry identifies possible duplicates and specific donor retrofit measurement questions. Every actual assembly count, vendor order unit, current stock, confirmed quote and adjusted all-in total stays **unknown**. The full audit is embedded in Build Passport JSON and covered by Python/browser parity. A proposed variant revision invalidates the old inclusion audit.

See [the package inclusion contract](../docs/assembly_inclusion_audit_contract.md). All electrical, brake, structure and order authority remain false.

```bash
python tools/validate_board_package_inclusions.py
node --test tests/js/test_board_assembly_inventory.mjs
python -m pytest -q tests/test_board_assembly_inventory.py
```


## v1.6: receiving-to-BOM discrepancies and manufacturer document leads

Within **Build Passport**, expand **Receiving reconciliation** to see which exact catalog components have no user-recorded receipt, any contradictory counts/revisions across notes, donor contents that have not been individually inspected, and which official manufacturer reference pages may be worth consulting. These reference links are **not** exact-revision-approved manufacturer installation manuals.

This view updates as users record observations in the Evidence notebook. Repeated notes are **not summed** into stock. The combined evidence JSON export includes the reconciliation review queue. The browser stores these observations locally until the user chooses to export.

Documentation and reproducible safety tests: [receiving reconciliation contract](../docs/receiving_reconciliation_contract.md).

```bash
node --test tests/js/test_board_receiving_reconciliation.mjs
python -m pytest -q tests/test_board_receiving_reconciliation.py
python tools/compare_receiving_reconciliations.py
python tools/validate_manufacturer_document_references.py
```

An observation is not a verified part, an assembled quantity or permission to wire batteries, charge or ride.


## Experimental multi-sport direction

The current Builder **still configures mountainboard studies only**. The repository now contains a [domain-neutral outdoor-equipment architecture](../docs/outdoor_equipment_platform_architecture_2026-10-10.md) and [read-only taxonomy registry](../catalog/outdoor_equipment_domains.v0.json) for proposed skateboard/longboard, snowboard, ski, surfboard, bicycle and camping-shelter adapters.

These are **not** current user-facing product options. They add no supplier products, physical approvals or change to v1 Board Builder outputs. The first implementation following the domain contract is a read-only v1 catalog-to-core adapter, tested against the existing evidence and authority model.


## Outdoor Catalog Lab (experimental)

From the Board Builder top navigation, open **Catalog Lab**, or visit http://127.0.0.1:8000/builder/catalog.html with the existing local server. It now shows nine planned equipment domains and a read-only, searchable product/variant/offer/engineering-claim graph imported from the current board catalog.

No skis, snowboards, surfboards or other sport products are yet indexed; those domains are architecture proposals. All families and variants are provisional, historical supplier references are not live stock, and order quantities, maker-revision applicability, physical fit and all release authorities remain unverified.

Graph contract: [Outdoor Catalog Graph v1](../docs/outdoor_catalog_graph_v1_contract.md). Cross-runtime parity test: python tools/compare_outdoor_catalog_graphs.py . Legacy Board Builder candidate generation and Build Passport are regression-tested for exact replay parity.


## Exploded Assembly Atlas (mountainboards + cross-sport concepts)

After selecting a board, open **Inside the build** beneath the BOM. The source-aware assembly graph separates the selected design's existing catalog components into conceptual systems such as platform, mounting, wheels, rider interface, brakes/drive and power. Drag **Assembly separation** from assembled overview to exploded diagram, select a part in the grouped tree or diagram, inspect its source and package-overlap questions, and export an SVG diagram or JSON assembly graph. These are **never assembly instructions or verified CAD dimensions**.

The equipment selector also demonstrates **illustrative, UNSOURCED** longboard/skateboard, snowboard, alpine ski, splitboard and surfboard assembly recipes. These examples introduce no saleable SKU, matched boot-binding or physical approval. Snowboards and skis have separate fit/release checks, splitboards require touring pivot/puck interfaces, and fins can be optional for surfboards. Existing board candidate/BOM/price outputs are unchanged.

Technical specification: [Exploded assembly contract](../docs/exploded_assembly_contract.md). Validation: node --test tests/js/test_board_exploded_assembly.mjs; python tools/compare_exploded_assemblies.py. Actual mounting/fastener geometry, assembly quantities, stock, donor contents and power/ride authority remain unknown.


## Public manufacturer reference studies: longboards and Burton snowboards

The Assembly Atlas equipment selector now has a separate group of **maker-referenced but unqualified** designs. It includes the manufacturer-advertised complete assemblies for Loaded Tangent and Omakase longboards, plus Burton Custom, Good Company and Process board families studied with Mission, Cartel and Step On Re:Flex binding families and Burton Combo Disc references.

The manufacturer product pages provide meaningful board/mount/component information, but actual boot and binding sizes, purchased options, included unit counts, correct hardware, revisions, fit and current quotes are not known. No auto-generated assembly procedures or checkout controls are enabled. Step On family choices explicitly require matching Step On boots; Re:Flex needs the correct discs; EST is not suitable for non-Channel boards. Every physical qualification remains blocked.

Source registry: catalog/board_sport_reference_studies.v1.json. Negative/positive mounting family rules: builder/snowboard_mount_reference.mjs. Source/fit contract: docs/board_sport_reference_pilot_v1.md.
