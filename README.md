# Worcester X1

Experimental off-road electric mountainboard platform focused on controllability, rider-specific fit, redundant stopping authority, instrumentation, and evidence-driven commissioning.

> **Rev-C update (2026-09-30):** the product target is now a snowboard-inspired trail-carver with modular long-range energy, high-volume pneumatic study, low-jerk dog-accompanied riding mode, and a renewed brake/drive topology review. Expensive chassis, brake, wheel, drive and traction-power purchases are on hold. See `docs/rev_c_trail_carver_architecture.md` and `hardware/rev_c_requirements.json`.

> **Status:** Alpha engineering development platform. No powered riding is authorized. The current physical program is deliberately low-energy: qualify one fit-rig force zone, measure/qualify an unpowered donor chassis and friction brake, resolve the brake/drive mechanical topology, freeze the rider interface, qualify an inert battery-mass load path, and only then freeze the final power architecture.

## Current source of truth

X1 has moved beyond the original TRAMPA/14S Alpha sketch. Current build and purchasing decisions follow this order of authority:

1. machine-readable qualification reports produced from real physical evidence;
2. `hardware/build_authority.json` and `hardware/procurement_manifest.json`;
3. the Rev-C mission and purchase boundary in `hardware/rev_c_requirements.json`, `docs/rev_c_trail_carver_architecture.md`, and `docs/rev_c_chassis_trade.md`;
4. the ride-compliance experiment in `docs/rev_c_ride_compliance_program.md` and `hardware/rev_c_ride_compliance_snapshot_2026-10-01.json`;
5. the pre-purchase Rev-C handoff in `docs/rev_c_chassis_release_playbook.md`;
6. the current physical execution plan in `docs/physical_commissioning_playbook.md`;
7. current geometry/measurement authorities under `cad/`, `hardware/`, and `docs/`;
8. dated benchmark/risk registries;
9. older Alpha notes retained only as historical design exploration.

If an older document conflicts with a current manifest, build gate, or qualified authority, the older document does **not** authorize a purchase, fabrication step, or ride test.

## Ordering and sourcing

Start with `docs/complete_ordering_guide.md` for the staged checkout and receiving procedure.

The ordering stack is deliberately split by function:

- `hardware/procurement_manifest.json` says what is currently orderable or blocked;
- `hardware/order_sources_2026-09-11.json` records the dated vendor/source snapshot used for the current shopping guide;
- `hardware/planned_system_bom.json` maps the complete future board without pretending TBD powered parts are frozen;
- `tools/render_procurement_packet.py` renders the currently authorized checkout packet;
- `tools/validate_ordering_spec.py` detects source/price/compatibility drift against repository authority.

The current complete Issue #4 convenience ceiling remains **$120.90 before shipping/tax**, and optional owned tools/materials should be skipped. Rev-C now holds the previously preferred Comp 95 + V5 chassis purchase until rider-scale deck comparison and wheel/brake/drive topology release conditions close. Standard Rockstar II hubs are not assumed to accept the optional T2 9-inch tire; the 9-inch path remains physically and compatibility gated.

Storefront stock and prices can change faster than the repository. Refresh live availability before payment, but never use a storefront page to bypass a blocked repository item.

## Mechanical design review

The broad benchmark/critique is `docs/mechanical_architecture_review.md`. The **current runnable build sequence** is `docs/physical_commissioning_playbook.md`.

Machine-readable companions keep the review from becoming stale prose:

- `hardware/mechanical_reference_benchmarks_2026-09-11.json` records comparable production/DIY mechanisms and the exact lessons X1 takes from them;
- `hardware/mechanical_risk_register.json` tracks wheel retention, truck/axle structure, steering, brakes, brake fade, brake/drive packaging, drive mounts, guards, enclosure retention, cable routing, rider interface, serviceability and fastener migration;
- `hardware/critical_joint_register_v1.json` defines the minimum critical-joint retention evidence for the unpowered chassis.

`tools/validate_mechanical_architecture.py` fails CI if the donor geometry, benchmark set, FMEA structure, staged packaging gates, power gating, or brake/drive topology boundary silently regresses.

## Current development architecture

### Rider-fit path

```text
one 3135 load cell + one HX711
        -> physical one-zone qualification
        -> four-zone unpowered fit rig
        -> repeatable stance evidence
        -> Rev-B left/right rider-interface CAD
```

The fit layer intentionally supports independent left/right foot dimensions, yaw, position, and removable cant while keeping truck geometry symmetric by default. Exact rider measurements and raw recordings stay under gitignored `rider/private/`. Before any chassis order, `docs/rev_c_no_parts_chassis_experiment.md` provides a zero-cost three-way Comp/Warren/Agent stance test.

### Chassis/brake path

