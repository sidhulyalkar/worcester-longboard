# Worcester X1 Rev-C powertrain envelope

**Status:** pre-purchase architecture rejection/qualification tool.  
**Issue:** #43.  
**Drive selected:** no.  
**Motor selected:** no.  
**Voltage selected:** no.  
**Powered-operation authority:** none.

The final propulsion system should not be chosen by starting with a motor SKU and asking whether the rest of the board can tolerate it.

Issue #43 works in the opposite direction.

Start with the physical vehicle state and the mission:

- mass;
- wheel diameter;
- wheelbase and CG;
- selected brake/drive topology;
- target grades;
- target acceleration;
- target speed;
- plausible traction;
- range/energy architecture.

Then ask which motor/ratio/voltage/current combinations survive all declared constraints.

This is a rejection-first model.

## 1. Why the old fixed sizing script is insufficient

`simulation/x1_dynamics.py` remains a useful historical first-order sanity check, but it embeds a fixed 160 KV / 7:1 / 12S-style architecture.

Rev-C intentionally does not inherit those values.

The new solver:

`simulation/rev_c_powertrain_envelope.py`

accepts the relevant quantities explicitly.

It does not contain a hidden X1 motor, gear ratio, voltage, current limit, or controller selection.

## 2. Current MBS reference facts

The dated source snapshot is:

`hardware/rev_c_powertrain_reference_snapshot_2026-10-01.json`

The current MBS G1 reference provides useful mechanical facts:

- 64-tooth helical wheel gear;
- Matrix III 70 mm axle requirement;
- common four-hole 44 mm diagonal motor-adapter pattern;
- motor sold separately;
- motor gear sold separately.

The current MBS Agent reference uses a stock 15:64 ratio and lists 13T and 17T alternate helical motor gears.

Those facts make 13/15/17-tooth pinions useful ratio-study points.

They do **not** select:

- G1;
- 64T;
- 13T;
- 15T;
- 17T;
- an MBS Agent motor;
- 18S;
- an Agent ESC;
- or any Agent battery

for Worcester X1.

The current MBS references used here do not publish enough motor/controller details to populate X1 KV, pole-pair, current, or ERPM limits without another authoritative source.

Do not infer them from board top-speed or power claims.

## 3. Input model

The public input template is:

`hardware/rev_c_powertrain_envelope_template.json`

### Vehicle state

Required:

- total mass;
- wheelbase;
- CG position from the rear contact line;
- CG height;
- wheel diameter;
- rolling-resistance coefficient.

Optional:

- aerodynamic drag area;
- air density.

Once Issue #21 exists, the final candidate study should use the measured inert-pack vehicle state rather than an early catalog mass guess.

### Candidate propulsion state

Required:

- propulsion topology: front, rear, or AWD;
- motor count;
- motor KV;
- motor pole pairs;
- wheel gear teeth;
- motor gear teeth;
- nominal voltage;
- full voltage;
- declared speed-voltage basis;
- phase-current limit per motor;
- total battery-current limit;
- controller ERPM limit;
- drivetrain efficiency assumption;
- electrical efficiency assumption.

Optional:

- total electrical power limit.

A missing current, KV, pole-pair, voltage, or ERPM limit invalidates the configuration.

That is preferable to silently inserting a generic VESC number.

## 4. Scenario model

Each scenario declares:

- grade;
- target speed;
- target acceleration;
- assumed tire/terrain friction coefficient.

The candidate qualifier requires at least:

1. `flat_cruise`;
2. `grade_climb`;
3. `low_speed_accel`.

The actual values are not frozen by this document.

They should reflect the final X1 mission rather than a benchmark board's headline specification.

## 5. Longitudinal force model

For road/trail grade represented as decimal rise/run:

```text
theta = atan(grade)

F_grade = m g sin(theta)
F_roll  = Crr m g cos(theta)
F_accel = m a
F_aero  = 0.5 rho CdA v^2

F_required = F_grade + F_roll + F_accel + F_aero
```

This is a first-order longitudinal model.

It does not include:

- tire sinkage;
- deep loose-soil bulldozing;
- obstacle impact force;
- wheel hop;
- suspension transients;
- lateral cornering demand;
- rider pumping;
- detailed drivetrain inertia.

Use it to reject obviously inadequate candidates, not to certify terrain performance.

## 6. Wheel and motor torque

Total required wheel torque:

```text
T_wheel = F_required * wheel_radius
```

For:

```text
ratio = wheel_gear_teeth / motor_gear_teeth
```

