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

`catalog/board_components.v1.json` is the initial catalog. Entries may carry category, manufacturer/SKU, evidence state, procurement state, interface facts, source type, dated URL, price snapshot/range and hold reason.

Procurement states are `SOURCE_ONLY`, `HOLD_MEASURE`, `POWER_GATED`, `STUDY_ONLY`, and `BUY_CANDIDATE`. The seed catalog intentionally contains no buy-candidate power items. Vendor links are source links, not purchase authorization, and planning placeholders receive no invented vendor link.

## Candidate architectures

`configurator/architectures.v1.json` currently seeds four deliberately different hypotheses: Brake-first Trail Core, Compact Electric Coexistence Study, Range Explorer Drive Study, and SnowDeck Fit Bench. Their trait vectors are soft trade-space declarations. Hard compatibility findings remain separate.

## Fit score and trade-space frontier

The fit score is a weighted comparison of architecture traits against normalized rider priorities, plus small transparent mission adjustments for deck envelope, electric intent, braking requirement and budget. It is not a safety score.

The engine separately marks non-dominated candidates across the declared soft traits. This preserves meaningful alternatives instead of collapsing everything into one recommendation. `winner_selected=false` is part of the engine contract.

## BOM behavior

Each generated candidate gets a BOM with component ID, category, manufacturer/SKU when known, evidence state, procurement state, dated source URL, source date, price snapshot/range and hold reason. The displayed subtotal is explicitly a known-price subtotal and can be partial.

`checkout_state` is independent of fit score: `SOURCE_LINKS` means browsing only, `HOLD_MEASURE` means unresolved measurement/study holds, and `BLOCKED` means a power gate or hard blocker is present. The current platform does not place orders.

## Digital-twin handoff

Candidate cards deep-link to `/showcase/?preset=<configuration-preset>&candidate=<architecture-id>`. The twin applies the matching visualization preset. This handoff does not add evidence to the build-authority graph.

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

This first platform version does not claim exhaustive multi-vendor coverage, live stock/prices, automated checkout, arbitrary third-party compatibility, validated structural loads/braking, exact electric range/thermal behavior, battery/charger qualification, legal operating eligibility, fabrication authority, or powered-operation authority.

The next catalog phase should prioritize interface/provenance quality before volume: normalize deck/truck/axle/hub/wheel/brake interfaces, add sourced dimensions/SKUs, add evidence for mixed-vendor interfaces, build a separate live price/stock refresh service, mature electrical schemas before sourcing power hardware, and eventually replace planning priors with measured ride telemetry.
