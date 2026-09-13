# Worcester X1 topology decision tools

Status: **analysis support only**. These tools can reject a weak candidate early. They cannot qualify Issue #19, authorize a drivetrain purchase, or authorize powered operation.

Reusable blank structures live in `hardware/topology_analysis_templates_v1.json`.

## 1. Candidate A: shared rear V5 + rear drive axial screen

The first question is one-dimensional and cheap:

> Do the measured brake rotor, pad window, brake-arm sweep, wheel/hub stack, drive coupler and guard already occupy incompatible axial space?

Use one physical datum for every measurement. A suitable datum is a repeatable hanger/axle shoulder or other directly measurable surface. Do not mix dimensions referenced to different faces and then subtract them as if they shared a coordinate system.

Build a private config containing measured intervals:

```json
{
  "schema_version": 1,
  "scope": "brake_drive_axial_stack_analysis",
  "datum": "rear hanger outer face, outward positive",
  "components": [
    {"id": "pad_window", "start_mm": 0.0, "end_mm": 0.0},
    {"id": "rotor", "start_mm": 0.0, "end_mm": 0.0},
    {"id": "brake_arm_sweep", "start_mm": 0.0, "end_mm": 0.0},
    {"id": "drive_coupler", "start_mm": 0.0, "end_mm": 0.0},
    {"id": "drive_guard", "start_mm": 0.0, "end_mm": 0.0}
  ],
  "containment_rules": [
    {"child": "rotor", "container": "pad_window", "minimum_edge_margin_mm": 0.0}
  ],
  "separation_rules": [
    {"a": "brake_arm_sweep", "b": "drive_coupler", "minimum_gap_mm": 0.0}
  ]
}
```

The zeroes above are placeholders, not recommended clearances. Set margins before interpreting the result and justify them from measurement uncertainty, manufacturer clearance, motion, and consequence.

Run:

```bash
PYTHONPATH=. python tools/analyze_brake_drive_axial_stack.py \
  rider/private/topology/v1/axial_stack.json \
  --out rider/private/topology/v1/axial_stack_analysis.json
```

The result reports:

- rotor containment margin inside the pad window;
- positive gap between separated intervals;
- negative gap as overlap depth;
- explicit pass/fail for every declared rule.

### Interpretation

An axial failure is strong evidence to reject that configuration or redesign it before buying the drivetrain.

An axial pass is **not** Issue #19 evidence by itself. The layout can still fail through:

- steering or lean sweep;
- radial interference;
- brake-arm structural loading;
- cable routing;
- wheel service;
- guard impact path;
- drive retention;
- torque reaction.

The full physical topology gate remains authoritative.

## 2. Candidate B: rear V5 + front 2WD traction sensitivity

Front drive solves the rear axial packaging problem cleanly, but acceleration and uphill grade transfer normal load rearward.

`simulation/front_drive_traction.py` calculates the quasi-static front/rear normal forces and asks a more useful question than “will front drive work?”:

> What tire/terrain friction coefficient would front drive require in each mission scenario, and how does that compare with rear drive or AWD under the same assumptions?

Private config:

```json
{
  "schema_version": 1,
  "scope": "front_drive_traction_sensitivity",
  "total_mass_kg": 0.0,
  "wheelbase_m": 0.0,
  "cg_from_rear_m": 0.0,
  "cg_height_m": 0.0,
  "rolling_resistance_coeff": 0.0,
  "scenarios": [
    {
      "name": "measured_or_planned_case",
      "grade": 0.0,
      "acceleration_mps2": 0.0,
      "compare_mu": []
    }
  ]
}
```

Again, zeroes are placeholders. Use measured wheelbase and mass. CG location/height should come from measured or explicitly bounded load-distribution work rather than a convenient guess.

Run:

```bash
PYTHONPATH=. python simulation/front_drive_traction.py \
  rider/private/topology/v1/front_drive_scenarios.json \
  --out rider/private/topology/v1/front_drive_analysis.json
```

For each scenario the tool returns:

- grade angle;
- propulsion force demand;
- front and rear normal force;
- front/rear load fraction;
- required coefficient of friction for front drive;
- required coefficient for rear drive;
- required coefficient for AWD;
- optional force margins at user-supplied `compare_mu` values.

### Model equation

With wheelbase `L`, CG distance from the rear contact line `x`, CG height normal to the road `h`, grade angle `theta`, and forward acceleration `a`, the screening front normal force is:

```text
N_front = m [g cos(theta) x - (g sin(theta) + a) h] / L
```

So both uphill grade and forward acceleration reduce front normal load.

### Interpretation

Use this model to reject front drive when required friction becomes implausibly demanding across important mission cases.

Do not use it to qualify front drive. It omits:

- transient suspension/board flex;
- individual left/right wheel loading;
- loose-soil sinkage and bulldozing resistance;
- steering angle;
- bumps/roots;
- tire pressure effects;
- torque-vectoring/control behavior.

If Candidate B survives the sensitivity screen, it still needs low-energy physical traction/control evidence before Issue #19 can select it.

## 3. Brake fade: repeated-stop analysis with frozen criteria

A brake that passes one cool stop has not demonstrated repeated-stop performance.

`tools/analyze_brake_repeat_stops.py` is for a **controlled, low-energy, unpowered/external-motion** repeated-stop series. It explicitly rejects powered-test data because powered hill qualification belongs to a future authority.

The plan must be frozen before collection:

```json
{
  "schema_version": 1,
  "scope": "unpowered_repeated_stop_thermal_series",
  "plan_frozen_before_data": true,
  "powered_test": false,
  "test_plan": {
    "target_start_speed_mps": 0.0,
    "start_speed_tolerance_mps": 0.0,
    "baseline_stop_count": 2,
    "minimum_stop_count": 0,
    "max_deceleration_loss_fraction": 0.0,
    "max_rotor_peak_temp_c": 0.0
  },
  "stops": []
}
```

The zeroes are intentionally invalid placeholders. Decide the real low-energy protocol and thresholds before collecting data.

Each stop records:

```json
{
  "start_speed_mps": 0.0,
  "stop_distance_m": 0.0,
  "ambient_temp_c": 0.0,
  "rotor_temp_start_c": 0.0,
  "rotor_temp_peak_c": 0.0
}
```

Run:

```bash
PYTHONPATH=. python tools/analyze_brake_repeat_stops.py \
  rider/private/brake/v5-a/repeat_stops.json \
  --out rider/private/brake/v5-a/repeat_stop_analysis.json
```

The analyzer computes equivalent constant deceleration:

```text
a_eq = v_start^2 / (2 * stop_distance)
```

It uses the median of the predeclared baseline stops and reports subsequent deceleration loss plus rotor-temperature rise.

### Why equivalent deceleration

Raw stopping distance changes with start speed. Equivalent deceleration makes small accepted start-speed variation easier to compare without pretending the runs were identical.

### What this still does not prove

A low-energy repeated-stop pass does not reproduce the energy of a long powered descent. Before future powered hill work, the project still needs a duty-cycle-specific thermal/fade authority with appropriate energy, cooling, instrumentation, wear inspection, and conservative stop rules.

## 4. Evidence discipline

For every input to these tools, tag it in the private notes as one of:

- **MEASURED**: directly measured on the identified X1 hardware;
- **MANUFACTURER_REFERENCE**: published by the identified manufacturer/revision;
- **SENSITIVITY_ASSUMPTION**: deliberately varied hypothetical value.

Never silently promote a sensitivity assumption to measured geometry.

These tools follow one rule:

> A model may eliminate a bad idea cheaply. Only the named physical gate may promote a surviving idea.
