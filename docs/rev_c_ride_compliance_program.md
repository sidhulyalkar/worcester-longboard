# Worcester X1 Rev-C ride-compliance program

**Status:** experimental protocol.  
**Authority:** analysis only.  
**Powered riding:** not authorized.

This program turns snowboard-like trail feel into measurable, reversible experiments. The goal is not maximum softness. It is progressive lean-to-turn response, low trail chatter, predictable recentering, useful edge leverage, low fatigue, and enough stability that the board does not feel nervous.

## Tuning order

Rev-C should exhaust lightweight compliance before adding mass or structural complexity:

1. stock pneumatic tire setup;
2. Matrix III shock-block position;
3. wheelbase where the chassis permits adjustment;
4. real deck and footbed behavior;
5. alternate shock-block hardness;
6. higher-volume wheel architecture;
7. independent suspension only after a measured failure of the preceding stack.

That order prevents solving an unknown handling problem with kilograms.

## Current Matrix III tuning reference

The dated facts snapshot is `hardware/rev_c_ride_compliance_snapshot_2026-10-01.json`.

MBS describes the soft 78A Matrix III block with the inside position as the maximum-carve direction, including lightweight-rider use cases, and the outside position as a more balanced carve/stability setup. The 400 mm brake-compatible Matrix III reference ships with soft blocks outside.

MBS Agent references use medium/orange blocks inside as a carvey electric setup and describe moving them outside for more high-speed stability. Hard/red 95A blocks are strongly stability biased. Those alternatives remain later tuning purchases, not things to buy before testing the stock hardware.

## Safety and test boundary

The first campaign uses a selected and physically qualified **unpowered** chassis. Do not use powered propulsion, traffic, a steep hill, a leash, a dog, or another moving subject to generate the test.

Use a repeatable low-energy course, fixed IMU mount, the same shoes/rider interface, appropriate protective equipment, and a controlled unpowered start. Keep the IMU orientation fixed; the analyzer treats `accel_z_mps2` as the axis normal to the deck.

## Initialize a private session

```bash
python tools/init_rev_c_ride_compliance_session.py \
  rider/private/ride_compliance/session-01
```

This creates `ride_compliance_manifest.json`, six empty sensor CSV files, `rider_observations.csv`, and a non-authoritative workspace manifest.

Actual ride data stays under `rider/private/`.

## Sensor and observation provenance

Before collecting runs, fill these manifest fields with the actual setup:

- `imu_source_id`;
- `imu_mount_id`;
- `speed_source_id`;
- `speed_source_calibrated=true` only after the chosen speed reference has been checked;
- `sensor_timebase_aligned=true` only after speed and IMU timestamps are demonstrably aligned;
- `tire_pressure_approved_range_kpa` from the selected tire/wheel manufacturer's documentation;
- `course_id` and `surface_description`.

The analyzer will not accept placeholder provenance.

The separate `rider_observations.csv` must contain exactly one row per sensor run. It is evidence, not an optional diary.

## Sensor data contract

Each run CSV uses:

```text
time_s
speed_mps
accel_z_mps2
gyro_roll_dps
gyro_yaw_dps
```

The analyzer reports mean speed, speed variability, deck-normal acceleration RMS, p95 and peak, roll-rate RMS, yaw-rate RMS, yaw/roll RMS ratio, and roll/yaw correlation.

The last two are descriptive lean-to-turn proxies only. They are not handling scores.

## Comparison gates

A valid comparison requires the same course, unchanged IMU mount, at least three valid runs per setup, minimum duration/sample counts, target-speed matching, bounded within-run speed variation, configuration median-speed matching to baseline, exactly one declared primary setup variable changed from baseline, and a separate rider observation for every run.

This prevents a slower pass from appearing smoother simply because it was slower.

## Experiment A: stock baseline

Record the exact chassis, tire family, measured front/rear pressure, shock-block ID and position, wheelbase, deck, and footbed/binding interface. Perform at least three runs and do not tune anything until baseline repeats are internally consistent.

## Experiment B: tire pressure

