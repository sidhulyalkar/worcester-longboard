# Worcester Board Builder platform

The Worcester Board Builder turns rider and mission inputs into explicit planning requirements, compares board architecture hypotheses, audits known component interfaces, and renders a provenance-aware bill of materials.

It is deliberately not a storefront that guesses compatibility.

## Product loop

```text
rider + mission questionnaire
        ↓
BoardRequirements
        ↓
architecture trade space
        ↓
compatibility / readiness evaluation
        ↓
candidate BOM + source provenance
        ↓
3D twin inspection
        ↓
physical measurement / qualification
        ↓
future catalog and model refinement
```

Worcester X1 is reference build `worcester_x1_0001`. It bootstraps the platform with a real evidence graph, but the generic Builder cannot promote X1 authority.

## Four separate questions

The UI and data model intentionally keep four ideas separate:

1. **Profile fit**: does the architecture's declared behavior match what the rider wants?
2. **Interface compatibility**: do the selected components have documented or physically established interfaces?
3. **Procurement readiness**: are the exact parts sufficiently sourced and released to buy?
4. **Physical authority**: did a real assembled system pass its required tests?

A high profile-fit score does not turn a `MEASURE_FIRST` interface into a compatible one and never opens a `POWER_GATED` item.

## Rider and mission intake

`configurator/questionnaire.v1.json` is the single questionnaire definition used by the web UI. The quick path asks high-information rider, terrain, mission, ride-feel and budget questions. Advanced mode adds shoe/stance details, cargo, snowboarding experience, speed comfort, charging, full terrain mix, weather, jumps, compliance, maneuverability, portability, maintenance, fabrication/electronics capability and complete priority weights.

Optional fields may remain unknown. Unknown data is preserved as uncertainty instead of being replaced with fake precision. Browser profile answers stay in local storage until the user explicitly exports a profile JSON.

## Requirement derivation

`configurator/rules.v1.json` contains every numerical planning assumption used by both deterministic engines. The derived `BoardRequirements` object includes loaded rider mass, target mission range, planning Wh/mi and installed-energy envelope, reserve fraction, normalized terrain mix, rough-terrain fraction, wheel strategy, friction-brake requirement, adjustable stance study interval, deck-envelope preference, ingress priority, electric intent, budget envelope, normalized priorities, assumptions and warnings.

Every derived result is marked `PLANNING_ESTIMATE`. Energy/range output compares architectures and is not a battery selection or range guarantee. Height-derived stance is only the center of an adjustable study range and is not a rider-fit prescription.

## Compatibility states

`configurator/compatibility_rules.v1.json` defines `COMPATIBLE`, `REFERENCE_COMPATIBLE`, `MEASURE_FIRST`, `UNKNOWN`, and `INCOMPATIBLE`.

The seed rules preserve current X1 facts: Comp 95 / Matrix + V5 is a reference-compatible brake path; the 400 mm / 50 mm axle branch is not a G1 drive branch; the G1 reference path uses 70 mm axle geometry; V5 alignment after that axle swap remains measure-first; and standard Rockstar II is not silently treated as compatible with the current 9-inch T2 listing.

An unknown spatial or mechanical interface propagates uncertainty. The solver may still show the architecture for study, but cannot convert uncertainty into a green compatibility claim.

## Catalog and provenance

The catalog is now split into three layers so source text, normalized mechanical interfaces and recommendation logic cannot blur together:

- `catalog/source_snapshots_YYYY-MM-DD.json` preserves dated vendor/retailer facts and native-currency source prices;
- `catalog/board_components.v1.json` normalizes stable component IDs, interface facts, evidence/procurement state and source provenance;
- `catalog/board_geometry.v1.json` normalizes deck/truck geometry used by the 2D renderer and 3D twin, including explicit visualization-only proxy values where an exact dimension is not published.

The first cross-vendor tranche includes MBS/Worcester, TRAMPA, Apex Boards, Boardnamics and Lacroix Boards reference parts. Procurement states remain `SOURCE_ONLY`, `HOLD_MEASURE`, `POWER_GATED`, `STUDY_ONLY`, and `BUY_CANDIDATE`. The catalog intentionally contains no buy-candidate power items. Vendor links are source links, not purchase authorization, and planning placeholders receive no invented vendor link.

Native-currency source prices remain source metadata rather than being silently converted into USD. The UI therefore reports a known USD subtotal plus explicit unpriced/source-native items.

See `docs/board_catalog_contract.md` for the ingestion, interface, compatibility, visual-substitution and freshness rules.

## Candidate architectures

`configurator/architectures.v1.json` now spans materially different mechanical families rather than only X1 variations. In addition to the MBS/Worcester brake-first, coexistence, range and SnowDeck studies, the current tranche includes a TRAMPA Short carve core, a TRAMPA HS11 hydraulic freeride core, a TRAMPA + Boardnamics coexistence study, a TRAMPA 9-inch open-belt-drive study, an Apex Air parallel-kingpin + Boardnamics M1-AT study, a Lacroix Barrel unpowered carve reference, and a Lacroix Hypertruck Lite native belt-drive study.

