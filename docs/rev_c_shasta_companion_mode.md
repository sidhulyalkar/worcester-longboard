# Worcester X1 Rev-C Shasta companion mode

**Status:** control research only.  
**Physical authority:** none.  
**Powered-operation authority:** none.  
**Dog-accompanied operation:** not authorized.

Shasta mode is the future low-speed neighborhood mode for riding near a dog while keeping the board fully rider-controlled.

It is not an autonomous dog-following system and it is not a towing mode.

The design goal is predictable behavior when the rider is managing two independent systems at once:

1. the board;
2. a moving animal whose speed and lateral direction can change suddenly.

The correct control response is therefore conservative and boring.

## Core product rule

The dog must never become part of the board's steering or retention system.

The leash stays with the rider.

A leash attachment point on the board is prohibited.

That prevents a lateral dog impulse from becoming:

- a steering input;
- a board yaw moment;
- an enclosure/truck/deck structural load;
- a runaway-board tether;
- a reason for control software to compensate for an unpredictable external load.

## Current research envelope

The machine-readable source is:

`hardware/rev_c_shasta_mode_requirements.json`

The current host-control hypothesis is:

| Quantity | Provisional value |
|---|---:|
| Speed cap | 2.70 m/s |
| Acceleration limit | 0.45 m/s² |
| Regen deceleration limit | 0.80 m/s² |
| Phase-current limit | 18 A |
| Drive-current slew | 20 A/s |
| Regen-current slew | 30 A/s |
| Fault/deadman propulsion-release slew | 60 A/s |

These values are not a safety certification.

They are deliberately below the existing Learn-mode software envelope so future physical qualification begins conservatively.

## Current slew is not physical jerk

The controller currently limits current slew.

That is useful because motor torque is approximately related to motor current, but current slew is **not** a complete vehicle-jerk measurement.

Actual longitudinal jerk depends on:

- drivetrain ratio and efficiency;
- motor torque constant;
- tire deformation and slip;
- vehicle mass;
- grade;
- surface;
- backlash/compliance;
- controller inner-loop behavior;
- rider motion.

Therefore Issue #33 must eventually measure acceleration and jerk from the real vehicle.

Do not relabel the software current-slew limit as a validated comfort metric.

## Deadman and remote loss

Shasta mode requires a rider-held deadman input.

If the deadman is released or the remote goes stale:

- no new propulsion is accepted;
- propulsion current ramps toward zero with the bounded fault-release slew;
- independent mechanical braking is recommended;
- the controller does not pretend motor braking is the only stopping layer.

The fault-release slew is intentionally faster than normal companion-mode torque buildup.

A gentle ride mode must not create lingering propulsion after control is lost.

## Overspeed

If measured ground speed exceeds the provisional Shasta cap:

- positive throttle cannot increase propulsion;
- existing propulsion ramps toward zero with the fault-release slew;
- an overspeed fault is reported;
- independent mechanical braking is recommended.

The software speed cap is not a physical speed governor.

A downhill slope can accelerate an unpowered board beyond the software cap.

That is one reason independent mechanical stopping remains mandatory.

## Regen and battery limits

Regenerative braking is supplemental.

If pack voltage reaches the configured regen ceiling:

- regen command drops immediately to zero;
- mechanical braking is recommended.

The controller must not preserve a smooth regen ramp at the expense of charging into a pack state that forbids regen.

## Nominal left/right behavior

Shasta mode does not use deliberate differential carve assist.

With equal wheel state, equal thermal state, and no slip event, the nominal drive request remains symmetric.

Temporary left/right differences are allowed only for protective reasons such as:

- detected wheel slip;
- independent motor/controller thermal derate.

This is different from intentional steering torque.

## Lights

The control core emits a lighting request whenever Shasta mode is selected.

That request is only an interface contract.

It does not authorize a specific light, wiring harness, voltage converter, or installation.

A future lighting subsystem should be independently fused/protected and should not be required for traction control to function.

## Qualification ladder

### Stage 0: host software

Dog present: **no**  
Powered vehicle: **no**

Current work belongs here.

