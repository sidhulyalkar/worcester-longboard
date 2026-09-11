# X1 Fit Rig v0.3 — one-zone pilot qualification

Before four load-cell pods are duplicated, one physical Phidgets 3135/HX711/pod/pad stack must pass a bench qualification. This is an **unpowered fixture test**. It does not qualify any rideable component.

## Why one zone first

The CAD authority already permits a vendor-pattern pilot but deliberately blocks four-pod fabrication until one real sensor verifies the mechanical stack. The one-zone pilot is where we discover screw engagement, orientation, flexure clearance, stop geometry, wiring polarity, logger health, and calibration behavior at low consequence.

## Evidence contract

Keep physical measurements and raw logs under `rider/private/`. Start from `hardware/one_zone_pilot_manifest.example.json`.

Each load plateau is a separate raw logger CSV. Use the same selected logger channel for every file. The minimum sequence is:

1. unloaded `zero_pre`
2. three or more unique ascending nonzero masses
3. two or more matching descending masses
4. unloaded `zero_post`
5. at least one independent validation mass not used to fit the calibration line

Record at least five seconds of settled data per plateau. Do not include the transient while adding or removing the mass.

## Mechanical checks

Explicitly verify on the real unit:

- vendor body and hole pattern
- fixed/wire end versus loaded/free end
- M5 screw engagement and non-interference with the flexure
- unloaded overload-stop gap
- minimum stop clearance under the largest pilot load

Do not intentionally drive the load cell into the stop to test it. The stop is a protective limit, not a calibration datum.

## Default gates

`fit/pilot_qualification.py` owns the exact values:

- selected-channel coverage >= 98%
- strictly monotonic logger timestamps
- each plateau >= 5 s
- linearity R² >= 0.999
- maximum calibration residual <= 1.0% of pilot full scale
- ascending/descending hysteresis <= 1.5% of pilot full scale
- zero-return error <= 0.5% of pilot full scale
- independent validation error <= 2.0% of applied force
- plateau noise <= 0.5% of pilot full scale
- unloaded stop gap 0.30–2.00 mm
- minimum loaded stop clearance >= 0.15 mm

These are engineering screening limits for this fixture, not manufacturer certification claims.

## Run

```bash
PYTHONPATH=. python tools/qualify_one_zone_pilot.py \
  rider/private/fit_rig/pilot_manifest.json \
  --out rider/private/fit_rig/pilot_authority.json
```

A nonzero exit means four-zone duplication remains blocked. The report stores the metrics, thresholds, failures, SHA-256 of every raw plateau, the manifest SHA-256, and an authority fingerprint.

The only field that opens the next manufacturing gate is:

```json
"qualified_for_four_zone_duplication": true
```

That field must come from real physical evidence. CI proves only that the qualification machinery behaves correctly on synthetic data.
