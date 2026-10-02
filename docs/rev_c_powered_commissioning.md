# Worcester X1 Rev-C staged powered commissioning

**Issue:** #45  
**Status:** future staged authority framework.  
**General powered operation:** not authorized.  
**Public operation:** not authorized.  
**Dog-accompanied operation:** not authorized.

This program defines how Worcester X1 may eventually progress from a frozen power architecture to controlled energized evidence without jumping directly from CAD/bench work to normal riding.

The core rule is: every increase in energy, load, freedom of motion, or rider exposure is a new commissioning stage with its own evidence.

A passing stage satisfies only one prerequisite in the build-authority graph.

## Relationship to Rev-C

Issue #45 begins only after:

- final `x1_power_architecture` authority exists;
- Issue #43 powertrain-envelope evidence has already been consumed by that final freeze;
- the exact board/configuration has a current `READY_FOR_ALLOWED_ACTIVITY` lifecycle-health state;
- the independent mechanical stopping path remains healthy.

Ground-contact stages additionally require fingerprinted Issue #35 powered-test venue evidence.

Dog-accompanied work remains downstream of Issue #33 and does not participate in Stage 0-4 commissioning.

## Authority ladder

The machine-readable source is `hardware/rev_c_powered_commissioning_snapshot_2026-10-01.json` and the evidence template is `hardware/rev_c_powered_commissioning_stage_template.json`.

```text
Stage 0  BENCH_READINESS
   |
   v
Stage 1  SECURED_UNLOADED_SPIN
   |
   v
Stage 2  RESTRAINED_LOADED_BENCH
   |
   +---- qualified powered-test venue required before ground travel
   |
   v
Stage 3  RIDER_FREE_CONTROLLED_GROUND
   |
   v
Stage 4  RIDER_ONLY_VERY_LOW_SPEED
```

Even after Stage 4:

```text
general_powered_operation_authorized = false
public_operation_authorized = false
dog_accompanied_operation_authorized = false
```

Stage 4 is commissioning evidence, not a normal-use license.

## Configuration lineage

Every stage binds to the board ID, configuration ID, exact final power-architecture fingerprint, exact pre-stage lifecycle-health fingerprint, immediately previous commissioning-stage fingerprint where applicable, exact powered-test venue fingerprint for Stage 3/4, and post-stage lifecycle-health fingerprint for every energized stage.

A meaningful configuration change invalidates downstream commissioning lineage until affected stages are repeated.

Examples include motor/ratio changes, controller replacement or material configuration changes, traction-system replacement, wheel diameter changes, brake/drive topology changes, mount/gearbox changes, harness changes, or major enclosure/mass-distribution changes.

## Lifecycle-health handshake

Before every stage the current board/configuration must report `READY_FOR_ALLOWED_ACTIVITY`.

For Stage 1-4, qualification additionally requires a different post-stage READY health report created after the stage completes.

```text
fresh preflight
   -> READY health report
   -> commissioning stage
   -> post-stage inspection/service if needed
   -> fresh preflight
   -> new READY health report
   -> qualify stage
```

If the stage creates `STOP_USE`, `SERVICE_REQUIRED`, unresolved findings, or an incomplete preflight, the stage cannot qualify.

## Stage 0: powered bench readiness

**Energized:** no  
**Free ground travel:** no  
**Rider:** no  
**Dog:** no  
**Venue:** not required

Stage 0 reviews the exact final architecture, lifecycle health, independent brake, wiring/connectors, fuse/disconnect/precharge strategy, emergency power removal, remote/deadman configuration, declared electrical/thermal stop limits, logging plan, and secured spin-fixture plan.

Do not use Stage 0 to discover motor direction under propulsion.

## Stage 1: secured unloaded wheel spin

**Energized:** yes  
**Free ground travel:** no  
**Rider:** no  
**Dog:** no

The board is mechanically secured with driven wheels clear of the ground.

Purpose:

- verify motor direction and left/right mapping;
- verify zero command produces no drive;
- verify deadman/remote/stale-command behavior;
- verify wheel/motor speed sensing;
- verify motor/controller temperature sensing;
- observe current, voltage and speed/ERPM inside the declared stage limits;
- verify fault/event logging;
- inspect retention after the test.

A Stage 1 pass does not authorize free ground contact.

## Stage 2: restrained loaded bench / roller

**Energized:** yes  
**Free ground travel:** no  
**Rider:** no  
**Dog:** no

This stage adds controlled drivetrain load while preserving physical restraint.

Observe battery current separately from motor phase current, pack voltage, ERPM, motor/controller temperature, wheel/motor-speed consistency, vibration/noise, mount motion, retention, sensor agreement, and regen behavior.

Independent mechanical braking remains required. A short loaded bench run does not prove continuous thermal capability.

## Stage 3: rider-free controlled ground contact

