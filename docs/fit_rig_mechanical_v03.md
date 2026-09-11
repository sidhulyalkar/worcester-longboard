# Worcester X1 Fit Rig v0.3 mechanical build contract

This fixture exists only to measure stance geometry and repeatable force transfer before personalized geometry is moved onto a rideable board. It is **unpowered calibration hardware**, not a structural skateboard component.

## Mechanical stack

Each of the four zones uses the same single-point-scale arrangement:

1. rigid fixture base,
2. load-cell pod,
3. fixed/wire end of one single-point full-bridge load cell bolted to the pod,
4. loaded/free end of that load cell bolted directly to the heel or forefoot zone pad,
5. adjustable footplate supported by the two independent zones for that foot.

This matches the intended single-point load-cell installation pattern: one end secured to the base and the other end secured to the top plate. There is no separate force-transfer button in the current v0.3 architecture.

The four zones remain mechanically and electrically independent:

- left heel,
- left forefoot,
- right heel,
- right forefoot.

Do not bridge the force zones together with a rigid bypass structure. The footplate must transfer load through its intended heel/forefoot supports without bottoming on the fixture base during normal calibration.

## Current Rev-A reference dimensions

The public CAD authority currently uses:

- fixture base: 700 x 300 x 12 mm,
- footplate: 260 x 132 x 6 mm,
- zone pad: 105 x 78 x 6 mm,
- load-cell pod: 92 x 38 x 6 mm,
- Phidgets 3135 vendor body reference: 55 x 12.65 x 12.65 mm,
- sensor holes: 2x M5x0.8 THRU, 40 mm center-to-center,
- nominal overload-stop gap: 0.8 mm,
- electronics enclosure: 185 x 125 x 42 mm.

These are prototype fixture dimensions, not a certification or structural-rating claim.

## Vendor pattern vs physical verification

The current Phidgets 3135 mechanical drawing is now sufficient to define a **one-zone pilot**: two M5 through holes total, separated by 40 mm. In X1's sensor coordinate frame the reference centers are `(-20, 0)` and `(20, 0)` mm.

Coordinate convention:

- origin: geometric center of the load-cell body,
- +x: loaded/free end,
- -x: fixed/wire end,
- +y: across the narrow width,
- units: millimetres.

Before duplicating four final pods, verify one purchased sensor against the vendor pattern with calipers and inspect which physical end carries the cable/load arrow.

Suggested workflow:

```bash
cp cad/fit_rig_measurements.example.json rider/private/fit_rig_measurements.json
# enter one physical sensor's measured fixed and loaded hole centers
python tools/validate_fit_rig_measurements.py rider/private/fit_rig_measurements.json
python cad/generate_fit_rig.py \
  --measurements rider/private/fit_rig_measurements.json \
  --out rider/private/generated_fit_v03
```

Without the private verification file, the generator still emits a vendor-pattern pilot pod but the authority report keeps four-pod replication gated.

## Overload protection

The CAD contains hard-stop towers near the loaded end. The nominal 0.8 mm gap is only a starting prototype value. Before a person steps on the fixture:

1. assemble one sensor zone by itself,
2. apply small known loads,
3. confirm the top pad is supported by the intended loaded sensor end without rubbing or side-loading,
4. measure actual deflection and stop clearance,
5. trim/shim the stop height so a misstep cannot grossly overload the cell,
6. verify the stop does not touch during the entire intended calibration load range.

A hard stop is backup protection, not part of the normal calibrated load path.

## Zone pads

The zone pad is bolted to the loaded/free end of the single-point cell. The pilot CAD uses the vendor hole pattern. Screw length, washer stack and any spacer must be selected from the actual printed/machined pad + physical sensor stack so the fastener does not bottom improperly or interfere with sensor flexure.

## Base and footplate adjustment

The base uses long slots to keep stance width and left/right longitudinal placement adjustable. The fit rig is supposed to discover a repeatable stance, not impose one.

Do not permanently drill the rideable deck from these reference dimensions. Rev-B rider-interface CAD remains blocked until fit-session qualification closes Issue #2 and the private dimensional profile is complete.

## Electronics enclosure

The generated enclosure is a low-voltage packaging reference for ESP32-S3, four HX711 boards, IMU, optional microSD and USB power/data. The cable windows are generic; choose final strain relief after measuring the actual board stack and cable diameters.

## Assembly-jig purpose

`fit_load_cell_alignment_jig` is a shallow pocket gauge around the vendor sensor envelope. Use it to keep placement repeatable during the one-zone pilot and physical verification. It does not override the current vendor mechanical drawing or physical measurements.

## Qualification before a rider uses the rig

- one pilot zone physically verifies the vendor hole pattern,
- all four final cells individually calibrated with a known mass,
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