Rev-C now has **two compact Matrix/RSII chassis hypotheses** plus the wider Agent reference: Comp 95 minimizes known mass/cost, while Pro Warren III adds a narrower snowboard-composite deck and adjustable 910–970 mm wheelbase at a 1.3 lb complete-mass penalty. The Agent remains the electric-native reference. None is purchase-authorized until fingerprinted Issue **#25** evidence selects a matching chassis/brake path.

The donor-grounded published reference is explicit:

- **950 mm deck**, **251 mm max width**, **940 mm axle-to-axle**;
- stock **T1 200x50** tires, with current MBS product reference about **194 mm diameter x 51 mm width**;
- **Matrix III 400 mm / 300 mm hanger / 50 mm axle** brake-first geometry;
- **MBS V5** rear friction-brake measurement reference;
- **Matrix III 420 mm / 70 mm axle** drive-only reference;
- **300 mm hanger + 70 mm axle / ~440 mm** topology-study reference where drive compatibility is plausible but V5 brake alignment stays explicitly unknown.

The CAD preserves those as separate branches. It does not recombine brake and drive compatibility into an imaginary universal truck.

`hardware/rev_c_chassis_trade_snapshot_2026-10-01.json` and `tools/analyze_rev_c_chassis_trade.py` preserve the current three-way pre-purchase trade without inventing unknown Agent mass/truck data. The existing donor-grounded Comp CAD remains a **reference**, not permission to skip Issue #25. `tools/init_chassis_session.py` and `tools/qualify_rolling_chassis.py` make Issue #12 physically executable after a chassis family is deliberately released. The qualifier requires a valid linked V5 authority, real measured donor geometry, stock-baseline tests, serviceability checks, and zero detected movement across every critical retention joint.

No rider-specific permanent drilling is authorized from shoe-size labels, approximate web dimensions, or Wi-Fi pose.

### Brake/drive topology path

Issue **#19** is a hard gate between the qualified unpowered chassis and future power packaging.

Candidates include:

- rear V5 + rear drive on a shared truck, only if real axial/sweep geometry coexists;
- documented rear V5 + front 2WD, only if traction/control is acceptable;
- rear 2WD + a **proven** front friction-brake architecture, without improvised safety-critical adapters;
- an alternate rear drive whose packaging preserves the brake-first layout and whose debris/tension/retention risks are acceptable.

`tools/init_brake_drive_topology_session.py` seeds the evidence package from the real Issue #14 and Issue #12 authorities. `tools/qualify_brake_drive_topology.py` requires exactly one passing topology, explicit rejection of the others, and verifies the linked authority fingerprints. A topology report still cannot authorize power.

`docs/topology_decision_tools.md` documents three non-authoritative rejection/sensitivity tools that can reduce wasted physical work before Issue #19:

- `tools/analyze_brake_drive_axial_stack.py` detects measured rotor/pad/brake-arm/drive interval conflicts from one shared axial datum;
- `simulation/front_drive_traction.py` reports front/rear load transfer and the tire/terrain friction coefficient required by front, rear and AWD layouts across grade/acceleration scenarios;
- `tools/analyze_brake_repeat_stops.py` analyzes a predeclared low-energy repeated-stop series for equivalent-deceleration loss and rotor-temperature growth.

These analyses may reject a bad idea cheaply. They are explicitly marked `physical_authority=false` and cannot promote a topology.

### Ride-compliance path

Issue **#28** characterizes the selected unpowered chassis before larger tires or suspension are justified.

The lightweight tuning order is:

```text
stock 200x50 pneumatics
        -> tire pressure within approved range
        -> Matrix III shock-block position
        -> wheelbase where adjustable
        -> real deck / footbed behavior
        -> alternate elastomer hardness only for a named deficiency
        -> higher-volume wheels only for a named deficiency
        -> independent suspension only after measured failure of the lightweight stack
```

`tools/init_rev_c_ride_compliance_session.py` creates a private data workspace and `tools/analyze_rev_c_ride_compliance.py` rejects speed-mismatched or multi-variable comparisons. Objective IMU metrics remain separate from rider observations; neither produces a single snowboard-feel score.

No dog/leash or powered propulsion belongs in this experimental phase.

### Power packaging and inert-load path

The power path is deliberately split into two mechanical stages before final freeze:

```text
qualified topology + qualified Rev-B
        -> x1_power_packaging_candidate
        -> Issue #21 inert dummy-pack mount
        -> x1_power_architecture final freeze
```

The packaging candidate defines only the mechanical target needed to build a faithful inert surrogate: mass/tolerance, enclosure envelope, local CG/tolerance, mounting region, load-spreading/retention concepts, service direction, ground keep-out and acceptable static load-distribution windows.

`tools/qualify_power_packaging_candidate.py` validates that definition. It is **not** a battery purchase authority.

