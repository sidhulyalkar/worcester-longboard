# Worcester X1 telemetry flight recorder and commissioning replay

**Issues:** #47 and #49  
**Status:** evidence-quality architecture.  
**Powered-operation authority:** none.

Worcester X1 now uses one canonical telemetry contract for future powered commissioning, lifecycle health, range-model calibration, control debugging, and fault reconstruction.

The recorder is deliberately **not** part of the real-time safety loop.

If logging fails:

- the controller must continue to fail conservative according to its own control/fault logic;
- unsafe propulsion must never be preserved just to finish a log;
- the commissioning run may become unusable as evidence.

That separation is fundamental.

## 1. Data flow

```text
real-time controller / sensors
        |
        +---- control remains independent of logging
        |
        v
private raw streams + event log
        |
        v
seal exact file bytes by SHA-256
        |
        v
x1_telemetry_session validator
        |
        v
fingerprinted telemetry authority
        |
        v
commissioning replay
        |
        v
fingerprinted metric evidence
        |
        v
Issue #45 stage qualifier
```

A metric typed into a commissioning manifest is not enough for Stage 1-4.

The stage measurement must reference the exact evidence URI emitted by the telemetry replay report.

## 2. Private raw data

Actual telemetry belongs under:

`rider/private/`

Raw logs may contain:

- exact ride timing;
- location/route data if GNSS is later enabled;
- hardware serial information;
- rider motion;
- control inputs;
- faults;
- component behavior.

The public repository stores:

- signal definitions;
- schemas;
- validators;
- synthetic fixtures;
- replay logic;
- non-personal derived methods.

Do not commit real route or rider telemetry to the public repository.

## 3. Canonical stream families

The initial contract uses four periodic streams.

### Control

Examples:

- remote throttle;
- remote/deadman state;
- remote age;
- ride mode;
- left/right drive-current command;
- left/right regen-current command;
- traction-control scales;
- controller fault bits.

### Electrical / drivetrain

Examples:

- pack voltage;
- battery current;
- phase current;
- motor ERPM;
- future BMS state where available.

### Motion

Examples:

- independent ground speed;
- non-driven wheel speed;
- longitudinal acceleration;
- longitudinal jerk;
- IMU acceleration/gyro.

### Thermal

Examples:

- pack temperature;
- left/right motor temperature;
- left/right controller temperature.

These files may come from different devices and different clocks.

## 4. Do not assume clocks are aligned

Every stream declares:

- source-device ID;
- clock ID;
- timestamp unit;
- nominal sample rate;
- maximum accepted sample gap;
- synchronization method;
- affine clock scale;
- clock offset into session time;
- synchronization uncertainty;
- synchronization evidence reference.

The current normalized clock model is:

```text
session_time_s = raw_time_s * scale + offset_s
```

This can represent fixed offset and simple clock-rate correction.

A future more complex clock model should be introduced as a new schema version rather than silently changing this one.

## 5. Sequence gaps

Periodic streams use explicit sequence numbers.

A periodic sample gap may be represented only when:

1. the missing sequence range is declared in `dropped_sequence_ranges`;
2. the reason is recorded;
3. timestamps still satisfy the declared maximum-gap contract;
4. Stage-required stream overlap remains sufficient.

This allows evidence to say:

> two samples were lost and accounted for

instead of pretending they never existed.

The event log is stricter.

Event-log sequence gaps are not accepted, because losing a fault/deadman/stop marker can invalidate the interpretation of the entire run.

## 6. Event log

The initial JSONL event vocabulary includes:

- `SESSION_START`
- `SESSION_STOP`
- `STAGE_START`
- `STAGE_STOP`
- `DEADMAN_TRANSITION`
- `REMOTE_STALE`
- `FAULT_TRANSITION`
- `MECHANICAL_BRAKE_MARKER`
- `STOPPING_TEST_START`
- `OPERATOR_STOP`
- `ANOMALY`

The telemetry manifest declares every event type the logger supports.

Every recorded event declares:

- sequence;
- timestamp;
- event type;
- source ID;
- structured details.

## 7. Signal provenance

The canonical signal registry is:

`hardware/x1_telemetry_signal_registry_2026-10-02.json`

Every signal declaration identifies its source.

Derived signals also identify their derivation.

A calibration ID may be recorded, but telemetry validation **does not prove the physical calibration is correct**.

For example, a ground-speed signal can pass:

- file integrity;
- timestamp integrity;
- provenance declaration;
- synchronization;

while still requiring separate physical calibration/validation before it is trusted as a safety measurement.

## 8. Start a session

After the final power architecture exists:

```bash
python tools/init_x1_telemetry_session.py \
  rider/private/telemetry/stage-1-run-01 \
  --board-id X1-A \
  --configuration-id CFG-A \
  --stage-id SECURED_UNLOADED_SPIN \
  --started-at-utc 2026-10-02T20:00:00Z \
  --power-architecture rider/private/power/final/power_authority.json
```

The initializer verifies the fingerprinted power architecture.

It creates:

- `telemetry_manifest.json`;
- four CSV stream files;
- `events/events.jsonl`;
- a private workspace manifest.

Before recording, replace all source/clock/synchronization placeholders with the actual acquisition configuration.

## 9. Record without blocking control

The logger implementation must never be allowed to:

- delay the motor-control loop;
- hold the last command because storage is busy;
- suppress a fault because an event cannot be written;
- make propulsion conditional on successful SD/network logging;
- retry storage indefinitely in a real-time path.

