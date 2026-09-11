# Worcester X1

Experimental off-road electric mountainboard platform focused on controllability, instrumentation, redundant braking, terrain-aware ride control, and rider-specific fit.

> **Status:** Alpha engineering prototype. Hardware and firmware are not yet qualified for riding. Current physical priority is the low-voltage, unpowered X1 Fit Rig v0.3 before personalized rideable geometry is frozen.

## Alpha architecture

- rear 2WD sealed 7:1 spur drivetrain
- dual 6376 160 KV motors
- two independent VESC 6/75 controllers
- 8-inch pneumatic wheels
- independent front hydraulic braking
- professionally assembled 14S4P battery target
- ESP32-S3 supervisory ECU
- front-wheel speed sensing for rear slip estimation
- traction-control / regen-slip prototype
- privacy-preserving asymmetric rider-fit subsystem

## Repository map

- `cad/` parametric custom-part source and fit-rig geometry authority
- `firmware/` supervisory controller, VESC CAN integration, and fit-rig ESP32 logger
- `simulation/` gearing, speed, force and grade sizing
- `docs/` architecture, electrical, fit and commissioning rationale
- `fit/` rider profile, raw-log quality, force calibration, stance scoring, Rev-B gates, stream synchronization and optional pose adapters
- `hardware/` low-voltage fit-rig BOM, wiring, cut list and interface-control notes
- `rider/` public schemas only; personal data belongs under gitignored `rider/private/`
- `bom/` drivetrain/power procurement notes
- `tools/` commissioning, capture, calibration, quality, measurement-gate and private-profile utilities

## Design philosophy

Use proven commercial hardware for safety-critical load paths where practical, then innovate in sensing, control, packaging, fit and telemetry. Generated CAD artifacts are build outputs; component interfaces must have an explicit authority source instead of being inferred from approximate product dimensions.

## Current validation

GitHub Actions currently validates:

```text
vehicle dynamics model
full Python fit/calibration/end-to-end suite
host C++ vehicle-control core
ESP32-S3 fit-rig logger at 10 SPS
ESP32-S3 fit-rig logger at 80 SPS
CadQuery generation of fit-rig STEP/STL reference artifacts
CAD authority assertions
```

## X1 Fit Rig v0.3

The fit rig is an **unpowered** four-zone measurement fixture:

```text
left heel      left forefoot      right heel      right forefoot
    |                |                 |                 |
  3135             3135              3135              3135
    |                |                 |                 |
  HX711             HX711             HX711             HX711
     \                \                /                 /
                       ESP32-S3
                         |
                   fixture IMU
```

Each force zone uses one independent 50 kg-class full-bridge single-point cell. The current Phidgets 3135 vendor drawing defines a 55 x 12.65 x 12.65 mm body, two M5x0.8 through holes total, and 40 mm hole-center spacing. One end bolts to the rigid pod and the opposite end bolts directly to the top zone pad.

The vendor pattern is enough for **one pilot zone**. Four final pods remain gated on physical verification of one purchased sensor plus real overload-stop clearance.

`cad/generate_fit_rig.py` produces the base, universal footplate, independent zone pad, one-hole-per-end load-cell pod, sensor reference, alignment jig, electronics enclosure and removable 1–4 degree cant wedges.

## Measurement pipeline

The fit pipeline is intentionally provenance-heavy:

```text
raw ESP32 log
    -> raw coverage/timing quality
    -> per-zone known-mass calibration
    -> calibrated force + roll trial
    -> >=3 remount trial summaries
    -> repeatability score
    -> Rev-B data/measurement gate
    -> private personalized CAD input
```

Raw logs carry a four-bit `load_valid_mask`; one missing HX711 cannot freeze the remaining channels. The current Rev-B gate requires monotonic timestamps, >=20 s raw duration per qualifying trial, >=98% complete four-force-channel coverage, >=95% IMU coverage, direct dimensional measurements, and repeatable stance statistics.

Stable left/right loading differences are preserved as observations rather than forced toward 50/50.

## Rider-fit boundary

X1 does not assume bilateral symmetry. The generic fit layer supports independent left/right foot dimensions, natural yaw, position and removable cant shims while keeping truck geometry symmetric by default.

Shoe-size labels are never converted into manufacturing dimensions. Exact rider measurements, medical information, raw body scans, CSI captures and pose recordings are intentionally excluded from public Git history.

RuView-style Wi-Fi pose may be captured as optional dynamic-comparison data. It is explicitly non-authoritative for metric CAD and cannot command the board.

## Tracked milestones

- Issue #2: build and qualify X1 Fit Rig v0.3
- Issue #3: generate measurement-qualified Rev-B rider-interface CAD, blocked by #2

## Safety boundary

This repository is an engineering development workspace, not a certification. The fit rig stays low-voltage and unpowered. High-current traction-battery construction belongs with a qualified pack builder. The eventual powered board retains an independent mechanical braking path and progressive commissioning gates; software limits remain secondary to hard electrical/mechanical safety limits.