Tire pressure is the first compliance variable because it adds no structural mass. Use only values inside the tire/wheel manufacturer's approved operating range.

For the initial block, keep front and rear pressure equal, change pressure only, keep every other setting fixed, and run at least three repeats per pressure.

Do not assume the lowest pressure is best. Observe vibration attenuation, steering delay, tire squirm, rim protection, rolling resistance, and loose-surface behavior. The repository deliberately does not invent a PSI/kPa target before the selected tire/wheel system is physically known.

## Experiment C: Matrix III block position

Return to the chosen pressure baseline. With the same shock-block hardness, compare documented outside versus inside position and change nothing else.

Record how quickly steering begins with lean, whether the board recenters naturally, whether carve initiation is progressive or abrupt, and whether rough-surface inputs create unwanted steering.

## Experiment D: wheelbase

If Pro Warren III is selected, its published 910-970 mm range enables a controlled 910 / 940 / 970 mm block while pressure and truck tuning stay fixed. Do not combine wheelbase and shock-block changes in one comparison.

## Experiment E: real deck and footbed behavior

The cardboard stance experiment cannot measure real deck flex. On a received chassis, record deck liveliness, high-frequency foot vibration, deep-knee loading feel, local pressure/fatigue, and whether rebound feels progressive or springy.

Do not collapse these observations into one comfort number.

## When to buy another shock-block hardness

Only buy another hardness if stock block-position tuning leaves a named deficiency, such as excessive steering effort, poor centering, or a wheel/tire change that pushes steering outside the useful range. New hardware should close a measured gap, not create a branch just to try.

## When to reopen Explorer 200x70

Reopen the high-volume wheel branch only if 200x50 shows a measured conformity, chatter, flotation, or loose-surface problem after valid pressure tuning. Current trade analysis shows roughly 2.7 lb extra across four Explorer tires versus T1 before hub-mass delta, plus a wheel-family/brake-interface change.

## When to reopen 9-inch

The current T2 reference buys only about 12.5 mm nominal axle-height gain over the 194 mm T1 reference while adding roughly 3.08 lb across four tires before hub conversion. It should answer a measured ground-clearance problem.

## When to reopen independent suspension

Independent suspension is the last branch. Reopen it only after tire pressure, Matrix tuning, wheelbase where available, rider interface, and any justified high-volume tire branch still leave a concrete intended-terrain failure such as repeated wheel-contact loss or unacceptable deck-normal shock.

If reopened, suspension becomes a new chassis architecture with its own mass, braking, steering, retention, and packaging qualification. Do not bolt an improvised suspension layer onto the qualified chassis.

## Rider observations stay separate

`rider_observations.csv` records carve response, trail chatter, recentering, steering effort, stability, foot fatigue, confidence, emergency step-off behavior, and notes.

Use consistent wording or scales within a session, but do not sum those columns into one score. Objective smoothness is not the same thing as enjoyable handling.

The actual multi-objective question is: **which setup reduces unwanted terrain shock while preserving progressive, controllable lean-to-yaw response?**

## Analyze a session

```bash
python tools/analyze_rev_c_ride_compliance.py \
  rider/private/ride_compliance/session-01/ride_compliance_manifest.json \
  --out rider/private/ride_compliance/session-01/analysis.json
```

A valid report still has `physical_authority=false`, `procurement_authority=false`, and `powered_operation_authorized=false`.

## Dog-accompanied riding boundary

Do not involve Shasta in setup experiments. Dog-accompanied operation is a later mode, after steering, stopping, and low-speed acceleration/jerk are independently qualified. The compliance campaign should never use a leash or dog as part of the experimental load.

## Exit condition

The lightweight compliance stack is adequately explored when stock baseline is repeatable, tire pressure has a useful region, stock shock-block position has been compared, wheelbase has been tested when adjustable, objective and rider observations identify any remaining deficiency consistently, and every proposed new hardware purchase can be tied to that named deficiency.

At that point a new elastomer, larger tire, or suspension study becomes an engineering decision rather than accessory shopping.
