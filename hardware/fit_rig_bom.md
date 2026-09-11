# X1 Fit Rig hardware BOM

This fixture is for **unpowered stance calibration only**. It is not structural riding hardware.

## Preferred v0.3 sensing stack

- 5x **Phidgets 3135_0 Single Point Load Cell - 50kg**: four installed + one characterized spare
  - full bridge / 4-wire sensor
  - 50 kg rated capacity, 60 kg maximum overload
  - current mechanical drawing reference: 55 x 12.65 x 12.65 mm body
  - 2x M5x0.8 through holes total, 40 mm center-to-center
  - one end mounts to the rigid base/pod, the opposite end mounts to the top zone pad
- 5x **SparkFun HX711 Load Cell Amplifier** (SEN-13879) or equivalent independent HX711 channels: four installed + one spare
  - one ADC per load cell
  - selectable 10/80 samples per second
  - default hardware state is 10 SPS; 80 SPS requires the breakout RATE configuration to be changed
  - firmware build and physical RATE state must agree
- 1x ESP32-S3 development board
- 1x ICM-42688-P-class 6-axis IMU module for fixture roll/pitch and dynamic comparison
- 1x high-endurance microSD module/card if local logging is desired
- optional USB isolator for bench/debug work

Why independent full-bridge cells: X1 needs four separate force zones. Do not use a bathroom-scale combinator topology that sums multiple half-bridge sensors into one total-weight channel; that would destroy the left-heel / left-forefoot / right-heel / right-forefoot information.

## Mechanical fixture

- rigid base plate, approximately 700 x 300 mm
- 2x generated adjustable X1 fit footplates
- 4x independent heel/forefoot zone pads
- 4x load-cell pods
- removable 1, 2, 3 and 4 degree cant wedges from `cad/generate_fit_rig.py`
- M5 hardware for the load-cell interfaces, with screw length selected from the actual pilot stack
- M5/M6 fixture hardware, large washers/backing plates and nyloc nuts as appropriate
- thin elastomer anti-slip layer above each footplate
- hard mechanical overload stops around each load cell
- printed load-cell alignment jig

The current v0.3 design does **not** use a separate force-transfer button. Each 3135 is used in its intended single-point arrangement: fixed/wire end attached to the pod, loaded/free end attached directly to its zone pad.

## Pilot-before-duplicate rule

The vendor drawing is sufficient to make one pilot pod/pad pair. Before producing four final force zones:

1. verify one purchased 3135 body/hole pattern and fixed-versus-loaded orientation,
2. verify screw lengths do not bottom or interfere with flexure,
3. apply known loads and confirm monotonic response/zero return,
4. verify overload-stop clearance under the intended calibration range,
5. only then duplicate the mechanical stack.

## Calibration equipment

- one or more accurately known masses totaling roughly 5-15 kg
- digital scale for checking calibration masses
- ruler/tape and digital calipers
- painter's tape / removable floor markers

## Optional dynamic pose

RuView may be used as an auxiliary pose stream when suitable CSI hardware is available. X1 treats its pose data as dynamic-comparison information only, not as authoritative manufacturing dimensions or a board-control source.

## Electrical notes

Keep the entire fit rig low-voltage and USB/battery powered. No traction battery, motor controller, motor, charger or other high-energy X1 hardware is required.

Use one full-bridge load cell per HX711 channel so every zone can be calibrated and fault-checked independently. Log raw counts as well as converted newtons so calibration can be replayed later.

Suggested HX711 wiring convention per zone:

- load-cell excitation+ -> HX711 E+
- load-cell excitation- -> HX711 E-
- load-cell signal+ -> HX711 A+
- load-cell signal- -> HX711 A-
- HX711 DATA/CLOCK -> dedicated ESP32-S3 GPIO pair

Never rely on wire color alone; verify the selected sensor documentation before wiring.

## Acquisition modes

Use two explicit modes rather than an ambiguous intermediate rate:

- **10 SPS**: static zero, known-mass calibration and drift characterization
- **80 SPS**: remount, lean and dynamic pose/IMU comparison

The repository compiles separate PlatformIO environments for both modes. The logger prints its configured rate in the session header, and the physical HX711 RATE jumper/configuration must match it.

## Reference sources

- Phidgets 3135_0: https://www.phidgets.com/?prodid=226
- SparkFun HX711 SEN-13879: https://www.sparkfun.com/sparkfun-load-cell-amplifier-hx711.html
