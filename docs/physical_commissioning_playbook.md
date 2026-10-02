# Worcester X1 physical commissioning playbook

Status: **current execution plan**. This document supersedes older phase-order wording where it conflicts with `hardware/build_authority.json`.

The goal is not to assemble the final board as quickly as possible. The goal is to preserve a known-good mechanical baseline, introduce one new variable at a time, and produce machine-checkable evidence at each transition.

## 1. Evidence chain

Current physical release order:

```text
Issue #4 one-zone fit pilot
        |
        +--> Issue #2 four-zone rider-fit evidence --> Issue #3 Rev-B template
        |
        +--> Issue #14 V5 brake interface
                 |
                 v
          Issue #12 rolling chassis
                 |
        +--------+------------------+
        |                           |
        v                           v
Issue #28 ride compliance    Issue #19 brake/drive topology
(unpowered analysis)                |
                                    +---- requires Rev-B template ----+
                                                   v
                                 power packaging candidate
                                                   |
                              +--------------------+--------------------+
                              |                                         |
                              v                                         v
                Issue #37 inert trail armor                 Issue #21 inert dummy-pack mount
                geometry / service path                     structural pack load path
                              |                                         |
                              +--------------------+--------------------+
                                                   |
                                                   v
                                Issue #39 inert environmental candidate
                                contamination / drainage / service recovery
                                                   |
                                                   v
                                      final power architecture freeze
                                                   |
                                                   v
                                   Issue #35 authorized venue evidence
                                                   |
                                                   v
                                       future powered commissioning
                                                   |
                                                   v
                                  Issue #33 rider-only Shasta qualification
                                                   |
                                                   v
                                 future explicit companion release
```

No current gate authorizes powered operation.

## 2. Donor receipt and stock baseline

Do not modify the donor before the baseline session is created.

Create the private session:

```bash
PYTHONPATH=. python tools/init_chassis_session.py \
  rider/private/chassis/donor-a \
  --donor-id DONOR-A \
  --deck-id DECK-A \
  --front-truck-id TRUCK-F-A \
  --rear-truck-id TRUCK-R-A \
  --wheel-fl-id WHEEL-FL-A \
  --wheel-fr-id WHEEL-FR-A \
  --wheel-rl-id WHEEL-RL-A \
  --wheel-rr-id WHEEL-RR-A \
  --brake-id BRAKE-V5-A
```

Before changing anything:

1. photograph/record exact donor condition and revision markings;
2. measure deck tip-to-tip, deck maximum width and axle-to-axle distance;
3. measure both truck total widths;
4. record cold tire pressure for all four wheels;
5. measure all four inflated tire diameters and widths at those pressures;
6. measure wheel axial play and verify free spin;
7. inspect deck faces/edges/inserts and truck mount zones;
8. inspect axles/hangers for damage, visible bending or unusual play;
9. record steering adjustment/shockblock state;
10. apply or record the inspection method for every joint in `hardware/critical_joint_register_v1.json`.

Then perform the stock unpowered baseline:

- left/right steering effort comparison;
- return-to-center check;
- full lean/steer interference check;
- walking-speed push/coast;
- jogging-speed push/coast in a controlled area;
- rough-surface push/coast;
- complete post-test inspection.

Any new noise, movement, crack, wheel contact, witness-mark movement or steering migration is a failed baseline until understood.

## 3. Issue #14 V5 qualification

Qualify the received V5 separately using the existing brake measurement contract.

The brake authority must be a valid fingerprinted `x1_mechanical_brake_interface` report with:

- released free spin;
- no unintended contact at full application;
- cable clear of wheel sweep;
- measured static brake torque;
- controlled unpowered rolling stop;
- post-test fastener/cable inspection;
- `powered_operation_authorized=false`.

Do not use the brake report to infer drivetrain compatibility.

## 4. Issue #12 rolling-chassis authority

After the stock baseline and V5 qualification, complete the brake-installed chassis fields in `chassis_manifest.json`.

