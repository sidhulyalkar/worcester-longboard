# Worcester X1 current development authority

## Purpose

This document describes the **current engineering direction** for Worcester X1. It replaces the original “frozen Alpha v0.1” hardware table as the human-readable design authority.

The original TRAMPA/14S architecture remains useful historical exploration, but it is no longer the current purchase or fabrication plan.

The detailed mechanical review and build sequence now live in `docs/mechanical_architecture_review.md`.

## Authority precedence

When two repository artifacts disagree, use the following precedence:

1. real, fingerprinted physical qualification evidence;
2. `hardware/build_authority.json`;
3. `hardware/procurement_manifest.json`;
4. current component/geometry authority documents and generated reports;
5. dated benchmark/risk registries;
6. historical Alpha notes and packaging snapshots.

A public CI pass proves software behavior only. It never proves that a physical sensor, brake, chassis, battery, drivetrain, enclosure, or rider interface has been measured or qualified.

## Mission

Build a trail-first mountainboard that prioritizes low-speed control, predictable stopping, serviceability, rider-specific fit, and inspectable evidence over headline speed.

The project minimizes expensive re-buys by freezing interfaces in the order that physical evidence becomes available and by avoiding multiple simultaneous novel safety-critical mechanisms.

## Current mechanical reference

| Subsystem | Current status |
|---|---|
| Chassis sourcing | MBS Comp 95 donor-first strategy is preferred for cost and interface coherence |
| Donor geometry | published Comp 95/T1 baseline: 950 mm deck, 251 mm max deck width, 940 mm axle-to-axle, T1 ~194 x 51 mm physical tire reference |
| Brake-first truck | Matrix III 400 mm / 300 mm hanger / 50 mm axle reference; physical unit still measurement-gated |
| Mechanical stopping | MBS V5 measurement reference; rear rotor/arm/cable geometry and stop performance require Issue #14 evidence |
| Wheels | donor 8-inch T1 pneumatics first; 9-inch is a separate optional architecture |
| Drive reference | Matrix III 420 mm / 70 mm axle reference; vendor drive-compatible but brake-incompatible |
| Brake-hanger drive study | 300 mm hanger + 70 mm axles, ~440 mm end-to-end; drive-compatible reference with **brake alignment unknown** |
| Brake/drive topology | unresolved and explicitly gated by Issue #19 |
| Rider interface | independent left/right Rev-B geometry is blocked on qualified fit evidence |
| Permanent rider-specific drilling | blocked until full-scale template and Rev-B gate pass |

The unpowered donor must roll, steer, clear its real motion envelope, stop mechanically, be serviceable, and survive post-test inspection before the brake/drive topology can be qualified.

## Benchmark-derived mechanical principles

`hardware/mechanical_reference_benchmarks_2026-09-11.json` records the comparable production and DIY references used by the current review. The project takes these recurring lessons seriously:

- preserve a known mountainboard truck/hub/wheel/deck family rather than inventing all structural interfaces together;
- use 8-inch pneumatics as the first physical wheel architecture;
- design off-road drives around replaceable guards/skids, positive torque paths, final assembled backlash/tension, and service inspection;
- treat wheel retention, fastener migration, enclosure mounting, cable routing, and debris ingress as first-class failure modes;
- treat front friction braking as a valid topology only when a coherent brake/truck architecture supports it;
- never infer simultaneous brake/drive compatibility from separate catalog compatibility statements.

The FMEA-style planning register is `hardware/mechanical_risk_register.json`.

## Rider-fit architecture

The rider-fit program is independent of the drivetrain:

1. qualify one Phidgets 3135 + HX711 zone with real known-mass evidence;
2. duplicate the verified mechanical/electrical stack to four zones;
3. collect repeated remount sessions with four-zone force and fixture-IMU coverage;
4. record directly measured left/right foot dimensions and stance geometry privately;
5. generate independent left/right Rev-B adapters with adjustment reserve;
6. physically template the geometry before structural fabrication/drilling.

Stable left/right differences are measurement data, not a reason to distort front/rear truck geometry. Truck geometry remains mechanically symmetric unless later vehicle evidence justifies otherwise.

## Brake/drive topology gate

Issue #19 now sits between the qualified unpowered chassis and the future power freeze.