A recorder should buffer asynchronously and account for loss.

The fail-safe behavior remains in the controller.

## 10. Seal the session

After acquisition is complete:

```bash
python tools/seal_x1_telemetry_session.py \
  rider/private/telemetry/stage-1-run-01/telemetry_manifest.json \
  --ended-at-utc 2026-10-02T20:01:00Z
```

Sealing computes SHA-256 for every raw stream and the event log.

Do not edit raw files after sealing.

Any later byte change causes validation or replay to fail.

## 11. Validate

```bash
python tools/validate_x1_telemetry_session.py \
  rider/private/telemetry/stage-1-run-01/telemetry_manifest.json \
  --power-architecture rider/private/power/final/power_authority.json \
  --out rider/private/telemetry/stage-1-run-01/telemetry_authority.json
```

The validator checks:

- exact raw-file hashes;
- schema;
- stage identity;
- board/configuration identity;
- power-architecture fingerprint;
- signal registry membership;
- signal family;
- source provenance;
- derivation identity where required;
- finite values;
- monotonic timestamps;
- monotonic sequence numbers;
- declared sequence drops;
- maximum stream gaps;
- clock/sync metadata;
- required Stage signal coverage;
- required event coverage;
- cross-stream overlap.

The initial required-stream overlap threshold is 90% of the declared session duration.

A passing output is:

`x1_telemetry_session`

It explicitly does **not** prove:

- physical sensor calibration;
- commissioning-stage success;
- vehicle safety;
- normal powered-operation authority.

## 12. Replay commissioning metrics

After telemetry validation:

```bash
python tools/summarize_x1_commissioning_telemetry.py \
  rider/private/telemetry/stage-4-run-01/telemetry_manifest.json \
  --telemetry-authority rider/private/telemetry/stage-4-run-01/telemetry_authority.json \
  --out rider/private/telemetry/stage-4-run-01/commissioning_replay.json
```

The replay tool re-hashes the raw files before using them.

A changed file invalidates replay even if an older telemetry authority existed.

The replay output is:

`x1_commissioning_telemetry_replay`

## 13. Raw versus derived commissioning evidence

Most commissioning measurements simply reference a validated time series.

Examples:

- `pack_voltage_v`
- `battery_current_a`
- phase current;
- motor ERPM;
- motor/controller temperatures;
- ground speed;
- longitudinal acceleration;
- longitudinal jerk.

The replay report stores:

- source signal;
- sample count;
- min/max/mean summary;
- evidence URI.

The stage qualifier uses the evidence URI rather than accepting an unrelated typed summary.

### Deadman propulsion decay

For Stage 3/4, the current replay method finds:

1. `DEADMAN_TRANSITION(active=false)`;
2. synchronized left/right positive drive-current commands;
3. the first time both are at or below the declared replay threshold.

It reports the maximum decay time across recorded release trials.

This is commanded propulsion decay, not proof of actual tire force reaching zero.

### Stopping distance

For Stage 4, the current method:

1. begins at `STOPPING_TEST_START`;
2. integrates the absolute independent ground-speed signal;
3. stops after speed remains under the declared stopped threshold for the declared dwell time;
4. reports the maximum derived stopping distance across trials.

This result is only as physically meaningful as the underlying ground-speed calibration and marker procedure.

## 14. Issue #45 integration

Stage 0 is non-energized and does not require telemetry replay.

Stage 1-4 do.

Each energized stage must now link:

```text
sealed raw files
  -> x1_telemetry_session
  -> x1_commissioning_telemetry_replay
  -> x1_powered_commissioning_stage
```

The stage manifest includes the exact telemetry replay fingerprint.

Every required Stage measurement must match the replay:

- metric ID;
- unit;
- evidence URI;
- replay-derived numeric value when one exists.

A copied value with a different evidence reference cannot qualify.

## 15. Lifecycle integration

Issue #41 remains the vehicle-health authority.

Telemetry can later produce lifecycle inputs such as:

- accumulated ride hours;
- odometer distance;
- repeated thermal events;
- fault-event history;
- unexpected slip/control interventions;
- impact/anomaly markers.

But telemetry must not silently mutate lifecycle health.

A future bridge should create explicit lifecycle events that remain inspectable and closable under the Issue #41 event history.

## 16. Range-model calibration

Telemetry eventually provides the data needed to replace planning Wh/mi assumptions with X1-specific empirical distributions.

Useful channels include:

- battery energy/current/voltage;
- independent distance/ground speed;
- terrain/session label;
- total mass/configuration ID;
- tire setup;
- temperature.

Do not overwrite the planning model from one ride.

Use repeated, configuration-specific evidence.

## 17. Fault reconstruction

A useful black box should answer:

- what did the rider/remote command?
- what did the controller command?
- what did each motor/controller report?
- what did the independent ground reference observe?
- what were voltage/current/thermal states?
- which fault bit changed first?
- did deadman/remote loss precede propulsion decay?
- were samples dropped?
- how certain is cross-device synchronization?

This is more valuable than a dashboard that merely looks polished.

## 18. Current authority boundary

A passing telemetry session or replay report still has:

```text
commissioning_stage_qualified = false
powered_operation_authorized = false
public_operation_authorized = false
dog_accompanied_operation_authorized = false
```

Only the separate Issue #45 qualifier can decide whether the complete stage evidence passes.

And even Stage 4 remains commissioning evidence, not normal-use authority.