Their trait vectors are soft trade-space declarations. Hard compatibility findings remain separate. Regression tests require the reference manual-carver and electric-trail profiles to produce different top-ranked architectures and to retain cross-vendor breadth in each top-three set.

## Catalog Composer v1

The platform now has two candidate sources:

- **Curated reference architectures** are stable human-authored hypotheses used as regression anchors and to preserve deliberately blocked educational studies.
- **Catalog-composed candidates** are generated at runtime from normalized deck, truck/topology, wheel, friction-brake, drive and battery slots.

`configurator/composer.v1.json` is the machine-readable synthesis contract. The composer is deliberately bounded rather than an unrestricted Cartesian-product recommender. It caps raw enumeration, unresolved interface findings, output count and candidates per vendor family.

Every proposed combination follows the same sequence:

```text
normalized catalog selection
        ↓
Swap Lab component resolution
        ↓
explicit compatibility rules
        ↓
fail-closed UNKNOWN category-pair fallbacks
        ↓
mission brake / electric / energy checks
        ↓
prune BLOCKED and INCOMPATIBLE
        ↓
transparent catalog trait heuristic
        ↓
standard rider-fit scorer
        ↓
exact-BOM deduplication
        ↓
bounded synthesized frontier
```

The composer currently emits only `REFERENCE_COMPATIBLE` and `MEASURE_FIRST` candidates with no hard blocker and at most the configured number of unresolved findings. Curated reference candidates remain free to show blocked or incompatible concepts when those are useful engineering comparisons.

For an electric mission, a synthesized candidate must contain both a drive and a traction-energy planning class. For an unpowered mission, the composer adds neither. If the rider mission requires an independent friction brake, combinations without one are rejected before they can become synthesized candidates.

Soft traits for a newly composed board use the explicitly labeled `PLANNING_HEURISTIC` model in `composer.v1.json`. That model uses normalized deck length, truck width, wheel diameter, drive type, known-price subtotal and unresolved-interface count to produce comparison traits. These are ranking proxies, not measured physical performance predictions.

Each synthesized candidate carries:

- `origin = SYNTHESIZED`;
- exact `swap_defaults` so opening Swap Lab reproduces the generated design with zero edits;
- a `composition` record containing the selected slots, named manufacturers, compatibility-state counts and rationale;
- the same BOM, visual-state, 3D handoff, readiness and authority-false contracts as curated candidates.

Python and browser implementations are independent (`configurator/composer.py` and `builder/composer.mjs`) and CI requires exact design-space parity. `configurator/platform_engine.py` and `builder/platform_engine.mjs` merge curated and synthesized candidates, remove exact-BOM duplicates, recompute the trade-space frontier and preserve `winner_selected=false`.

The composer can never create procurement, fabrication, charging or powered-operation authority. Its authority object contains only false flags, and the Board Builder validator rejects a composer configuration that permits `BLOCKED`/`INCOMPATIBLE` synthesis or references unknown Swap Lab options.

## Fit score and trade-space frontier

The fit score is a weighted comparison of architecture traits against normalized rider priorities, plus small transparent mission adjustments for deck envelope, electric intent, braking requirement and budget. It is not a safety score.

The engine separately marks non-dominated candidates across the declared soft traits. This preserves meaningful alternatives instead of collapsing everything into one recommendation. `winner_selected=false` is part of the engine contract.

## BOM behavior

Each generated candidate gets a BOM with component ID, category, manufacturer/SKU when known, evidence state, procurement state, dated source URL, source date, price snapshot/range and hold reason. The displayed subtotal is explicitly a known-price subtotal and can be partial.

`checkout_state` is independent of fit score: `SOURCE_LINKS` means browsing only, `HOLD_MEASURE` means unresolved measurement/study holds, and `BLOCKED` means a power gate or hard blocker is present. The current platform does not place orders.

## Swap Lab

The Board Builder now supports a component-level **Swap Lab** on top of every generated candidate.

`configurator/swap_slots.v1.json` defines the editable slots and their allowed catalog-backed options. The current editable study dimensions are deck envelope, truck/axle topology, wheel/tire study, mechanical brake, drive, battery class, rider interface, trail armor, and passive dock.

The baseline candidate is immutable. A swap creates a separate `non_authoritative_component_swap_study` and recalculates:

- resolved component IDs and source-aware BOM;
- known-price range and delta versus the generated baseline;
- pairwise compatibility rules;
- mission-required friction braking;
- mission energy versus the selected battery class;
- wheel-strategy mismatch;
- procurement state;
- blockers, unknowns, and measure-first findings.