Every critical joint record must include:

- actual hardware description;
- assembly state;
- locking/retention method;
- witness or equivalent inspection method;
- pre-test inspection pass;
- post-test inspection pass;
- `movement_detected=false`.

Manufacturer torque may be recorded only when a manufacturer source exists. Do not invent a torque value to fill a field.

Qualify:

```bash
PYTHONPATH=. python tools/qualify_rolling_chassis.py \
  rider/private/chassis/donor-a/chassis_manifest.json \
  --brake-authority rider/private/brake/v5-a/brake_authority.json \
  --out rider/private/chassis/donor-a/chassis_authority.json
```

The qualifier intentionally does not promote a catalog clearance number into a physical threshold. It requires real measured clearance plus passing full-steer, full-lean and rough-surface tests.

A passing report is `x1_rolling_chassis_physical`; it still cannot authorize power.

## 4A. Issue #28 unpowered ride-compliance characterization

Issue #28 may run after a real `x1_rolling_chassis_physical` authority exists. It is parallel evidence, not a prerequisite for beginning Issue #19.

Initialize:

```bash
python tools/init_rev_c_ride_compliance_session.py \
  rider/private/ride_compliance/session-01
```

Follow `docs/rev_c_ride_compliance_program.md`.

The first comparison order is:

1. repeatable stock baseline;
2. 200x50 tire pressure within the selected tire/wheel approved range;
3. stock Matrix III shock-block position;
4. wheelbase where the chassis is adjustable;
5. real deck / footbed behavior.

Alternate shock-block hardness, Explorer wheels, 9-inch wheels, and independent suspension remain deferred until a specific measured deficiency justifies them.

The session is explicitly unpowered, uses no dog/leash, keeps the course and IMU mount fixed, changes one primary variable per comparison block, and requires matched-speed repeated runs.

Analyze:

```bash
python tools/analyze_rev_c_ride_compliance.py \
  rider/private/ride_compliance/session-01/ride_compliance_manifest.json \
  --out rider/private/ride_compliance/session-01/analysis.json
```

The analysis is intentionally `physical_authority=false`, `procurement_authority=false`, and `powered_operation_authorized=false`. It characterizes the chassis and can justify later tuning studies; it cannot release traction power.

## 5. Issue #19 brake/drive topology

Create the topology session from the actual Issue #14 and Issue #12 authorities:

```bash
PYTHONPATH=. python tools/init_brake_drive_topology_session.py \
  rider/private/topology/v1 \
  --brake-authority rider/private/brake/v5-a/brake_authority.json \
  --chassis-authority rider/private/chassis/donor-a/chassis_authority.json \
  --front-truck-id TRUCK-F-A \
  --rear-truck-id TRUCK-R-A \
  --rear-axle-id AXLE-R-A \
  --rear-hub-id HUB-R-A \
  --rear-wheel-id WHEEL-R-A \
  --brake-id BRAKE-V5-A \
  --drive-reference-id DRIVE-REF-A
```

Evaluate all four candidate families. Exactly one may pass and every other candidate must be explicitly rejected with a reason.

Candidate A, shared rear V5 plus rear drive, is investigated first because success yields the simplest conventional architecture. Reject it immediately if it needs an unqualified safety-critical brake-arm spacer/extender, has axial/swept interference, blocks wheel service, or compromises the brake cable path.

The collision-sweep and service records referenced by the manifest must be hashed and preserved.

Qualify:

```bash
PYTHONPATH=. python tools/qualify_brake_drive_topology.py \
  rider/private/topology/v1/topology_manifest.json \
  --brake-authority rider/private/brake/v5-a/brake_authority.json \
  --chassis-authority rider/private/chassis/donor-a/chassis_authority.json \
  --out rider/private/topology/v1/topology_authority.json
```

## 6. Rev-B rider interface

The rider-fit path can progress in parallel once Issue #4 opens four-zone duplication.

Before permanent drilling:

- use direct measured foot/stance data;
- generate a full-scale left/right template;
- retain adjustment reserve;
- verify full-steer clearance;
- verify service access to structural fasteners;
- rehearse emergency step-off/release unpowered;
- keep front/rear truck geometry symmetric unless mechanical evidence independently justifies a change.

Final output is fingerprinted `x1_rev_b_template` authority.

## 7. Define a power-packaging candidate, not the final battery

After Issue #19 and Rev-B qualify, define only enough power architecture to create a faithful inert mechanical surrogate.

The candidate must specify:

- target pack mass and tolerance;
- enclosure length/width/height envelope;
- target local CG and tolerance;
- mounting region;
- positive-retention concept;
- load-spreading concept;
- skid/guard concept;
- service-removal direction;
- minimum vulnerable-component ground keep-out;
- acceptable front static-load fraction range;
- acceptable left static-load fraction range;
- linked topology and Rev-B fingerprints.

It deliberately does **not** authorize ordering a traction pack.

Prepare a candidate manifest and qualify it with:

```bash
PYTHONPATH=. python tools/qualify_power_packaging_candidate.py \
  rider/private/power/candidate_v1.json \
  --out rider/private/power/candidate_v1_authority.json
```

## 7A. Issue #37 inert trail-armor geometry and service path

After Issue #19 and the power-packaging candidate define the real protected zones, Issue #37 may begin in parallel with the dummy-pack program.

This stage still uses inert protected-component surrogates.

Initialize:

```bash
python tools/init_rev_c_trail_armor_session.py \
  rider/private/armor/zone-a
```

Before contact testing, quantify the proposed skid's clearance cost from measured geometry:

```bash
python simulation/rev_c_skid_geometry.py \
  --wheelbase-mm <measured> \
  --skid-x-mm <measured> \
  --component-clearance-mm <measured> \
  --skid-drop-mm <measured>
```

Then fill `trail_armor_manifest.json` and qualify:

```bash
python tools/qualify_rev_c_trail_armor.py \
  rider/private/armor/zone-a/trail_armor_manifest.json \
  --out rider/private/armor/zone-a/trail_armor_authority.json
```

The early armor trial requires:

- the wear surface to be the intended first hard contact;
- full steer/lean/deck-flex/wheel/brake/harness clearance;
- no forward-facing terrain hook or debris trap;
- an explicit wear-shoe -> carrier/vendor guard -> structural-mount load path;
- no battery shell or connector used as the primary impact structure;
- wear-part replacement without opening the traction enclosure or disturbing unrelated brake-critical retention;
- at least three low-energy root/curb surrogate contacts;
- clean post-contact retention and protected-component inspection.

A passing report remains `impact_energy_qualified=false`.

If the final motor, gearbox, enclosure, mount or skid geometry changes after power freeze, repeat the affected Issue #37 zone. Early armor geometry evidence cannot be inherited across a changed impact load path.

## 8. Issue #21 inert dummy-pack mount

Create the physical session:

```bash
PYTHONPATH=. python tools/init_dummy_pack_session.py \
  rider/private/dummy_pack/v1 \
  --candidate-authority rider/private/power/candidate_v1_authority.json \
  --chassis-authority rider/private/chassis/donor-a/chassis_authority.json \
  --enclosure-id DUMMY-ENC-A \
  --mount-id DUMMY-MOUNT-A
```

Use inert ballast only. No live cells, BMS, traction connector, ESC or energized motor belongs in this test.

Match the candidate mass and local CG within its stated tolerances before structural testing.

Record four-corner wheel loads on the same level surface for:

1. bare qualified chassis;
2. dummy-installed chassis.

The qualifier checks that wheel-load sums agree with independently recorded system masses and that the wheel-load delta agrees with dummy mass. This catches bad scale setup or transcription before those numbers become design authority.

Then test:

- positive retention independent of adhesive;
- load spreading;
- full steer;
- full lean;
- deck-flex clearance;
- safe tilt/inversion retention;
- rough-surface unpowered push/coast;
- service removal and reinstallation;
- ground/skid keep-out;
- witness marks;
- deck/insert/load-spreader/enclosure cracking, crushing, pull-through or fretting.

