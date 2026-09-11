# X1 Fit Rig v0.3 prototype cut list

This is a low-voltage, unpowered calibration fixture. Dimensions below are prototype starting dimensions and should be checked against generated CAD and physical components before fabrication.

## Panel / printed parts

| Qty | Part | Nominal size / source | Suggested prototype process |
|---:|---|---|---|
| 1 | rigid fixture base | 700 x 300 x 12 mm | flat birch plywood, tooling plate, or similarly rigid panel |
| 2 | universal footplate | `cad/generate_fit_rig.py` | PETG/nylon mock-up or machined polymer/aluminum after fit check |
| 4 | force zone pad | 105 x 78 x 6 mm | printed or machined |
| 4 | load-cell pod | 92 x 38 x 6 mm | printed mock-up; final holes only after measurement gate |
| 8 | overload-stop tower | integrated into pod CAD | integrated print/machining + shim as needed |
| 1 | electronics enclosure | 185 x 125 x 42 mm ref | printed enclosure |
| 1 | load-cell alignment jig | generated CAD | printed |
| 2 each | 1°, 2°, 3°, 4° cant wedge | generated CAD | printed |

## Mechanical hardware

Start with stainless or zinc-plated metric hardware appropriate for repeated bench adjustment.

- M5 socket-head screws for load-cell mounting, length selected only after physical stack measurement
- M5 flat washers and nyloc nuts for fixture hardware where through-bolting is used
- M6 hardware for high-cycle footplate/base adjustment if the generated slot geometry is revised to 6.5 mm clearance
- large-diameter washers or small backing plates under slotted panel fasteners
- threaded inserts/T-nuts only where they cannot interfere with sensor load paths
- thin non-slip elastomer sheet for top of footplates
- optional thin shim stock for overload-stop tuning
- adhesive cable tie mounts only as secondary cable retention; use mechanical strain relief at the electronics box

## Sensor stack

Per `hardware/fit_rig_bom.md`:

- 4x 50 kg-class independent full-bridge single-point load cells
- 4x independent HX711-class ADC boards
- 1x ESP32-S3 development board
- 1x ICM-42688-P-class 6-axis IMU module
- 1x high-endurance microSD module/card if raw local logging is used

Recommended spares for first build:

- +1 load cell
- +1 HX711 board
- +1 set of critical mounting screws/washers

## Wire / interconnect

- four short shielded or tightly routed load-cell harnesses as practical
- separate DATA and CLOCK pair from each HX711 to the ESP32-S3
- short I2C harness for IMU
- USB cable with strain relief for development power/data
- low-voltage locking connectors if the foot zones need to be removable
- heat-shrink, ferrules/crimps as appropriate, abrasion sleeve, cable labels

## Build order

1. Cut/verify the flat base.
2. Print one pod, one zone pad and one alignment jig before producing all four.
3. Place an actual load cell in the jig and measure its threaded-hole centers.
4. Record coordinates in a private measurement file.
5. Run `tools/validate_fit_rig_measurements.py`.
6. Regenerate measured CAD.
7. Build and calibrate **one** complete force zone.
8. Verify linear response, zero return, absence of rubbing and overload-stop clearance.
9. Only then duplicate the validated zone three more times.
10. Add footplates and electronics after all four zones pass individual calibration.

## Do not bulk-fabricate yet

Do not produce four final sensor pods, drill final sensor holes, or commit to the final overload-stop height from nominal CAD alone. The one-zone prototype exists specifically to discover those mechanical tolerances cheaply.
