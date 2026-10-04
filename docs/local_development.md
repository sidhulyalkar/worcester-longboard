# Local development environment

Worcester X1 uses Python 3.12 and a repository-local `.venv`.

Do not layer the project `.venv` on top of an active Conda environment. The CAD stack imports native OpenCascade/OCP code, so interpreter provenance matters.

## Known-good package set

`requirements-dev.txt` is the local/CI development contract.

The direct dependencies are pinned to the package versions used by the successful `main` CI run for commit `50f0a7dd593edc3113fdb14046f98e4ebfbe8e76`.

The CadQuery/OCP trio is pinned explicitly because OCP is native code:

- `cadquery==2.8.0`
- `cadquery-ocp==7.9.3.1.1`
- `cadquery-ocp-proxy==7.9.3.1.1`

## Diagnose the currently active environment

From the repository root:

```bash
python tools/check_dev_environment.py
```

A clean local environment should report:

- Python 3.12;
- executable under this repository's `.venv`;
- Conda inactive;
- no Conda-family base interpreter;
- exact pinned package versions;
- successful CadQuery and OCP imports.

The doctor exits nonzero when the local environment contract is violated.

## Repair a Conda-layered or Conda-derived `.venv`

If your prompt shows both:

```text
(.venv) (base)
```

first leave both environments:

```bash
deactivate
conda deactivate
```

If `conda deactivate` still leaves another Conda environment active, repeat it until `(base)` or the Conda environment name disappears.

Then inspect the interpreter you plan to use:

```bash
which python3.12
python3.12 -c "import sys; print(sys.executable); print(sys.base_prefix)"
```

If either path points into Miniconda, Anaconda, Miniforge, Mambaforge, or Micromamba, use a standalone Python 3.12 interpreter instead.

On Apple Silicon with Homebrew:

```bash
brew install python@3.12
```

Then rebuild the repository environment explicitly:

```bash
PYTHON_BIN=/opt/homebrew/bin/python3.12 \
  bash tools/bootstrap_dev_env.sh --recreate
```

If `python3.12` already resolves to a non-Conda Python 3.12:

```bash
bash tools/bootstrap_dev_env.sh --recreate
```

The bootstrap refuses to build from an active or underlying Conda-family interpreter.

## Normal daily activation

```bash
cd /path/to/worcester-longboard
source .venv/bin/activate
python tools/check_dev_environment.py
```

The shell prompt should contain `.venv` but not `(base)`.

## Validate the repository

Run the fast local software validation:

```bash
python -m pip check
python -m compileall -q tools cad fit simulation
python -m pytest -q tests
```

If Node is installed, also parse the browser module:

```bash
cp showcase/app.js /tmp/x1-showcase-app.mjs
node --check /tmp/x1-showcase-app.mjs
```

CI additionally runs the procurement, mechanical, telemetry, firmware, and generated-CAD smoke tests.

## Exercise the digital twin

With the clean `.venv` active:

```bash
python tools/prepare_x1_showcase.py --synthetic-snowdeck-demo
python -m http.server 8000
```

Open:

```text
http://localhost:8000/showcase/
```

This should generate the CAD references, GLB assets, runtime manifest, and `showcase/generated/design_review.md`.

## Start the physical handoff

No additional software setup is required.

For the complete Day-0 physical workspace:

```bash
python tools/init_x1_physical_kickoff.py rider/private/physical_kickoff
```

For only the Rev-C no-parts chassis/deck experiment:

```bash
python tools/init_rev_c_chassis_release_session.py rider/private/rev_c_release
```

The second command creates the blinded A/B/C templates, field sheet, private blind key, and Issue #25 evidence workspace.

Neither command authorizes powered operation or opens a blocked procurement gate.
