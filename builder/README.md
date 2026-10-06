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

Audit the current dated source layer with:

```bash
python tools/audit_board_catalog.py
```

Native-currency source prices are displayed as source metadata and excluded from the USD subtotal until an explicit dated USD/FX layer exists.


## Catalog Composer

`configurator/composer.v1.json` controls runtime synthesis from the normalized deck, truck, wheel, brake, drive and battery catalog.

The product keeps curated references and synthesized boards separate:

- curated candidates remain stable engineering anchors;
- synthesized candidates are marked **catalog composed**;
- each composed candidate exposes its exact slot selection and compatibility-state counts;
- opening Swap Lab reproduces the composed board exactly before the user edits anything.

The composer reuses Swap Lab compatibility evaluation and the standard rider-fit scorer. It prunes hard blockers and incompatible combinations, caps unresolved interfaces and candidate count, removes exact-BOM duplicates, and never promotes authority.
