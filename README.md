# Worcester X1

Experimental off-road electric mountainboard platform focused on controllability, instrumentation, redundant braking, terrain-aware ride control, and rider-specific fit.

> **Status:** Alpha engineering prototype. Hardware and firmware are not yet qualified for riding. Commission from an unpowered rolling chassis through bench and walking-speed gates before enabling higher modes.

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

- `cad/` parametric custom-part source, including the unpowered adjustable fit rig
- `firmware/` supervisory controller and VESC CAN integration
- `simulation/` gearing, speed, force and grade sizing
- `docs/` architecture, electrical, fit and commissioning rationale
- `fit/` generic rider profile, left/right stance optimization and load analysis
- `rider/` public schemas only; personal data belongs under gitignored `rider/private/`
- `bom/` procurement notes
- `tools/` commissioning, measurement gates and private-profile utilities

## Design philosophy

Use proven commercial hardware for safety-critical load paths where practical, then innovate in sensing, control, packaging, fit and telemetry. Generated CAD artifacts are treated as build outputs; interface dimensions that are not published by a vendor remain measurement-gated.

## Current validation

```bash
python simulation/x1_dynamics.py
python -m pytest -q tests

g++ -std=c++17 -O2 -Ifirmware/include \
  firmware/src/x1_control_core.cpp firmware/test/test_control_core.cpp \
  -o /tmp/x1_control_test && /tmp/x1_control_test
```

GitHub Actions runs the same dynamics, full Python test suite and host controller-core test on every push and pull request.

## Rider fit

X1 does not assume bilateral symmetry. The generic fit layer supports independent left/right foot dimensions, natural yaw, position and removable cant shims while keeping steering geometry symmetric by default. The stance optimizer is measurement-gated: shoe-size labels are never converted into manufacturing dimensions.

`cad/generate_fit_rig.py` creates an **unpowered** universal footplate and removable 1–4 degree wedges for stance experiments. These parts are calibration fixtures, not structural riding hardware.

The four-zone load analysis preserves observed asymmetry and evaluates repeatability rather than forcing the rider toward a 50/50 load split. Exact rider measurements, medical information, raw body scans and pose recordings are intentionally excluded from the public repository.

## Safety boundary

This repository is an engineering development workspace, not a certification. High-current battery construction belongs with a qualified pack builder. Maintain an independent mechanical braking path, use progressive commissioning, and treat all software limits as secondary to hard electrical/mechanical safety limits.