the idealized per-motor torque is:

```text
T_motor_each =
  T_wheel /
  (motor_count * ratio * drivetrain_efficiency)
```

A larger numerical reduction ratio therefore reduces required motor torque and idealized phase current for the same wheel force.

It also spins the motor faster at the same vehicle speed.

There is no free torque.

## 7. KV and idealized Kt

For a declared motor KV:

```text
Kt_ideal = 60 / (2 pi KV)
```

Then:

```text
I_phase_ideal = T_motor_each / Kt_ideal
```

This is only a planning proxy.

It does not model:

- winding resistance;
- saturation;
- temperature-dependent resistance;
- controller modulation limits;
- field weakening;
- motor inductance;
- current-control dynamics;
- manufacturing tolerance.

The candidate's real motor/current envelope must come from its actual source.

## 8. Phase current is not battery current

This distinction is deliberate.

VESC documentation describes motor current and battery/input current separately. At lower duty cycle, high motor current can coexist with substantially lower battery current.

Issue #43 therefore never sets:

```text
battery current = motor phase current
```

Instead the first-order power estimate is:

```text
P_wheel = F_required * speed

P_battery_est =
  P_wheel /
  (drivetrain_efficiency * electrical_efficiency)

I_battery_est =
  P_battery_est / battery_voltage
```

The solver reports estimates at nominal and full voltage and uses nominal voltage for the declared battery-current check.

This still is not a controller configuration.

Real VESC duty/current behavior, motor losses, pack sag, BMS behavior and controller losses require the selected hardware.

## 9. Speed, motor RPM and ERPM

At target ground speed:

```text
wheel_rpm =
  vehicle_speed / wheel_circumference * 60

motor_rpm = wheel_rpm * ratio

ERPM = motor_rpm * motor_pole_pairs
```

The controller ERPM limit is a candidate-specific input.

Do not use one universal VESC ERPM value.

VESC hardware limits differ by controller.

## 10. Geometric no-load speed ceiling

For a declared KV and voltage:

```text
motor_no_load_rpm = KV * voltage
wheel_no_load_rpm = motor_no_load_rpm / ratio
```

The solver reports nominal- and full-voltage geometric no-load speeds.

If the target speed exceeds the selected voltage-basis no-load speed, the candidate is rejected.

Passing this check does **not** predict that the board will reach that speed under load.

Real speed margin must pay for:

- winding voltage drop;
- controller duty limit;
- torque demand;
- battery sag;
- terrain;
- aero;
- thermal derating.

No-load speed is an impossibility screen, not a ride-speed claim.

## 11. Traction and topology

The solver carries the same first-order pitch/load-transfer concept used by:

`simulation/front_drive_traction.py`

Positive uphill acceleration and grade unload the front axle.

For the candidate topology:

- front drive uses front normal load;
- rear drive uses rear normal load;
- AWD uses total normal load.

Then:

```text
mu_required =
  F_required / driven_normal_force
```

and:

```text
traction_margin =
  assumed_mu * driven_normal_force
  - F_required
```

This is especially useful when comparing front-drive versus rear-drive solutions to the Issue #19 brake packaging problem.

It is not a soil-mechanics model.

## 12. Ratio sweep

For a fixed wheel gear:

```bash
python simulation/rev_c_powertrain_envelope.py \
  rider/private/powertrain/candidate-a/envelope.json \
  --sweep-pinions 13 15 17 \
  --out rider/private/powertrain/candidate-a/ratio_sweep.json
```

A smaller pinion with the same wheel gear:

- increases reduction ratio;
- reduces required idealized motor torque/current for the same wheel force;
- increases motor RPM/ERPM at the same ground speed;
- reduces geometric no-load ground speed.

A larger pinion does the reverse.

Battery power for the same wheel force and ground speed does not disappear just because the ratio changes.

The ratio sweep reports all trade-offs and makes **no selection**.

## 13. Candidate source discipline

The architecture-qualification manifest is:

`hardware/rev_c_powertrain_candidate_template.json`

It requires explicit references for:

- KV;
- pole pairs;
- phase-current limit;
- battery-current limit;
- controller ERPM limit;
- nominal/full voltage;
- motor mount and shaft;
- wheel gear;
- motor gear;
- drivetrain efficiency basis;
- electrical efficiency basis;
- rolling-resistance basis;
- traction-mu basis.

"Study assumption" is acceptable for an assumption such as efficiency or terrain friction when labeled clearly.

