# X1 Fit Rig hardware BOM

This fixture is for **unpowered stance calibration only**. It is not structural riding hardware.

## Core sensing

- 4x single-point load cells, nominal 50 kg class, one per heel/forefoot zone
- 4x HX711-class 24-bit load-cell ADC modules, or one multi-channel instrumentation ADC with equivalent resolution
- 1x ESP32-S3 development board
- 1x 6-axis IMU module for deck roll/pitch/yaw-rate capture
- 1x high-endurance microSD module/card for raw local logging
- optional USB isolator for bench/debug work

The 50 kg per-zone load-cell class is intentionally generous. Dynamic leaning can concentrate much more than one quarter of total body load onto one zone.

## Mechanical fixture

- rigid plywood/aluminum base plate, approximately 700 x 300 mm
- 2x generated adjustable X1 fit footplates
- removable 1, 2, 3 and 4 degree cant wedges from `cad/generate_fit_rig.py`
- M5/M6 fasteners, large washers and nyloc nuts
- thin elastomer anti-slip layer above each footplate
- hard mechanical overload stops around each load cell so a misstep cannot crush the sensor

## Calibration equipment

- one or more accurately known masses totaling roughly 5-15 kg
- digital scale for checking those calibration masses
- ruler/tape and digital calipers
- painter's tape / removable floor markers

## Optional dynamic pose

RuView may be used as an auxiliary pose stream when full CSI hardware is available. X1 treats those coordinates as dynamic-comparison data only; they are not authoritative manufacturing dimensions.

## Electrical notes

Keep the entire fit rig low-voltage and USB/battery powered. No traction battery, motor controller, motor, charger or other high-energy X1 hardware is required for this fixture.

Wire each load cell to its own channel when practical so calibration and sensor faults remain independently observable. Log raw counts as well as converted newtons so calibration can be replayed later.

## Data rates

Suggested starting rates:

- load cells: 40-80 Hz per zone
- deck IMU: 100-200 Hz
- pose: whatever stable rate the source provides
- session metadata: one record per stance/remount trial

Timestamp every stream from the same host clock where possible. Use `fit/session_sync.py` only for post-hoc nearest-neighbor alignment, not to hide large clock errors.
