# X1 Fit Rig hardware BOM

This fixture is for **unpowered stance calibration only**. It is not structural riding hardware.

## Preferred v0.3 sensing stack

- 4x **Phidgets 3135_0 Single Point Load Cell - 50kg**, one per heel/forefoot zone
  - full bridge / 4-wire sensor
  - 50 kg rated capacity, 60 kg maximum overload
  - approximately 55.25 x 12.7 x 12.7 mm
  - M5 mounting holes
  - 5 V excitation
- 4x **SparkFun HX711 Load Cell Amplifier** (SEN-13879) or equivalent independent HX711 channels
  - one ADC channel per load cell
  - selectable 10/80 SPS
  - standard 4-wire Wheatstone-bridge input
- 1x ESP32-S3 development board
- 1x 6-axis IMU module for fixture/deck roll, pitch and yaw-rate capture
- 1x high-endurance microSD module/card for raw local logging
- optional USB isolator for bench/debug work

Why independent full-bridge cells: X1 needs four separate force zones. Do not use a bathroom-scale combinator topology that sums multiple half-bridge sensors into one total weight channel; that would destroy the left-heel / left-forefoot / right-heel / right-forefoot information we care about.

The 50 kg per-zone capacity is intentionally generous. Dynamic leaning can concentrate far more than one quarter of total body load onto a single zone.

## Mechanical fixture

- rigid plywood/aluminum base plate, approximately 700 x 300 mm
- 2x generated adjustable X1 fit footplates
- removable 1, 2, 3 and 4 degree cant wedges from `cad/generate_fit_rig.py`
- M5/M6 fasteners, large washers and nyloc nuts
- thin elastomer anti-slip layer above each footplate
- hard mechanical overload stops around each load cell so a misstep cannot crush the sensor
- load-spreading button/pad geometry that applies force through the intended sensing region without side-loading the cell

## Calibration equipment

- one or more accurately known masses totaling roughly 5-15 kg
- digital scale for checking those calibration masses
- ruler/tape and digital calipers
- painter's tape / removable floor markers

## Optional dynamic pose

RuView may be used as an auxiliary pose stream when full CSI hardware is available. Current RuView deployments expose a 17-keypoint pose API. X1 treats those coordinates as dynamic-comparison data only; they are not authoritative manufacturing dimensions.

## Electrical notes

Keep the entire fit rig low-voltage and USB/battery powered. No traction battery, motor controller, motor, charger or other high-energy X1 hardware is required for this fixture.

Use one full-bridge load cell per HX711 channel so every force zone can be calibrated and fault-checked independently. Log raw counts as well as converted newtons so calibration can be replayed later.

Suggested HX711 wiring convention per zone:

- load-cell excitation+ -> HX711 E+
- load-cell excitation- -> HX711 E-
- load-cell signal+ -> HX711 A+
- load-cell signal- -> HX711 A-
- HX711 DATA/CLOCK -> dedicated ESP32-S3 GPIO pair

Never rely on wire color alone; verify the selected sensor datasheet before wiring.

## Data rates

Suggested starting rates:

- load cells: 40-80 Hz per zone
- fixture IMU: 100-200 Hz
- pose: whatever stable rate the source provides
- session metadata: one record per stance/remount trial

Timestamp every stream from the same host clock where possible. Use `fit/session_sync.py` only for post-hoc nearest-neighbor alignment, not to hide large clock errors.

## Reference sources

- Phidgets 3135_0: https://www.phidgets.com/?prodid=226
- SparkFun HX711 SEN-13879: https://www.sparkfun.com/sparkfun-load-cell-amplifier-hx711.html