It is not a substitute for a real controller hardware limit or battery-builder current limit.

## 14. Upstream physical linkage

A candidate cannot qualify unless it links to the exact fingerprinted:

- `x1_rolling_chassis_physical`;
- `x1_brake_drive_topology`;
- `x1_dummy_pack_mount`.

The Issue #19 selected topology must match the propulsion topology.

Current mapping:

```text
same_rear_axle_v5_plus_drive
  -> rear

rear_v5_front_2wd
  -> front

rear_2wd_front_friction_brake
  -> rear

alternate_drive_on_brake_first_rear
  -> rear
```

If Issue #19 later introduces another topology, add it explicitly.

Do not silently map an unknown topology.

## 15. Candidate qualification

After filling a sourced candidate manifest:

```bash
python tools/qualify_rev_c_powertrain_candidate.py \
  rider/private/powertrain/candidate-a/manifest.json \
  --chassis-authority \
    rider/private/chassis/donor-a/chassis_authority.json \
  --topology-authority \
    rider/private/topology/v1/topology_authority.json \
  --dummy-pack-authority \
    rider/private/dummy_pack/v1/dummy_pack_authority.json \
  --out rider/private/powertrain/candidate-a/authority.json
```

A passing report is:

`x1_powertrain_envelope_candidate`

It fingerprints:

- candidate;
- topology;
- ratio;
- entire envelope configuration;
- recomputed analysis;
- upstream physical authorities;
- source references.

## 16. What qualification actually means

A passing Issue #43 candidate means:

> the sourced candidate is internally consistent with the linked physical vehicle/topology state and passes the declared first-order scenarios.

It does **not** mean:

- motor thermal qualification;
- ESC thermal qualification;
- battery qualification;
- BMS qualification;
- controller-current settings are safe;
- real loose-surface traction is proven;
- range is proven;
- brake blending is proven;
- the drivetrain physically fits beyond Issue #19 evidence;
- hardware may be ordered;
- powered operation is authorized.

Every report therefore keeps:

```text
thermal_qualification = false
physical_authority = false
procurement_authority = false
controller_configuration_authority = false
battery_configuration_authority = false
powered_operation_authorized = false
```

## 17. Thermal boundary

A motor can satisfy a peak current calculation and still overheat.

An ESC can satisfy a peak current calculation and still overheat.

A battery can satisfy an instantaneous power calculation and still suffer unacceptable temperature rise or voltage sag.

Continuous thermal performance depends on:

- exact motor winding;
- exact motor thermal path;
- airflow;
- gearbox/belt losses;
- ambient temperature;
- enclosure;
- controller cooling;
- battery internal resistance;
- duty cycle;
- repeated grade duration;
- rider behavior.

Issue #43 intentionally refuses to invent a thermal model before those things exist.

A later powered bench/commissioning program must measure temperatures and derating.

## 18. Relationship to energy/range planning

`simulation/rev_c_energy_planner.py` answers a different question:

> How much energy does a mission plausibly require under planning Wh/mi assumptions?

Issue #43 asks:

> Can this propulsion candidate produce the declared force/speed envelope without violating its sourced first-order current, power, ERPM, and traction assumptions?

Both are needed.

Neither predicts final real-world range before telemetry.

## 19. Relationship to final power freeze

The build graph now requires:

```text
Issue #19 topology
        |
        v
Issue #21 inert dummy-pack state
        |
        +--> Issue #39 inert environmental candidate
        |
        +--> Issue #43 sourced powertrain-envelope candidate
        |
        v
final power architecture freeze
```

Issue #43 therefore stops the project from freezing a motor/ratio/voltage combination merely because the parts physically fit.

Likewise, passing Issue #43 cannot bypass Issue #39, the lifecycle-health program, procurement policy, or future powered commissioning.

## 20. Exit condition

Issue #43 architecture tooling is complete when:

1. reference facts are dated and source-backed;
2. no KV/current/ERPM limits are inferred from marketing performance;
3. simulator separates phase and battery current;
4. force, torque, power, RPM/ERPM, no-load speed and traction are coupled;
5. ratio sweep reports trade-offs without selecting a winner;
6. candidate values have explicit provenance;
7. flat-cruise, grade-climb and low-speed-acceleration scenarios all pass;
8. candidate is tied to the real chassis/topology/dummy-pack fingerprints;
9. output is fingerprinted;
10. final power freeze requires that output;
11. thermal, controller, battery, procurement and powered-operation authority remain false.
