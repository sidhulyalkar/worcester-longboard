# X1 one-zone pilot: assembly and measurement procedure

This is an **unpowered, bench-only** fixture. The objective is to qualify one load-cell/pod/pad stack, not to stand on it or test ride hardware.

## Mechanical stack

From bottom to top:

```text
rigid bench / sacrificial base
        |
        |  bench clamps / fasteners
        v
130 x 70 x 8 mm pilot carrier
        |
        |  4x auxiliary M4 through-fasteners
        v
pilot load-cell pod
        |
        |  fixed/wire-end M5 interface
        v
Phidgets 3135 single-point load cell
        |
        |  loaded/free-end M5 interface
        v
105 x 78 x 6 mm zone pad
        |
        v
Issue #61 reference mass
```

The auxiliary M4 carrier holes are pilot-only. They do not redefine the four-zone sensor interface.

## 1. Print/machine and inspect

Generate the one-zone package:

```bash
PYTHONPATH=. python cad/generate_one_zone_pilot.py
```

Use the STEP files for machining/CAD inspection and STL files for prototype printing. Inspect every through-hole and verify the pilot authority JSON reports `pilot_cad_ready=true` and `four_zone_duplication_ready=false`.

Printed parts are acceptable for low-load fit-up and calibration screening only if they are rigid, undamaged, and securely fastened. Do not infer ride-structure suitability from this fixture.

## 2. Label the stack

Assign stable IDs to the load cell, HX711, pod, and pad before wiring. Photographing the labels for your private records is useful, but photographs are not required by the public repo.

## 3. Verify the real sensor before tightening

With calipers, confirm the physical cell agrees with the vendor-pattern reference sufficiently to use the pilot CAD. Record the real fixed-hole and loaded-hole centers in the private measurement record.

Identify the wire/fixed end and free/loaded end before assembly. The loaded pad belongs only on the free end.

## 4. Establish the M5 screw stack

Do not select M5 screw length from CAD alone. For each end:

1. measure the thickness of everything the screw passes through;
2. determine actual thread engagement in the physical cell;
3. confirm the screw cannot bottom out or enter a flexure-sensitive region;
4. start with light hand torque and inspect alignment;
5. record the selected screw length in private notes.

Use washers as needed to distribute bearing load, but never bridge or clamp the bending section of the cell.

## 5. Fix the pilot pod to the carrier

Use the four pilot-only M4 through-holes with washers and nyloc nuts or an equivalent positive fastening method. The pod should sit flat with no rocking. Then positively clamp/bolt the carrier to a rigid base through its separate 6.5 mm bench holes.

The load cell should never be the component preventing the entire fixture from sliding across the bench.

## 6. Measure unloaded stop clearance

Before applying test mass, use feeler gauges to measure the smallest air gap between the zone pad underside and overload-stop towers. Record the minimum value, not the prettiest one.

Do not sand or shim the stops merely to make the nominal CAD value appear. If the real gap differs, the measurement wins.

## 7. Wire one sensing path

Connect only the selected load cell to one HX711 channel and the HX711 to the ESP32-S3. Add strain relief so cable motion does not pull the sensor body or solder joints.

Start with the 10 SPS firmware target for static qualification. Confirm the physical RATE configuration agrees with that target and retain the startup header in every captured file.

## 8. Zero and polarity sanity check

With the pad unloaded, record a short raw stream. Apply a small hand force **well below the first calibration mass** and verify counts move consistently rather than rail, jump intermittently, or reverse unexpectedly. Remove the force and verify the signal returns near baseline.

This is only a wiring sanity check. Do not use hand force as qualification evidence.

## 9. Issue #61 reference-mass plateaus

Create and validate the mass-reference set **before** this capture. Follow `docs/x1_fit_pilot_mass_reference.md`.

The private Issue #4 session derives its exact sequence from the fingerprinted `x1_fit_pilot_mass_reference` authority. Do not replace those values with nominal 2/5/10/7.5 kg labels.

For the **Issue #4 calibration itself**, apply each authority-bound mass centrally and repeatably to the zone pad. Capture only settled plateau windows. The initializer orders the calibration loads upward, repeats the appropriate lower loads on the descending path, and then uses the separately identified independent-validation mass.

Every applied mass remains `<=20 kg`.

At the largest pilot mass, measure the **minimum remaining stop clearance** without forcing the pad into the stop.

If a mass value, uncertainty, or evidence source changes, stop and create a new Issue #61 authority and a new Issue #4 session.

After Issue #4 passes, do **not** immediately duplicate four zones. Run Issue #63 using the same assembled one-zone fixture and the same Issue #61 independent validation mass. Issue #63 deliberately moves that validation load to CENTER, +X, -X, +Y, and -Y positions without re-zeroing or recalibrating, verifying that the complete pad/pod/load-cell stack preserves the Issue #4 validation envelope across platform loading. See `docs/x1_fit_platform_repeatability.md`.

## 10. Run authority

```bash
PYTHONPATH=. python tools/qualify_one_zone_pilot.py \
  rider/private/fit_rig/<session>/pilot_manifest.json \
  --out rider/private/fit_rig/<session>/pilot_authority.json
```

A passing Issue #4 report closes the **base one-zone calibration gate**. Four-zone duplication additionally requires Issue #63 platform-repeatability authority through the project build-authority graph. Neither gate authorizes standing on the fixture, rideable CAD, motors, batteries, or powered testing.