Qualify:

```bash
PYTHONPATH=. python tools/qualify_dummy_pack_mount.py \
  rider/private/dummy_pack/v1/dummy_pack_manifest.json \
  --candidate-authority rider/private/power/candidate_v1_authority.json \
  --chassis-authority rider/private/chassis/donor-a/chassis_authority.json \
  --out rider/private/dummy_pack/v1/dummy_pack_authority.json
```

Only a passing `x1_dummy_pack_mount` report can open the final power freeze.

## 8A. Issue #39 inert environmental durability candidate

Issue #39 runs after the qualified Issue #21 dummy-pack mount and before final power architecture freeze.

Create the private session from the real authorities:

```bash
python tools/init_rev_c_environmental_session.py \
  rider/private/environmental/session-01 \
  --chassis-authority rider/private/chassis/donor-a/chassis_authority.json \
  --dummy-pack-authority rider/private/dummy_pack/v1/dummy_pack_authority.json \
  --candidate-enclosure-id INERT-ENC-A \
  --harness-revision-id HARNESS-SURROGATE-A
```

Follow `docs/rev_c_environmental_durability.md`.

Initial trials are inert/disconnected only and must cover:

1. complete exposed-interface inventory;
2. dry-grit surrogate;
3. clean-water splash surrogate;
4. inert mud surrogate;
5. disconnected connector inspection/clean/re-seat;
6. wheel/bearing/brake/steering recovery;
7. declared drying process and post-exposure inspection.

Do not use:

- live traction battery;
- traction voltage;
- connected charger;
- powered vehicle;
- pressure washer;
- immersion.

Qualify:

```bash
python tools/qualify_rev_c_environmental_durability.py \
  rider/private/environmental/session-01/environmental_manifest.json \
  --chassis-authority rider/private/chassis/donor-a/chassis_authority.json \
  --dummy-pack-authority rider/private/dummy_pack/v1/dummy_pack_authority.json \
  --out rider/private/environmental/session-01/environmental_authority.json
```

A passing report is fingerprinted `x1_environmental_inert_candidate`.

It still has:

```text
ip_rating_claimed = false
waterproof_claimed = false
corrosion_life_claimed = false
electrical_wet_operation_qualified = false
live_battery_test_authorized = false
procurement_authority = false
powered_operation_authorized = false
```

This gate exists so the enclosure, harness entries, drainage, connector access and maintenance strategy can be changed before expensive power hardware freezes.

Future energized environmental validation remains separate.

## 9. Final power architecture freeze

Only after Issue #21 **and Issue #39** pass may the project freeze the coupled powered system:

- selected drive architecture;
- final axle configuration;
- wheel size;
- ratio;
- motor size/KV/shaft interface;
- system voltage;
- ESC current/voltage/ERPM/thermal headroom;
- professionally built battery cell/current/capacity architecture;
- BMS and charger;
- main fuse;
- service disconnect;
- precharge/anti-spark;
- high-current connectors/conductors;
- final enclosure derived from the qualified dummy envelope;
- remote/failsafe architecture;
- low-voltage CAN/sensor/harness layout.

Power purchasing remains separately blocked by the procurement manifest until explicitly promoted.

## 9A. Issue #30 passive charge-cradle mechanics

After the battery architecture, approved charger, connector orientation and final enclosure interfaces are selected, the **mechanical** charging cradle can be frozen.

Use an inert pack and inert connector surrogate first. The template and qualifier are:

```text
hardware/rev_c_charge_dock_mechanical_template.json
tools/qualify_rev_c_charge_dock.py
```

The dock must support and retain the parked board independently of the charge connector, avoid loading brake/drive hardware, self-center repeatably, preserve service access, protect the connector when the board is absent, and maintain cable strain relief and clearance.

