# Board Builder

`builder/` is the browser product surface for the generic Worcester Board Builder.

It consumes the versioned data under `configurator/` and `catalog/`. `builder/engine.mjs` derives requirements and candidate architectures, while `builder/swap_engine.mjs` powers the component Swap Lab. Both have deterministic Python counterparts and CI parity checks.

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
node --test tests/js/test_board_builder_engine.mjs tests/js/test_board_builder_swap_lab.mjs
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