Exactly one of these families must be selected by physical evidence:

- rear V5 plus rear drive on a shared rear truck, only if rotor/pad/drive/coupler/guard geometry genuinely coexists;
- documented rear V5 plus front 2WD, only if front-drive traction/control proves acceptable;
- rear 2WD plus a proven front friction-brake architecture, without improvised safety-critical adapters;
- an alternate rear drive whose packaging preserves the qualified brake-first architecture and whose own debris/tension/retention risks are lower overall.

A passing topology report must be emitted by `tools/qualify_brake_drive_topology.py` as `x1_brake_drive_topology`, select one topology, explicitly reject the others, link brake/chassis/collision/service evidence, and keep `powered_operation_authorized=false`.

## Power architecture status

Power is intentionally **not frozen**.

`hardware/procurement_manifest.json` currently carries comparison candidates including:

- a professionally assembled high-drain 12S4P-class battery reference;
- a dual VESC-class controller;
- two sensored 6374-class motors;
- an MBS G1 dual-drive reference.

These entries are comparison placeholders under `POWER_GATED`, not purchase instructions. The G1 is especially a **drive reference**, not the selected final drive, until Issue #19 resolves brake/drive topology.

Voltage, KV, ratio, controller limits, enclosure, BMS, fuse, precharge/service disconnect, connector architecture, drive type, wheel size, and mechanical-brake topology must be selected as one coupled system after the required physical authorities exist.

The older 14S4P P50B + dual VESC 6/75 + TRAMPA 7:1 design is a historical v0.1 sizing study only.

## Braking philosophy

Mechanical or hydraulic friction stopping remains an independent authority. Regenerative braking may later reduce brake heat or improve control, but it is never the sole stopping path.

Before any powered hill work, the selected physical friction-brake system must demonstrate at minimum:

- braking on at least two wheels;
- stopping availability with traction power disabled;
- released wheel free-spin;
- no unintended contact at full application;
- cable/hose exclusion from wheel/drive sweep;
- measured static brake torque tied to measured wheel radius;
- controlled unpowered rolling stop;
- post-test fastener/cable/pad inspection;
- later repeated-stop thermal/fade evidence appropriate to the intended descent duty cycle.

Issue #14 qualifies the V5 interface only. Issue #19 decides whether that interface survives into the final powered topology.

## Mechanical retention and service philosophy

Critical joints require a joint-specific retention method rather than a blanket “threadlocker everything” rule. Where applicable, record manufacturer torque, locking feature, witness mark, and inspection interval.

Wheel/tube service, brake adjustment, and replaceable guard service must be possible without opening or disturbing unrelated future battery assemblies.

Future battery/enclosure mounting must first be qualified using inert dummy mass matching the intended pack mass and center of mass. A live traction pack is not the mechanical test weight.

## Build-state machine

`hardware/build_authority.json` defines dependency gates and capabilities. `tools/evaluate_build_authority.py` composes that plan with the procurement manifest and optional local physical-evidence reports.

The key dependency is now:

`V5 brake -> unpowered rolling chassis -> brake/drive topology -> power architecture`

The Rev-B rider-interface path joins the power freeze independently after qualified fit and rolling-chassis evidence.

The public baseline deliberately allows only low-risk evidence acquisition. Later capabilities remain blocked until their upstream physical authorities exist.

This separation matters: “we wrote the validator” is not the same statement as “the hardware passed the validator.”

## First-order simulation

`simulation/x1_dynamics.py` remains a provisional sizing model, not drivetrain authority. When given a private schema-v2 rider profile it consumes both `mass_kg` and `board_mass_kg`; this keeps grade-force estimates tied to the selected profile rather than silently reverting to generic defaults.

Drive voltage, gearing, KV, wheel diameter, efficiency, traction, and thermal constants remain research parameters until the future power architecture is frozen. Candidate-B front-drive studies may use simulation to reject obviously poor traction layouts, but simulation cannot qualify the topology by itself.

## Commissioning boundary

Current repository authority stops before traction power. No present document, test fixture, CAD generator, procurement entry, brake report, topology report, or CI pass authorizes powered riding.

A future powered-commissioning tranche must introduce an explicit progressive authority contract beginning with low-energy bench operation and repeated mechanical inspection rather than inheriting permission from the power-architecture freeze.