The Swap Lab deliberately supports bad combinations because showing *why* they fail is useful. For example, the current rules reject a V5 brake on the 420 mm drive-clearance reference, keep the 440 mm / 70 mm coexistence branch measure-first, and keep the T2 9-inch tire on standard Rockstar II geometry measure-first.

Power selections remain `POWER_GATED`. A user can study them, but the editor cannot convert them into a purchasable or ride-authorized system.

### Swap Lab CLI

```bash
python tools/evaluate_board_swap.py \
  configurator/examples/trail_rider_profile.json \
  configurator/examples/swap_incompatible_study.json \
  --candidate x1_compact_electric_study \
  --out /tmp/custom-board.json
```

The browser engine counterpart is `builder/swap_engine.mjs`. CI evaluates the same edit through Python and JavaScript and compares the outputs.

## Auto-generated candidate visuals

Every generated candidate also projects into a versioned `candidate_visual_state`.

The visual state contains the candidate's deck envelope, truck/topology branch, wheel study, rider-profile stance center, visible systems, readiness, checkout state, fit score and known-price band. Its authority object is hard-coded to visualization-only with procurement/fabrication/powered-operation authorization false.

The dimensional geometry now comes from `catalog/board_geometry.v1.json`, which is consumed by both the Builder and the digital twin. System visibility comes from the candidate BOM, not merely from a named showcase preset. The visual state also carries deck-shape, steering, wheel/hub, brake and drive families, so substitution can change the actual schematic character of the board rather than only its label.

The browser renderer in `builder/preview_renderer.mjs` emits deterministic SVG in three comparison views:

- **Hero** for immediate product recognition;
- **Top** for deck, stance and truck/wheel-width comparison;
- **Side** for wheel size and under-deck system comparison.

One view selector updates the whole candidate gallery so builds are compared from the same perspective.

The current preview renderer is schematic. It distinguishes MBS-style, TRAMPA composite and Lacroix asymmetric deck silhouettes; channel-spring, parallel-kingpin and precision bushing/spring trucks; wheel/hub families; hydraulic/mechanical brake cues; gear/open-belt/native-belt drive cues; and 8-inch/9-inch proportions. It intentionally does not claim fabrication-level surface geometry, loaded ground clearance, tire deformation, exact drive/brake packaging or structural strength.

### Visual parity and headless export

Python and browser visual-state derivation are implemented separately in `configurator/visual_state.py` and `builder/visual_state.mjs`, but consume the same component catalog and generic geometry registry. CI compares their full serialized visual states.

Headless SVG generation uses the browser renderer directly:

```bash
python tools/build_board_visual_states.py \
  configurator/examples/trail_rider_profile.json \
  --out /tmp/visual-states.json

node tools/render_board_candidate_previews.mjs \
  configurator/examples/trail_rider_profile.json \
  --out-dir /tmp/board-previews
```

Swap Lab edits project through the same visual contract, so component changes immediately change the custom board preview.

## Digital-twin handoff

Candidate cards deep-link to the matching visualization preset while overriding it with the generated candidate's actual deck, topology, wheel study, stance center and system-layer state. Swap Lab studies carry the edited version of those same fields. URL overrides are visualization-only and do not add evidence to the build-authority graph.

## Deterministic engines

The same versioned JSON is consumed by `configurator/engine.py` and `builder/engine.mjs`. CI runs an identical example profile through both and compares derived requirements, candidate IDs, fit scores, readiness, checkout state, cost summaries, blockers/unknowns, frontier membership and authority fields.

## CLI workflow

```bash
python tools/derive_board_requirements.py configurator/examples/trail_rider_profile.json

python tools/generate_board_candidates.py \
  configurator/examples/trail_rider_profile.json \
  --out /tmp/board-candidates.json

python tools/render_board_bom.py \
  configurator/examples/trail_rider_profile.json \
  --candidate x1_compact_electric_study \
  --out /tmp/x1-electric-study-bom.md

python tools/validate_board_builder.py

python tools/audit_board_catalog.py
```

## Browser workflow

```bash
python tools/serve_board_platform.py
```

To rebuild the synthetic demonstration twin before serving:

```bash
python tools/serve_board_platform.py --prepare-showcase --synthetic-snowdeck-demo
```

Open `http://127.0.0.1:8000/builder/`. The root landing page is `http://127.0.0.1:8000/` and the twin is `http://127.0.0.1:8000/showcase/`.

## Current limits

The platform now has real cross-vendor mechanical breadth, but it still does not claim exhaustive coverage, live stock/prices, automated checkout, arbitrary third-party compatibility, validated structural loads/braking, exact electric range/thermal behavior, battery/charger qualification, legal operating eligibility, fabrication authority, or powered-operation authority.

The next catalog phase should continue expanding interface quality before raw item count: more deck/truck/hub/wheel/brake families, stronger mixed-vendor interface evidence, explicit mounting-pattern schemas, more complete visual geometry, a separate live price/stock refresh service, and electrical schemas mature enough to compare controllers/packs without pretending they are released hardware.