Host tests must cover:

- mode limits;
- drive-current slew;
- brake-current slew;
- deadman release;
- remote loss;
- overspeed behavior;
- regen removal at pack overvoltage;
- symmetric nominal output;
- lighting request.

Passing Stage 0 proves only that the software implements the declared research contract.

### Stage 1: bench / no rider

Dog present: **no**  
Road contact: **no**

A future bench setup should verify actual ESC/controller interpretation of:

- positive current commands;
- regen commands;
- command transitions;
- deadman loss;
- stale-sensor faults;
- lighting request;
- logging.

No road or dog is needed to discover protocol/sign/interface mistakes.

### Stage 2: rider-only closed low-speed course

Dog present: **no**  
Requires future powered authority: **yes**

Only after the full vehicle power architecture has independently passed its prerequisite gates.

Measure:

- real ground speed;
- longitudinal acceleration;
- longitudinal jerk;
- remote-release propulsion decay time;
- stopping response;
- regen-to-mechanical-brake transition;
- wheel slip;
- left/right current;
- temperatures;
- fault logs.

This stage determines whether the provisional software numbers produce the intended physical behavior.

### Stage 3: future companion-proximity test

Dog present: **yes**  
Authorized now: **no**

This stage needs its own explicit release after Stage 2 evidence is accepted.

The first companion experiment should not involve towing, leash attachment to the board, or deliberate lateral loading.

The purpose is to observe whether the already-qualified rider-controlled vehicle remains manageable in the presence of normal companion-speed variability.

## Initial acceptance questions for future Stage 2

Do not turn these into pass/fail numbers until the powered vehicle, brake system, and measurement stack are qualified.

The future rider-only program needs to answer:

- Does the board remain comfortably below the intended companion-speed envelope on the controlled test course?
- Does throttle onset feel progressive rather than step-like?
- Is measured jerk acceptably bounded?
- Does releasing the deadman remove propulsion promptly and predictably?
- Is braking predictable when regen is available?
- Is braking still predictable when regen is unavailable?
- Does the independent mechanical brake remain sufficient without motor braking?
- Does traction control avoid unexpected yaw impulses?
- Are thermal and voltage faults understandable to the rider?
- Can the rider step off cleanly at companion speeds?

## Fault priority

The companion mode should favor loss of propulsion over attempts to preserve ride feel.

Examples:

- stale ground-speed data: remove propulsion;
- stale remote: remove propulsion;
- deadman released: remove propulsion;
- thermal zero-derate point reached: no affected-side propulsion;
- pack overvoltage: no regen;
- overspeed: no new positive propulsion;
- uncertain carve/assist sensor state: no deliberate differential assist.

Failing smooth is secondary to failing conservative.

## Shasta mode is not autonomous

Explicit non-goals:

- dog following;
- dog tracking for steering;
- leash-force sensing for propulsion;
- autonomous pace matching;
- automatic steering around pedestrians;
- board-mounted leash anchoring;
- dog-powered towing;
- software-only stopping.

The rider remains responsible for steering, speed command, stopping, and leash control.

## Relationship to ride modes

The intended future hierarchy is roughly:

```text
Shasta
  lowest speed / lowest torque-change / no carve assist
     ↓
Learn
  rider training envelope
     ↓
Trail / Powder / Range
  mission-specific normal riding
     ↓
higher-performance research modes
```

The exact final mode set remains provisional until the traction system and powered commissioning program exist.

## Repository implementation

Research contract:

- `hardware/rev_c_shasta_mode_requirements.json`

Controller:

- `firmware/include/x1_control_core.hpp`
- `firmware/src/x1_control_core.cpp`

Host tests:

- `firmware/test/test_control_core.cpp`

Tracking issue:

- Issue #33

## Exit condition for this tranche

The current software tranche is complete when:

1. the host control core implements the research envelope;
2. host tests cover all declared fail-conservative behaviors;
3. requirements and docs agree with firmware;
4. CI passes;
5. the public repository still reports powered operation as blocked.

Nothing in this document authorizes a live dog-accompanied ride.
