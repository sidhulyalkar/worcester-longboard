# Worcester X1 Fit Rig v0.3 mechanical build contract

This fixture exists only to measure stance geometry and repeatable force transfer before personalized geometry is moved onto a rideable board. It is **unpowered calibration hardware**, not a structural skateboard component.

## Mechanical stack

Each of the four zones uses the same stack:

1. rigid fixture base,
2. load-cell pod,
3. single-point full-bridge load cell,
4. centered force-transfer button,
5. heel or forefoot zone pad,
6. adjustable footplate above the two zones for that foot.

The four zones remain mechanically and electrically independent:

- left heel,
- left forefoot,
- right heel,
- right forefoot.

Do not bridge the left/right pads together with a rigid plate that bypasses the sensors. The footplate must transfer load through its intended heel/forefoot supports without bottoming on the fixture base during normal calibration.

## Current Rev-A reference dimensions

The public CAD authority currently uses:

- fixture base: 700 x 300 x 12 mm,
- footplate: 260 x 132 x 6 mm,
- zone pad: 105 x 78 x 6 mm,
- load-cell pod: 92 x 38 x 6 mm,
- nominal load-cell envelope: 55.25 x 12.70 x 12.70 mm,
- force-transfer button: 12 mm diameter x 2 mm,
- nominal overload-stop gap: 0.8 mm,
- electronics enclosure: 185 x 125 x 42 mm.

These are prototype fixture dimensions, not a certification or structural-rating claim.

## Measurement-gated sensor interface

The nominal sensor envelope and M5 thread family are known, but the actual threaded-hole centers must be measured on the physical load cells before sensor mounts are treated as fabrication-authoritative.

Coordinate convention:

- origin: geometric center of the load-cell body,
- +x: loaded/free end,
- -x: fixed/wire end,
- +y: across the narrow width,
- units: millimetres.

Record the centers in a private copy of `cad/fit_rig_measurements.example.json`.

Suggested workflow:

```bash
cp cad/fit_rig_measurements.example.json rider/private/fit_rig_measurements.json
# fill only direct caliper measurements
python tools/validate_fit_rig_measurements.py rider/private/fit_rig_measurements.json
python cad/generate_fit_rig.py \
  --measurements rider/private/fit_rig_measurements.json \
  --out rider/private/generated_fit_v03
```

A non-zero exit from the validator means the sensor interface remains measurement-gated.

## Overload protection

The CAD contains hard-stop towers near the loaded end. The nominal 0.8 mm gap is a starting prototype value only. Before a person steps on the fixture:

1. assemble one sensor zone by itself,
2. apply small known loads,
3. confirm the force-transfer pad loads the intended free end without rubbing or side-loading,
4. measure actual deflection and stop clearance,
5. trim/shim the stop height so the cell cannot be crushed by a misstep,
6. verify the stop does not touch during the entire expected calibration load range.

A hard stop is backup protection, not a calibration surface.

## Force-transfer pads

The underside button should contact the intended loaded region of the sensor without introducing a large lateral moment. The first pad is deliberately generic. After the physical sensors arrive, inspect the manufacturer's force-application marking and adjust the button location if needed before full-load use.

## Base and footplate adjustment

The base uses long slots to keep stance width and left/right longitudinal placement adjustable. The fit rig is supposed to discover a repeatable stance, not impose one.

Do not permanently drill the rideable deck from these reference dimensions. Rev-B rider-interface CAD remains blocked until fit-session qualification closes Issue #2 and the private dimensional profile is complete.

## Electronics enclosure

The generated enclosure is a low-voltage packaging reference for:

- ESP32-S3,
- four HX711 boards,
- IMU,
- microSD/logging hardware,
- USB power/data.

The current cable windows are generic. Choose glands/strain reliefs after measuring the actual board stack and cable diameters.

## Assembly-jig purpose

`fit_load_cell_alignment_jig` is a shallow pocket gauge around the nominal sensor envelope. Use it to keep sensor placement repeatable during mock-up and measurement. It does not define threaded-hole coordinates.

## Qualification before a rider uses the rig

- all four cells individually calibrated with a known mass,
- each channel verified with a second independent mass,
- no visible rubbing or preload when unloaded,
- total reconstructed force plausible when standing centrally,
- overload stops verified not to engage during normal loading,
- base cannot rock on the floor,
- footplates cannot slide under expected stance load,
- exposed fasteners cannot contact feet,
- all wiring strain-relieved and kept away from moving interfaces,
- only low-voltage USB/battery electronics present.

If any zone behaves nonlinearly or changes zero after mechanical adjustment, re-zero and recalibrate that zone before collecting fit data.
