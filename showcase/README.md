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

## Optional evidence index

By default every physical gate is closed.

A local evidence index may be passed explicitly:

```bash
python tools/build_showcase_manifest.py \
  --evidence-index /path/to/private/showcase_evidence_index.json
```

Example structure:

```json
{
  "fit_pilot_qualified": {
    "qualified": true,
    "authority": "x1_one_zone_pilot",
    "authority_fingerprint_sha256": "..."
  }
}
```

The builder checks the expected authority name where one is defined and refuses any supplied evidence that claims powered operation.

Do not commit private rider measurements or raw fit logs to `showcase/`.