The inert qualifier requires at least five repeatable alignment trials and a clean post-trial inspection.

A passing report still has:

```text
live_battery_test_authorized = false
electrical_charge_authorized = false
procurement_authority = false
powered_operation_authorized = false
```

The dock never creates charger compatibility. A later live charging procedure must use only the selected battery/system-approved charger and the selected system's documented instructions.

## 9B. Issue #35 authorized powered-test venue evidence

Before any future powered ground test, create a private venue session:

```bash
python tools/init_powered_test_venue_session.py \
  rider/private/venues/test-01
```

Fill `venue_manifest.json` from the actual location and permission record.

The record must identify:

- owner or managing jurisdiction;
- permission basis and source;
- date permission was checked;
- controlled course boundary;
- surface;
- pedestrian/vehicle separation;
- emergency stop plan;
- maximum planned speed;
- applicable restrictions;
- mechanical-brake requirement.

Current dated rules mean Worcester Park must not be used as the default powered test venue.

Qualify the venue record:

```bash
python tools/qualify_powered_test_venue.py \
  rider/private/venues/test-01/venue_manifest.json \
  --out rider/private/venues/test-01/venue_authority.json
```

A passing report proves only that the venue evidence is complete under the dated checklist.

It still emits:

```text
vehicle_powered_operation_authority = false
public_operation_authority = false
dog_accompanied_operation_authority = false
```

Venue permission never substitutes for vehicle qualification.

## 10. Drivetrain commissioning after final freeze

Even after final power architecture is frozen, do not jump directly to riding.

Mechanical commissioning order:

1. assemble drive without traction battery installed;
2. hand-rotate every wheel through a full revolution;
3. verify backlash/tension/alignment;
4. verify wheel/tube service;
5. verify guard/skid clearance;
6. perform static torque-reaction test;
7. inspect witness marks;
8. only then use a current-limited low-energy source if future electrical authority allows;
9. inspect mount angle, bearings and temperature after every run.

A future powered-operation authority must add its own incremental speed/load/failsafe/thermal test ladder. Current repository authority remains hard-blocked from powered riding.

## 10A. Issue #33 Shasta companion-mode qualification

Issue #33 begins in software now but cannot reach physical companion testing until a future powered-operation authority exists.

Current Stage 0 is host-only:

- validate `hardware/rev_c_shasta_mode_requirements.json`;
- compile and run `firmware/test/test_control_core.cpp`;
- keep `tools/validate_shasta_control_contract.py` green;
- preserve `powered_operation_authorized=false`.

Future Stage 1 is bench/no-rider only.

Future Stage 2 is rider-only closed-course low-speed testing after the overall vehicle has independent powered authority. Shasta must not be present.

That rider-only stage must measure actual:

- ground speed;
- longitudinal acceleration;
- longitudinal jerk;
- deadman/remote-release propulsion decay;
- regen-to-mechanical-brake transition behavior;
- stopping response;
- wheel slip and left/right current;
- thermal state;
- fault logs.

Current-slew limits are not accepted as a substitute for those measurements.

Only after Stage 2 is independently accepted may a separate explicit companion authority consider Stage 3.

Stage 3 still prohibits:

- leash attachment to the board;
- towing;
- dog-follow steering;
- autonomous pace matching;
- deliberate differential carve assist.

See `docs/rev_c_shasta_companion_mode.md`.

## 11. Stop rules

Stop the current stage immediately if any of these occur:

- witness mark moves;
- wheel retention changes;
- crack, crushing, pull-through or fretting appears;
- axle/hanger alignment changes;
- wheel/tire contacts deck, brake, drive or cable outside intended interfaces;
- brake cable or harness enters moving sweep;
- steering does not return predictably;
- service requires disturbing an unrelated safety-critical assembly;
- a test needs a custom safety-critical adapter that has not itself been engineered and qualified;
- evidence cannot be traced to stable hardware IDs.

The correct response is not to loosen the threshold. Find the mechanism, repair the design, and repeat the stage from a known baseline.