Issue **#21** then tests an inert dummy mass through `tools/init_dummy_pack_session.py` and `tools/qualify_dummy_pack_mount.py`. The qualifier reconciles four-corner wheel loads with independent mass measurements, checks dummy mass/CG tolerance, static load distribution, ground clearance, retention, tilt/inversion, steer/lean/deck-flex clearance, rough-surface behavior, serviceability and post-test structural condition.

The live traction pack is never the first enclosure mechanical test mass.

### Modular energy and charging path

Rev-C separates **installed energy**, **trip energy**, and **charge power**.

The current planning policy is:

- use the smallest qualified installed pack class that covers the mission with reserve;
- preserve the lighter 500-650 Wh trail class for handling/carryability when it is sufficient;
- use the 950-1150 Wh range class for genuinely long missions;
- keep cold swap powered-off and treat it as a logistics option, not a reason to permanently carry duplicate small packs;
- replace generic Wh/mi assumptions with X1 telemetry only after powered commissioning eventually produces trustworthy data.

`simulation/rev_c_energy_planner.py` exposes mission-energy requirements and ideal energy/power charge-time lower bounds. `tools/analyze_rev_c_energy_trade.py` compares dated commercial pack references without selecting one.

Issue **#30** defines the future charge dock as a **passive mechanical alignment cradle**. The dock may self-center the board, manage cable strain and make approved-charger connection easier, but it does not replace the selected battery/system-approved charger, add exposed traction-voltage contacts, or authorize live charging. See `docs/rev_c_energy_and_charging.md`.

### Final power path

Power hardware remains **provisional and `POWER_GATED`**. The current procurement manifest carries comparison candidates only to preserve cost/compatibility analysis. None are frozen or order-authorized yet.

The G1 is a reference candidate, not the selected drive. Final drive type, ratio, axle state, wheel size, voltage, motor KV/shaft, controller, professionally built battery, BMS/charger, enclosure and harness freeze together only after Issue #19, Rev-B and Issue #21 pass.

Regenerative braking remains supplemental.

## Executable build gates

Run:

```bash
python tools/evaluate_build_authority.py \
  hardware/build_authority.json \
  hardware/procurement_manifest.json
```

With no private physical-evidence reports, the public repository must remain conservative: inexpensive fit-pilot parts can be considered, while Rev-C keeps measurement-stage chassis/brake purchases, four-zone duplication, chassis fabrication authority, brake/drive topology qualification, power-packaging definition, dummy-pack qualification, power ordering, and powered operation blocked.

Local/private authority reports can be supplied with repeated `--evidence` arguments. CI tests the gate machinery with synthetic fixtures, but synthetic CI data never becomes physical authority.

## Repository map

- `hardware/` procurement, mechanical benchmarks/FMEA, critical-joint retention, fit-rig interfaces, analysis templates, and build-state authority
- `cad/` parametric fit-rig and donor-grounded rolling-chassis reference geometry
- `fit/` calibration, provenance, stance scoring, and Rev-B data gates
- `tools/` capture, qualification, procurement, topology analysis, mechanical and authority evaluators
- `firmware/` fit-rig logger plus provisional vehicle-control research
- `simulation/` first-order sizing and topology sensitivity models
- `docs/` ordering, mechanical review, topology decision support, physical commissioning, measurement contracts and safety boundaries
- `rider/` public schemas only; private measurements belong under `rider/private/`
- `bom/` historical Alpha BOM notes plus procurement snapshots

## Current physical milestones

- **#4** qualify one load-cell/HX711/pod zone before four-zone duplication
- **#25** qualify Rev-C pre-purchase chassis release from deck/topology/inert-envelope evidence
- **#2** build and qualify X1 Fit Rig v0.3
- **#14** measure and qualify the V5 mechanical-brake interface
- **#12** qualify the donor-grounded unpowered rolling chassis
- **#28** characterize the lightweight unpowered ride-compliance stack
- **#19** resolve and qualify final brake/drive mechanical topology
- **#3** generate measurement-qualified Rev-B rider-interface CAD after fit evidence
- **#21** qualify inert dummy-pack enclosure/mount and mass distribution before final power freeze
- **#30** qualify the passive charge-cradle mechanics after final pack/charger interfaces are known

These tracks can advance in parallel only where their evidence dependencies allow.

## Rider-specific modeling boundary

The profile schema uses direct measured values such as `mass_kg`, `board_mass_kg`, independent foot dimensions, natural yaw, and stance geometry. Shoe-size labels are descriptive only and are never converted into manufacturing dimensions.

RuView-style Wi-Fi pose can be used as auxiliary dynamic-comparison data, but it is not metric CAD authority and cannot command the board.

## Safety boundary

This repository is an engineering workspace, not a product certification. Printed fit-rig parts are calibration hardware, not qualified ride structure. High-current traction battery construction belongs with a qualified pack builder. Powered operation requires future explicit authority beyond the current gate graph; software limits never replace hard mechanical/electrical safety layers.
