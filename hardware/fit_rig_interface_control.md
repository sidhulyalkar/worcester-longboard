# X1 Fit Rig v0.3 interface control document

This document defines which mechanical interfaces are frozen, adjustable, vendor-authoritative, or physically verification-gated for the **unpowered** rider-fit fixture.

## Authority classes

- **FROZEN-REFERENCE**: safe to use for mock-up/CAD packaging and fixture fabrication where noted.
- **VENDOR-AUTHORITY**: taken from the current component mechanical drawing and suitable for a one-zone pilot.
- **ADJUSTABLE**: intentionally slotted or shimmed; final rider-specific value is discovered experimentally.
- **PHYSICAL-VERIFY**: check one purchased component before duplicating the interface four times.
- **PRIVATE-FIT**: rider-specific result stored under `rider/private/`, never committed to public Git history.

## Base fixture

| Interface | Value/status | Authority |
|---|---|---|
| base envelope | 700 x 300 x 12 mm | FROZEN-REFERENCE |
| left/right station nominal x | ±180 mm | FROZEN-REFERENCE |
| stance station longitudinal slot | 150 x 6.5 mm | ADJUSTABLE |
| footplate rail spacing | y = ±42 mm | FROZEN-REFERENCE |
| electronics mount | generic slotted reference | ADJUSTABLE |

The base is a calibration fixture. Material/thickness may be increased if the chosen panel is not rigid enough; do not reduce stiffness merely to match the CAD envelope.

## Footplates

| Interface | Value/status | Authority |
|---|---|---|
| plate envelope | 260 x 132 x 6 mm | FROZEN-REFERENCE |
| base track slots | 105 x 6.5 mm | ADJUSTABLE |
| binding slots | 34 x 6.5 mm | ADJUSTABLE |
| cant | 0°, 1°, 2°, 3°, 4° shims | ADJUSTABLE / PRIVATE-FIT |
| left/right yaw | measured during fit sessions | PRIVATE-FIT |
| left/right lateral offset | measured during fit sessions | PRIVATE-FIT |
| final stance width | measured during fit sessions | PRIVATE-FIT |

## Four force zones

Each foot has heel and forefoot zones. Every zone is mechanically independent.

| Interface | Value/status | Authority |
|---|---|---|
| zone pad envelope | 105 x 78 x 6 mm | FROZEN-REFERENCE |
| zone-pad attachment | one M5 clearance hole to loaded sensor end | VENDOR-AUTHORITY / PHYSICAL-VERIFY |
| load-cell pod | 92 x 38 x 6 mm | FROZEN-REFERENCE |
| pod attachment | one M5 clearance hole to fixed sensor end | VENDOR-AUTHORITY / PHYSICAL-VERIFY |
| overload stop diameter | 10 mm nominal | FROZEN-REFERENCE |
| overload stop gap | 0.8 mm starting value | PHYSICAL-VERIFY under real deflection |

There is no separate force-transfer button in the current architecture. The single-point sensor itself is the compliant connection between pod and top pad.

## Load-cell interface

Current Phidgets 3135_0 vendor drawing reference:

- body: 55 x 12.65 x 12.65 mm,
- 2x M5x0.8 through holes total,
- 40 mm hole-center spacing,
- reference sensor-frame coordinates: fixed/wire hole `(-20, 0)` mm, loaded/free hole `(20, 0)` mm.

The sensor coordinate frame is:

- origin at geometric center,
- +x toward loaded/free end,
- -x toward fixed/wire end,
- +y across narrow width.

**One-zone pilot authority:** the vendor drawing is sufficient to generate and fabricate one pilot pod/pad pair.

**Four-zone duplication gate:** before making four final pods, verify one purchased sensor's hole centers and actual cable/fixed-end orientation, then check real overload-stop clearance under small known loads.

Use `cad/fit_rig_measurements.example.json`, `tools/validate_fit_rig_measurements.py`, and `cad/generate_fit_rig.py --measurements ...` to record that verification.

## Electronics enclosure

| Interface | Value/status | Authority |
|---|---|---|
| outer reference envelope | 185 x 125 x 42 mm | FROZEN-REFERENCE |
| wall | 3 mm | FROZEN-REFERENCE |
| cable windows | generic reference | PHYSICAL-VERIFY to actual glands/cables |
| internal PCB mounting | not frozen | PHYSICAL-VERIFY |

Because this fixture is low-voltage, packaging priority is strain relief, connector accessibility and clean sensor wiring rather than environmental sealing.

## Rev-B rider-interface handoff

No rideable-board binding geometry is frozen by this ICD. Rev-B is opened only after:

1. direct left/right foot dimensions exist,
2. natural yaw and stance width are repeatable,
3. >=3 full remount trials exist for the selected stance,
4. four-zone load repeatability is acceptable,
5. neutral fixture roll is acceptably small/repeatable,
6. subjective comfort is explicitly accepted,
7. Issue #2 exit criteria are satisfied.

Truck geometry remains symmetric by default throughout this fit phase.
