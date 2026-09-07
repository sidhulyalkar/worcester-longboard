# Worcester X1

Experimental off-road electric mountainboard platform focused on controllability, instrumentation, redundant braking, and terrain-aware ride control.

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
- privacy-preserving adjustable rider-fit subsystem

## Repository map

- `cad/` parametric custom-part source
- `firmware/` supervisory controller and VESC CAN integration
- `simulation/` gearing, speed, force and grade sizing
- `docs/` architecture, electrical and commissioning rationale
- `fit/` generic adjustable rider-fit schema and load calibration
- `bom/` procurement notes
- `tools/` commissioning and measurement gates

## Design philosophy

Use proven commercial hardware for safety-critical load paths where practical, then innovate in sensing, control, packaging, fit and telemetry. Generated CAD artifacts are treated as build outputs; interface dimensions that are not published by a vendor remain measurement-gated.

## Current validation

```bash
python simulation/x1_dynamics.py
python -m pytest -q tests/test_fit_tools.py

g++ -std=c++17 -O2 -Ifirmware/include \
  firmware/src/x1_control_core.cpp firmware/test/test_control_core.cpp \
  -o /tmp/x1_control_test && /tmp/x1_control_test
```

## Rider fit

X1 does not require a perfectly symmetric stance. The generic fit layer supports independent binding position, yaw, lateral offset and removable cant shims while keeping steering geometry symmetric by default. Exact rider measurements and raw scans are intentionally excluded from the public repository.

## Safety boundary

This repository is an engineering development workspace, not a certification. High-current battery construction belongs with a qualified pack builder. Maintain an independent mechanical braking path, use progressive commissioning, and treat all software limits as secondary to hard electrical/mechanical safety limits.
