# X1 Showcase

Local authority-aware visualization scaffold for Worcester X1.

## Run

From the repository root:

```bash
python tools/prepare_x1_showcase.py
python -m http.server 8000
```

The preparation command runs the rolling-chassis, Fit Rig, one-zone and SnowDeck CAD generators, converts generated STL references to GLB, builds the authority-aware runtime manifest, then renders a deterministic engineering review at `showcase/generated/design_review.md`. Use `--skip-cad` or `--skip-assets` when iterating only on evidence/UI state.

Open:

`http://localhost:8000/showcase/`

The initial viewer uses procedural geometry so it can run before detailed mesh conversion. It is intentionally a design-review visualization rather than fabrication authority.

## Add real authority evidence

By default every physical gate is closed.

Fingerprint-valid local authority documents may be supplied explicitly:

```bash
python tools/build_showcase_manifest.py \
  --evidence /path/to/private/x1_one_zone_pilot.json \
  --evidence /path/to/private/x1_fit_platform_repeatability.json
```

The manifest builder calls the repository's existing `tools/evaluate_build_authority.py` logic, including evidence predicates, fingerprint verification, upstream dependencies and evidence links. A document that merely claims `qualified=true` cannot promote the visualization.

The pre-hardware showcase also refuses any supplied document that asserts `powered_operation_authorized=true`.

Do not commit private rider measurements or raw fit logs to `showcase/`.


## CAD asset conversion

`tools/export_showcase_assets.py` converts generated STL references to GLB and writes a hash manifest under `showcase/generated/`. This is format conversion only. Source and output SHA-256 values are recorded, and every generated asset explicitly carries `physical_authority=false`.

The browser scaffold currently uses procedural evidence-colored geometry as its default because that keeps component states visually distinct. The GLB package is the next input for detailed mesh/clearance views.


## Interactive studies

The viewer is Z-up to match the CadQuery coordinate convention.

It supports:

- the three Issue #25 deck maximum-envelope references;
- the three current brake/drive topology geometry branches;
- manual or animated ±22 degree reference steering;
- provisional 65 mm static / 45 mm compressed-clearance overlays;
- exploded anatomy;
- independently adjustable front/rear SnowDeck yaw and cant;
- a compliance-layer thickness proxy;
- optional hashed GLB neutral and steering-sweep overlays.

The SnowDeck controls are visualization bounds, not recommended ride settings. The generated SnowDeck CAD package remains bench-study-only and explicitly carries no fabrication or ride authority.


## Synthetic SnowDeck demo now

No physical hardware is required to preview the response-vector UI:

```bash
python tools/prepare_x1_showcase.py --synthetic-snowdeck-demo
python -m http.server 8000
```

Then open `http://localhost:8000/showcase/`.

The response panel is visibly labeled **SYNTHETIC**. The committed example files have:

- `synthetic_fixture=true`;
- `physical_evidence_eligible=false`;
- all fabrication, ride and powered authorities false.

Synthetic response values exist only to exercise the visualization path.

## Real SnowDeck bench overlay later

After Issue #4, Issue #63 and the authorized four-zone Fit Rig are physically complete, keep raw force data private and summarize it locally:

```bash
python tools/summarize_snowdeck_force_log.py \
  rider/private/snowdeck/S1/force.csv \
  --session rider/private/snowdeck/S1/session.json \
  --out rider/private/snowdeck/S1/signature.json

python tools/compare_snowdeck_signatures.py \
  rider/private/snowdeck/S0/signature.json \
  rider/private/snowdeck/S1/signature.json \
  --out rider/private/snowdeck/S1/vs_s0.json

python tools/prepare_x1_showcase.py \
  --snowdeck-signature rider/private/snowdeck/S1/signature.json \
  --snowdeck-comparison rider/private/snowdeck/S1/vs_s0.json
```

The runtime manifest copies only a sanitized aggregate response vector. Session IDs, raw force traces and private notes are not projected into the public viewer contract.


## Design-review snapshot

Every successful `prepare_x1_showcase.py` run now emits:

`showcase/generated/design_review.md`

The snapshot contains:

- component evidence state and exact physical promotion gate;
- the three deck-envelope candidates;
- brake/drive topology branches without collapsing UNKNOWN compatibility;
- the sacrificial trail-armor study boundary;
- optional sanitized SnowDeck response vectors and signed deltas;
- highest-priority mechanical risks;
- the major physical progression gates and their current blockers.

It is generated from the same runtime manifest as the viewer and is explicitly non-authoritative. It is useful for design reviews, archiving decisions, and spotting when a beautiful visualization has outrun physical evidence.


## Physical deck-selection overlay

After the blinded full-scale deck experiment produces a qualified sanitized authority, pass that authority through the normal evidence channel:

```bash
python tools/prepare_x1_showcase.py \
  --evidence rider/private/rev_c_release/deck_comparison_authority.json
```

A fingerprint-valid `x1_rev_c_deck_comparison` authority causes the viewer and generated design review to mark the selected maximum envelope as **PHYSICAL PICK**.

This is an observation only. It does not satisfy `rev_c_chassis_release_qualified`, does not promote the deck/chassis component to QUALIFIED, and does not unlock MEASURE_FIRST procurement.


## Configuration-lab workflow

The viewer now supports reproducible, non-authoritative trade studies.

Recommended loop:

1. Apply a named preset that matches the question you want to inspect.
2. Toggle only the systems relevant to that question.
3. Adjust deck/topology/SnowDeck parameters.
4. Save the state as **A**.
5. Change one design choice and save the new state as **B**.
6. Read the descriptive A/B table and configuration warnings.
7. Use the result to decide which physical measurement or bench test would actually discriminate the two options.

Current preset families include:

- **Brake-first trail core**: brake-first donor reference with inert pack and SnowDeck visible.
- **SnowDeck fit bench**: rider-interface study with drivetrain clutter removed.
- **Drive packaging study**: drive-clearance branch with drive and pack envelopes visible.
- **Brake + drive coexistence question**: intentionally shows both unresolved systems together so interference can be inspected without claiming compatibility.
- **Armor + dock service study**: exposes underside protection and passive alignment geometry.

The A/B table reports reference geometry and compatibility only. It never computes an overall score or winner, and it does not infer ride quality, strength, stopping distance, range, or safety.

The default procedural assembly uses physically legible materials for the board and authority-colored edges/ghost volumes for evidence state. Generated GLB CAD can still be overlaid for geometry audit.
