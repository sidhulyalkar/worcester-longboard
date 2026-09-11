# X1 Fit Rig v0.3 prototype cut list

This is a low-voltage, unpowered calibration fixture. Dimensions below are prototype starting dimensions and should be checked against generated CAD and physical components before fabrication.

## Panel / printed parts

| Qty | Part | Nominal size / source | Suggested prototype process |
|---:|---|---|---|
| 1 | rigid fixture base | 700 x 300 x 12 mm | flat birch plywood, tooling plate, or similarly rigid panel |
| 2 | universal footplate | `cad/generate_fit_rig.py` | PETG/nylon mock-up or machined polymer/aluminum after fit check |
| 4 | heel/forefoot zone pad | 105 x 78 x 6 mm | print one pilot first, then duplicate after sensor verification |
| 4 | load-cell pod | 92 x 38 x 6 mm | print one pilot first, then duplicate after sensor verification |
| 8 | overload-stop tower | integrated into pod CAD | integrated print/machining + shim as needed |
| 1 | electronics enclosure | 185 x 125 x 42 mm ref | printed enclosure |
| 1 | load-cell alignment jig | generated CAD | printed |
| 2 each | 1°, 2°, 3°, 4° cant wedge | generated CAD | printed |

## Load-cell mechanical interface

The current Phidgets 3135_0 vendor drawing defines a 55 x 12.65 x 12.65 mm body with **two M5x0.8 through holes total at 40 mm center spacing**. X1 models the fixed/wire-end hole at `(-20, 0)` mm and the loaded/free-end hole at `(20, 0)` mm in the sensor frame.

The pilot zone therefore uses:

- one M5 fastener through the pod into the fixed/wire end,
- one M5 fastener through the zone pad into the loaded/free end,
- no separate force-transfer button.

Use the vendor pattern to print/machine **one** pilot zone. Verify one purchased sensor with calipers and check overload-stop clearance before duplicating all four final pods/pads.

## Mechanical hardware

Start with metric hardware appropriate for repeated bench adjustment.

- M5 socket-head screws for the two load-cell interfaces; exact length selected after the pilot stack is measured
- M5 flat washers where they do not interfere with sensor flexure
- M5/M6 washers and nyloc nuts for fixture through-bolting as appropriate
- M6-class hardware for high-cycle footplate/base adjustment if using the 6.5 mm slots
- large-diameter washers or small backing plates under slotted panel fasteners
- threaded inserts/T-nuts only where they cannot bypass or preload a sensor load path
- thin non-slip elastomer sheet for the top of footplates
- thin shim stock for overload-stop tuning
- mechanical cable strain relief at the electronics box

## Sensor stack

Per `hardware/fit_rig_bom.md`:

- 4x Phidgets 3135_0 50 kg-class independent full-bridge single-point load cells
- 4x independent HX711-class ADC boards
- 1x ESP32-S3 development board
- 1x ICM-42688-P-class 6-axis IMU module
- 1x high-endurance microSD module/card if raw local logging is used

Recommended first-build spares:

- +1 load cell
- +1 HX711 board
- +1 set of critical mounting screws/washers

## Wire / interconnect

- four short, independently labeled load-cell harnesses
- separate DATA and CLOCK pair from each HX711 to the ESP32-S3
- short I2C harness for IMU
- USB cable with strain relief for development power/data
- low-voltage locking connectors if the force zones need to be removable
- heat-shrink, ferrules/crimps as appropriate, abrasion sleeve, cable labels

## Build order

1. Cut and verify the flat 700 x 300 mm base.
2. Print one pod, one zone pad and one alignment jig.
3. Fit one purchased 3135 into the jig and verify the vendor 40 mm two-hole pattern and fixed/loaded orientation.
4. Record that physical check in `rider/private/fit_rig_measurements.json`.
5. Run `tools/validate_fit_rig_measurements.py`.
6. Regenerate the verified CAD.
7. Assemble **one** complete force zone using one fastener per sensor end.
8. Verify monotonic/linear response, zero return, absence of rubbing and overload-stop clearance with known masses.
9. Only then duplicate that validated zone three more times.
10. Add both adjustable footplates and the electronics enclosure after all four zones pass individual calibration.
11. Run a no-rider central-load test before collecting stance data.

## Do not bulk-fabricate yet

The vendor drawing is sufficient for the one-zone pilot, but do not produce four final sensor pods or freeze the overload-stop height without checking a physical cell. The pilot exists to expose stack-up, screw-length, flexure-clearance and printing/machining tolerances cheaply.
