# X1 Fit Rig v0.3: one-zone pilot qualification

Before four load-cell pods are duplicated, one physical Phidgets 3135/HX711/pod/pad stack must pass a bench qualification. This is an **unpowered fixture test**. It does not qualify any rideable component.

## Why one zone first

The CAD authority permits a vendor-pattern pilot but deliberately blocks four-pod fabrication until one real sensor verifies the mechanical stack. The one-zone pilot is where we discover screw engagement, orientation, flexure clearance, stop geometry, wiring polarity, logger health, and calibration behavior at low consequence.

## Evidence and identity contract

Keep physical measurements and raw logs under one `rider/private/` session directory. Start from `hardware/one_zone_pilot_manifest.example.json`. The qualification tool refuses log paths that escape the manifest directory.

Give the tested stack stable local IDs for its load cell, HX711, pod, and zone pad. The authority report binds those IDs to the source-log hashes, manifest hash, and SHA-256 of the qualification tool itself. Replacing a component therefore requires a new qualification authority rather than inheriting a previous sensor's result.

Every raw plateau must retain the logger startup line `# hx711_sps=<10|80>`. That header must match the manifest, and `acquisition.rate_jumper_verified` must be true only after checking the physical HX711 RATE configuration. The firmware declaration alone cannot prove the jumper state.

Each load plateau is a separate raw logger CSV using the same selected logger channel. The observation sequence must start with `zero_pre`, use strictly increasing `load_up` masses, then strictly decreasing `load_down` masses, and finish with `zero_post`. Use at least three unique ascending masses and at least two paired descending masses. The positive validation mass must be different from every ascending calibration mass.

Record at least five seconds of settled data per plateau. Do not include the transient while adding or removing a mass. The pilot software enforces a hard **20 kg maximum applied calibration/validation mass**. This is a conservative X1 screening ceiling, not the sensor manufacturer's capacity rating.

## Mechanical checks

Explicitly verify the vendor body/hole pattern, fixed versus loaded orientation, M5 engagement without flexure interference, unloaded overload-stop gap, and minimum stop clearance under the largest pilot load. Do not intentionally drive the cell into the stop. The stop is a protective limit, not a calibration datum.

## Default gates

`fit/pilot_qualification.py` owns the canonical limits: selected-channel coverage >=98%; monotonic timestamps; plateau duration >=5 s; R² >=0.999; calibration residual <=1.0% pilot full scale; hysteresis <=1.5% FS; zero-return <=0.5% FS; independent validation error <=2.0%; noise <=0.5% FS; unloaded stop gap 0.30–2.00 mm; loaded stop clearance >=0.15 mm; and no applied pilot mass above 20 kg.

A private manifest may make a threshold stricter, but the software rejects any attempt to relax a canonical gate. These are X1 engineering screening limits, not manufacturer certification claims.

## Run

```bash
PYTHONPATH=. python tools/qualify_one_zone_pilot.py \
  rider/private/fit_rig/pilot_manifest.json \
  --out rider/private/fit_rig/pilot_authority.json
```

A nonzero exit means four-zone duplication remains blocked. The report stores metrics, thresholds, hardware IDs, acquisition/mechanical evidence, SHA-256 of every raw plateau, the manifest hash, qualification-tool hash, and an authority fingerprint.

The only field that opens the next manufacturing gate is:

```json
"qualified_for_four_zone_duplication": true
```

That field must come from real physical evidence. CI proves only that the qualification machinery behaves correctly on synthetic data.
