# X1 Fit Rig v0.3 interface control document

This document defines which mechanical interfaces are frozen, adjustable, or measurement-gated for the **unpowered** rider-fit fixture.

## Authority classes

- **FROZEN-REFERENCE**: safe to use for mock-up/CAD packaging and fixture fabrication where noted.
- **ADJUSTABLE**: intentionally slotted or shimmed; final rider-specific value is discovered experimentally.
- **MEASUREMENT-GATED**: do not drill/machine from nominal assumptions. Measure the purchased part first.
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
| transfer button | 12 mm diameter x 2 mm nominal | FROZEN-REFERENCE; verify contact |
| load-cell pod | 92 x 38 x 6 mm | FROZEN-REFERENCE |
| overload stop diameter | 10 mm nominal | FROZEN-REFERENCE |
| overload stop gap | 0.8 mm starting value | MEASUREMENT-GATED under real deflection |

The overload stop must not become part of the normal load path. Verify the gap experimentally on one zone before a person uses the full fixture.

## Load-cell interface

Nominal envelope currently used for collision geometry:

- length: 55.25 mm,
- width: 12.70 mm,
- height: 12.70 mm,
- threaded family: M5.

The sensor coordinate frame is:

- origin at geometric center,
- +x toward loaded/free end,
- -x toward fixed/wire end,
- +y across narrow width.

The following remain **MEASUREMENT-GATED**:

- fixed-end hole-center coordinates,
- loaded-end hole-center coordinates,
- actual transfer-button contact position relative to manufacturer's load arrow/marking,
- final overload-stop height.

Use `cad/fit_rig_measurements.example.json`, `tools/validate_fit_rig_measurements.py`, and `cad/generate_fit_rig.py --measurements ...` to close these gates.

## Electronics enclosure

| Interface | Value/status | Authority |
|---|---|---|
| outer reference envelope | 185 x 125 x 42 mm | FROZEN-REFERENCE |
| wall | 3 mm | FROZEN-REFERENCE |
| cable windows | generic reference | MEASUREMENT-GATED to actual glands/cables |
| internal PCB mounting | not frozen | MEASUREMENT-GATED |

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