**Energized:** yes  
**Free ground travel:** yes  
**Rider:** no  
**Dog:** no  
**Venue:** qualified private/controlled venue required

This is the first stage where the vehicle may translate on the ground.

Purpose:

- very-low-speed propulsion and stopping;
- independent ground-speed measurement;
- remote/deadman propulsion-decay measurement;
- steering-neutral nominal drive;
- traction/slip observation;
- independent mechanical stop availability;
- unexpected yaw/differential-torque detection;
- immediate post-run retention and thermal inspection.

No rider, dog, pedestrian traffic, or public-road assumption belongs in this stage.

## Stage 4: rider-only very-low-speed closed-course commissioning

**Energized:** yes  
**Free ground travel:** yes  
**Rider:** yes  
**Dog:** no  
**Venue:** qualified controlled venue required

Stage 4 records ground speed, longitudinal acceleration, longitudinal jerk, stopping response, pack voltage/current, left/right phase current, remote/deadman propulsion decay, motor/controller temperatures, slip-control interventions, and fault logs.

It also requires a rider-only/no-dog/no-public-traffic plan, protective equipment and step-off plan, independent mechanical-brake fallback, and post-run health closure.

A Stage 4 pass is evidence for a future normal powered-operation contract. It is not that contract.

## Declared stage limits

Every manifest declares sourced limits for commanded speed, motor phase current, battery current, pack voltage, motor ERPM, motor temperature, and controller temperature.

These come from the final architecture and commissioning plan, not generic defaults.

The qualifier checks that they exist. Physical test execution is responsible for stopping before or at the declared stop limit.

## Required measurements

Stage-specific required metric IDs live in the dated snapshot. Measurement entries include metric ID, unit, source, and a finite summary value and/or evidence reference.

Stage 4 explicitly includes physical acceleration and jerk because software current slew is not a physical jerk measurement.

## Universal stop conditions

Stop the current stage for unexpected zero-command propulsion, non-conservative deadman/remote behavior, degraded mechanical braking, retention movement, structural damage, unexpected yaw torque, electrical/thermal limit exceedance, safety-relevant sensor disagreement, moving-sweep interference, abnormal vibration/grinding/smoke/odor/rapid heating, or a new lifecycle `STOP_USE` finding.

A stopped stage is investigated and repeated from a known healthy baseline. Do not loosen the stop rule because a run almost passed.

## Initialize a stage

Example Stage 0:

```bash
python tools/init_rev_c_powered_commissioning_stage.py \
  rider/private/commissioning/stage-0 \
  --stage-id BENCH_READINESS \
  --board-id X1-A \
  --configuration-id CFG-A \
  --power-architecture rider/private/power/final/power_authority.json \
  --pre-health-state rider/private/health/x1-a/health_state.json
```

Stage 1 additionally supplies `--previous-stage`. Stage 3 and Stage 4 also supply `--venue-authority`.

The initializer validates upstream fingerprints before creating the workspace.

## Qualify a stage

For an energized stage:

```bash
python tools/qualify_rev_c_powered_commissioning_stage.py \
  rider/private/commissioning/stage-1/commissioning_manifest.json \
  --power-architecture rider/private/power/final/power_authority.json \
  --pre-health-state rider/private/health/x1-a/pre_stage_health.json \
  --previous-stage rider/private/commissioning/stage-0/authority.json \
  --post-health-state rider/private/health/x1-a/post_stage_health.json \
  --out rider/private/commissioning/stage-1/authority.json
```

Stage 3 and Stage 4 additionally supply the venue authority.

A passing output is fingerprinted `x1_powered_commissioning_stage` authority for exactly one stage.

## Build-authority semantics

The graph distinguishes `prepare_powered_bench_readiness`, `conduct_secured_unloaded_spin`, `conduct_restrained_loaded_bench`, `conduct_rider_free_controlled_ground`, `conduct_rider_only_very_low_speed_commissioning`, and `powered_operation`.

The first five are commissioning capabilities. `powered_operation` remains hard-blocked.

## What Stage 4 does not authorize

Stage 4 does not authorize normal neighborhood riding, trail riding, public-road use, Worcester Park use, dog-accompanied riding, Shasta companion testing, high-speed operation, hill/descent endurance, wet/dirty powered riding, battery/charger changes, or controller tuning outside the qualified configuration.

## Exit condition for the Issue #45 software tranche

The software tranche is complete when Stage 0-4 contracts exist, stage order cannot be skipped, ground stages require fingerprinted venue evidence, all stages bind to exact architecture and health lineage, energized stages require post-stage READY health, required checks/measurements are machine validated, stop conditions prevent qualification, Stage 4 cannot authorize normal riding, and CI covers both passing and rejected synthetic lineages.

Physical commissioning remains future work until the prerequisite hardware authorities actually exist.
