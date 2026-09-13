# Worcester X1 current development authority

## Purpose

This document describes the **current engineering direction** for Worcester X1. It replaces the original “frozen Alpha v0.1” hardware table as the human-readable design authority.

The original TRAMPA/14S architecture remains useful historical exploration, but it is no longer the current purchase or fabrication plan.

The broad design critique is `docs/mechanical_architecture_review.md`. The **current runnable execution sequence** is `docs/physical_commissioning_playbook.md` and supersedes older phase-order wording where necessary.

## Authority precedence

When two repository artifacts disagree, use the following precedence:

1. real, fingerprinted physical qualification evidence;
2. `hardware/build_authority.json`;
3. `hardware/procurement_manifest.json`;
4. `docs/physical_commissioning_playbook.md`;
5. current component/geometry authority documents and generated reports;
6. dated benchmark/risk registries;
7. historical Alpha notes and packaging snapshots.

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
| Power packaging candidate | blocked until topology and Rev-B authority exist |
| Inert battery-mass load path | blocked until packaging candidate exists; Issue #21 closes it |
| Final power architecture | blocked until Issue #21 passes |
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

The FMEA-style planning register is `hardware/mechanical_risk_register.json`. `hardware/critical_joint_register_v1.json` defines the minimum retention evidence for the unpowered donor/V5 chassis.

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

Issue #19 sits between the qualified unpowered chassis and future power packaging.

Exactly one of these families must be selected by physical evidence:

- rear V5 plus rear drive on a shared rear truck, only if rotor/pad/drive/coupler/guard geometry genuinely coexists;
- documented rear V5 plus front 2WD, only if front-drive traction/control proves acceptable;
- rear 2WD plus a proven front friction-brake architecture, without improvised safety-critical adapters;
- an alternate rear drive whose packaging preserves the qualified brake-first architecture and whose own debris/tension/retention risks are lower overall.

A topology session is initialized from the real Issue #14 and Issue #12 authorities with `tools/init_brake_drive_topology_session.py`. A passing report from `tools/qualify_brake_drive_topology.py` must select one topology, explicitly reject the others, link and verify the actual brake/chassis authorities plus collision/service evidence, and keep `powered_operation_authorized=false`.

## Physical rolling-chassis authority

Issue #12 now has an executable evidence path rather than an abstract build gate.

`tools/init_chassis_session.py` creates a private donor session with stable hardware IDs and the full critical-joint retention contract. `tools/qualify_rolling_chassis.py` requires:

- actual measured donor dimensions and tire pressures;
- stock donor baseline captured before X1 modifications;
- wheel free-spin and bearing/play checks;
- steering effort and return-to-center checks;
- controlled stock push/coast testing;
- a valid linked Issue #14 V5 authority;
- full steer/lean/cable clearance with brake installed;
- rough-surface and wheel/tube service checks;
- pre/post inspection across every critical joint;
- no detected retention movement;
- no drivetrain, traction battery, or powered testing inside the unpowered evidence scope.

A passing report is `x1_rolling_chassis_physical` and still cannot authorize power.

## Staged power packaging architecture

Power is intentionally **not frozen** and is now split into preliminary packaging, inert physical qualification, and final freeze.

### Stage A: power packaging candidate

After Issue #19 and Rev-B qualify, define only the mechanical target required to build a faithful inert surrogate:

- target pack mass and tolerance;
- enclosure length/width/height envelope;
- local CG and tolerance;
- mounting region;
- positive-retention concept;
- load-spreading concept;
- skid/guard concept;
- service-removal direction;
- minimum vulnerable-component ground keep-out;
- acceptable front and left static-load fraction windows.

`tools/qualify_power_packaging_candidate.py` emits fingerprinted `x1_power_packaging_candidate` authority. It is **not** a battery purchase specification.

### Stage B: Issue #21 inert dummy-pack mount

The highest current FMEA risk, battery/enclosure structural retention, is closed using inert mass before any live traction pack is ordered or installed.

`tools/init_dummy_pack_session.py` consumes the actual packaging-candidate and rolling-chassis authorities. `tools/qualify_dummy_pack_mount.py` checks:

- dummy mass and measured CG against candidate tolerances;
- independent bare and dummy-installed system masses;
- four-corner wheel-load sums against those masses;
- wheel-load delta against dummy mass;
- front and left static-load fractions against candidate windows;
- vulnerable-component ground clearance;
- positive retention independent of adhesive;
- load spreading;
- steer/lean/deck-flex clearance;
- tilt/inversion retention;
- rough-surface unpowered push/coast;
- service removal/reinstallation;
- no witness movement, cracking, crushing, pull-through or fretting;
- no live cells or powered test.

A passing report is `x1_dummy_pack_mount` and is required before final power freeze.

### Stage C: final power architecture freeze

Only after the dummy-pack load path passes may the project freeze the coupled powered system:

- drive type and ratio;
- axle configuration;
- wheel size;
- motor size/KV/shaft interface;
- system voltage;
- ESC voltage/current/ERPM/thermal headroom;
- professionally built battery capacity/current/cell architecture;
- BMS/charger;
- fuse/service disconnect/precharge;
- connectors/conductors;
- final enclosure derived from the qualified dummy envelope;
- remote/failsafe architecture;
- supervisory/harness layout.

`hardware/procurement_manifest.json` still keeps all high-energy parts `POWER_GATED` until explicitly promoted. Final architecture freeze does not itself authorize powered riding.

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

Critical joints require a joint-specific retention method rather than a blanket “threadlocker everything” rule. Where applicable, record manufacturer torque, locking feature, witness method, and inspection interval. A torque value is recorded only when a real manufacturer source exists.

Any witness movement is a failed retention event until the mechanism is understood.

Wheel/tube service, brake adjustment, and replaceable guard service must be possible without opening or disturbing unrelated safety-critical assemblies.

Future battery/enclosure mounting is qualified using inert dummy mass matching the candidate pack mass and center of mass. A live traction pack is never the mechanical test weight.

## Build-state machine

`hardware/build_authority.json` defines dependency gates and capabilities. `tools/evaluate_build_authority.py` composes that plan with the procurement manifest and optional local physical-evidence reports.

The critical dependency is now:

`V5 brake -> rolling chassis -> brake/drive topology -> power packaging candidate -> inert dummy-pack mount -> final power architecture`

The Rev-B rider-interface path joins at the packaging-candidate gate after qualified fit and rolling-chassis evidence.

The public baseline deliberately allows only low-risk evidence acquisition. Later capabilities remain blocked until their upstream physical authorities exist.

This separation matters: “we wrote the validator” is not the same statement as “the hardware passed the validator.”

## First-order simulation

`simulation/x1_dynamics.py` remains a provisional sizing model, not drivetrain authority. When given a private schema-v2 rider profile it consumes both `mass_kg` and `board_mass_kg`; this keeps grade-force estimates tied to the selected profile rather than silently reverting to generic defaults.

Drive voltage, gearing, KV, wheel diameter, efficiency, traction, and thermal constants remain research parameters until final power architecture is frozen. Candidate-B front-drive studies may use simulation to reject obviously poor traction layouts, but simulation cannot qualify the topology by itself.

## Commissioning boundary

Current repository authority stops before traction power. No present document, test fixture, CAD generator, procurement entry, brake report, chassis report, topology report, dummy-pack report, or CI pass authorizes powered riding.

A future powered-commissioning tranche must introduce an explicit progressive authority contract beginning with low-energy bench operation and repeated mechanical inspection rather than inheriting permission from final power-architecture freeze.
