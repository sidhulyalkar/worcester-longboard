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
                 v
          Issue #19 brake/drive topology
                 |
                 +---- requires Rev-B template ----+
                                                   v
                                 power packaging candidate
                                                   |
                                                   v
                                  Issue #21 inert dummy-pack mount
                                                   |
                                                   v
                                      final power architecture freeze
                                                   |
                                                   v
                                       future powered commissioning
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

## 9. Final power architecture freeze

Only now freeze the coupled powered system:

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
