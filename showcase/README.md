# X1 Showcase

Local authority-aware visualization scaffold for Worcester X1.

## Run

From the repository root:

```bash
python tools/prepare_x1_showcase.py
python -m http.server 8000
```

The preparation command runs the rolling-chassis, Fit Rig, one-zone and SnowDeck CAD generators, converts generated STL references to GLB, then builds the authority-aware runtime manifest. Use `--skip-cad` or `--skip-assets` when iterating only on evidence/UI state.

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
