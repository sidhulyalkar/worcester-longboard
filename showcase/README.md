# X1 Showcase

Local authority-aware visualization scaffold for Worcester X1.

## Run

From the repository root:

```bash
python tools/build_showcase_manifest.py
python -m http.server 8000
```

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
