# Board Builder

`builder/` is the browser product surface for the generic Worcester Board Builder.

It consumes the versioned data under `configurator/` and `catalog/` and uses `builder/engine.mjs` to derive requirements and generate the same candidate set as the Python planning engine.

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
node --test tests/js/test_board_builder_engine.mjs
```

The full repository validator also checks Python/browser parity.

## Boundary

The Builder generates planning requirements, candidate architecture comparisons, compatibility findings and source-aware BOMs. It does not create procurement, fabrication, charging, ride or powered-operation authority.
