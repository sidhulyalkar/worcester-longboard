# Worcester X1 current development authority

## Purpose

This document describes the **current engineering direction** for Worcester X1. It replaces the original “frozen Alpha v0.1” hardware table as the human-readable design authority.

The original TRAMPA/14S architecture remains useful historical exploration, but it is no longer the current purchase or fabrication plan.

## Authority precedence

When two repository artifacts disagree, use the following precedence:

1. real, fingerprinted physical qualification evidence;
2. `hardware/build_authority.json`;
3. `hardware/procurement_manifest.json`;
4. current component/geometry authority documents and generated reports;
5. historical Alpha notes and packaging snapshots.

A public CI pass proves software behavior only. It never proves that a physical sensor, brake, chassis, battery, or rider interface has been measured or qualified.

## Mission

Build a trail-first mountainboard that prioritizes low-speed control, predictable stopping, serviceability, rider-specific fit, and inspectable evidence over headline speed.

The project should minimize expensive re-buys by freezing interfaces in the order that physical evidence becomes available.

## Current mechanical reference

| Subsystem | Current status |
|---|---|
| Chassis sourcing | MBS Comp 95 donor-first strategy is preferred for cost and interface coherence |
| Brake-first truck | Matrix III 400 mm reference; physical unit still measurement-gated |
| Mechanical stopping | MBS V5 reference; rotor/arm/cable geometry and stop performance require Issue #14 evidence |
| Wheels | donor 8-inch pneumatics first; 9-inch upgrade only after measured need/clearance |
| Drive-clearance study | Matrix III 420 mm reference only; coexistence with the brake-first path is not assumed |
| Rider interface | adjustable/asymmetric Rev-B geometry is blocked on qualified fit evidence |
| Permanent rider-specific drilling | blocked until full-scale template and Rev-B gate pass |

The unpowered chassis must roll, steer, clear its motion envelope, stop mechanically, and survive post-test inspection before traction power is promoted.

## Rider-fit architecture

The rider-fit program is independent of the drivetrain:

1. qualify one Phidgets 3135 + HX711 zone with real known-mass evidence;
2. duplicate the verified mechanical/electrical stack to four zones;
3. collect repeated remount sessions with four-zone force and fixture-IMU coverage;
4. record directly measured left/right foot dimensions and stance geometry privately;
5. generate independent left/right Rev-B adapters with adjustment reserve;
6. physically template the geometry before structural fabrication/drilling.

Stable left/right asymmetry is data, not an error to be numerically forced toward 50/50. Truck geometry remains symmetric unless later mechanical evidence justifies otherwise.

## Power architecture status

Power is intentionally **not frozen**.

`hardware/procurement_manifest.json` currently carries comparison candidates including:

- a professionally assembled high-drain 12S4P battery class;
- a dual VESC-class controller;
- two sensored 6374-class motors;
- an MBS G1 dual-drive reference.

These entries are cost/compatibility placeholders under `POWER_GATED`, not purchase instructions. Voltage, KV, ratio, controller limits, enclosure, BMS, fuse, precharge/service disconnect, and connector architecture must be selected together after the chassis/brake geometry is physically qualified.

The older 14S4P P50B + dual VESC 6/75 + TRAMPA 7:1 design is a historical v0.1 sizing study only.

## Braking philosophy

Mechanical stopping is an independent authority. Regenerative braking may later reduce brake heat or improve control, but it is never the sole stopping path.

Before powered hill work, the selected physical brake system must demonstrate at minimum:

- released wheel free-spin;
- no unintended contact at full application;
- cable/housing exclusion from wheel sweep;
- measured static brake torque tied to measured wheel radius;
- controlled unpowered rolling stop;
- post-test fastener/cable inspection.

Brake qualification explicitly cannot authorize powered operation.

## Build-state machine

`hardware/build_authority.json` defines dependency gates and capabilities. `tools/evaluate_build_authority.py` composes that plan with the procurement manifest and optional local physical-evidence reports.

The public baseline deliberately allows only low-risk evidence acquisition. Later capabilities remain blocked until their upstream physical authorities exist.

This separation matters: “we wrote the validator” is not the same statement as “the hardware passed the validator.”

## First-order simulation

`simulation/x1_dynamics.py` remains a provisional sizing model, not current drivetrain authority. When given a private schema-v2 rider profile it consumes both `mass_kg` and `board_mass_kg`; this keeps grade-force estimates tied to the selected profile rather than silently reverting to generic defaults.

Drive voltage, gearing, KV, wheel diameter, and efficiency constants in that script are retained research parameters until the future power architecture is frozen.

## Commissioning boundary

Current repository authority stops before traction power. No present document, test fixture, CAD generator, procurement entry, or brake report authorizes powered riding.

A future power tranche must introduce an explicit power-architecture qualification contract rather than inheriting permission from historical Alpha assumptions.
