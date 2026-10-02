# Worcester X1 Rev-C lifecycle health, preflight, and maintenance

**Status:** lifecycle evidence architecture.  
**Issue:** #41.  
**Powered-operation authority:** none.  
**Public-operation authority:** none.  
**Dog-accompanied-operation authority:** none.

Worcester X1 now treats maintenance state as part of the vehicle configuration.

A board can be mechanically well designed and still become unsafe because:

- a wheel nut moved;
- a brake cable slipped;
- a bearing developed play;
- a skid strike shifted a mount;
- mud blocked a drain;
- a connector was serviced incorrectly;
- a component was replaced but the old inspection history was silently reused;
- a serious finding was noticed once and then forgotten.

Issue #41 turns those events into an append-only longitudinal record.

The key rule is:

> **healthy does not mean authorized.**

`READY_FOR_ALLOWED_ACTIVITY` means only that the recorded current configuration has no unresolved lifecycle blockers and has passed the required current preflight.

The intended activity must still be allowed independently by the build-authority, environmental, venue, public-use, and companion rules.

## 1. When lifecycle tracking starts

Lifecycle tracking begins after the physical rolling chassis has qualified.

That gives the health record a stable physical anchor:

`x1_rolling_chassis_physical`

The private component registry stores that exact authority fingerprint.

The lifecycle evaluator verifies the fingerprint every time it computes health state.

This prevents a maintenance log from one donor chassis being copied onto another board.

## 2. Health states

### READY_FOR_ALLOWED_ACTIVITY

Requirements:

- lifecycle evidence is valid;
- no open `STOP`, `SERVICE`, or `INSPECT` findings remain;
- no sourced service interval is due;
- no declared service interval has unknowable due state because required counters are missing;
- the latest event is a complete `PREFLIGHT`;
- all required checks for the current component set and declared activity pass.

This state grants no operation authority.

### INSPECTION_REQUIRED

Examples:

- no preflight exists;
- the latest event is a post-activity record, service event, component change, or impact;
- an `INSPECT` finding is still open;
- a sourced service interval exists but its required counter is unavailable;
- a conditional preflight item is missing.

The next step is inspection, not assumption.

### SERVICE_REQUIRED

Examples:

- a `SERVICE` finding is open;
- a manufacturer or qualified-X1 service interval has come due.

After service, the health state still does not jump directly to READY.

A fresh preflight is required.

### STOP_USE

Examples:

- critical witness-mark movement;
- wheel-retention change;
- new structural crack or permanent deformation;
- independent mechanical brake unavailable or materially degraded;
- steering binding or unexpected mechanical interference;
- another explicitly recorded `STOP` finding.

A later green preflight cannot erase a STOP finding.

It must be explicitly closed in an inspection, service, component-replacement, or configuration-change event, followed by a fresh preflight.

## 3. Private workspace

Once a rolling-chassis authority exists:

```bash
python tools/init_x1_lifecycle_health.py \
  rider/private/health/x1-a \
  --board-id X1-A \
  --configuration-id CFG-A \
  --created-at-utc 2026-10-01T12:00:00Z \
  --rolling-chassis-authority \
    rider/private/chassis/donor-a/chassis_authority.json
```

The initializer verifies the upstream chassis authority before creating any workspace.

It creates:

```text
rider/private/health/x1-a/
  component_registry.json
  event_template.json
  events/
  workspace_manifest.json
```

Exact serials, maintenance history, measurements, ride history, photos, and later telemetry stay private.

## 4. Component registry

Populate `component_registry.json` from the actual installed hardware.

Use stable IDs.

Examples:

- `DECK-A`
- `TRUCK-F-A`
- `TRUCK-R-A`
- `WHEEL-FL-A`
- `WHEEL-FR-A`
- `BRAKE-A`
- `SKID-R-A`
- `ENCLOSURE-A`
- future `BATTERY-A`
- future `ESC-A`
- future `REMOTE-A`

Each installed component records:

- subsystem;
- role;
- manufacturer;
- model;
- revision;
- private serial/identifier when useful;
- install timestamp;
- odometer/ride-hour counters if those counters exist;
- sourced service policy.

Do not invent service intervals.

A component can have no interval at all until a real source exists.

Accepted service-interval sources are:

- selected component manufacturer;
- selected system integrator or battery builder;
- later qualified X1 physical evidence.

If a service interval exists, record the source.

## 5. Event history is append-only

Do not overwrite yesterday's inspection because the board looks better today.

Create a new event.

Supported event types:

- `BASELINE`
- `PREFLIGHT`
- `POST_ACTIVITY`
- `INSPECTION`
- `SERVICE`
- `COMPONENT_REPLACEMENT`
- `CONTAMINATION_EXPOSURE`
- `IMPACT`
- `FAULT`
- `CONFIGURATION_CHANGE`

Generate a new event skeleton:

```bash
python tools/new_x1_health_event.py \
  rider/private/health/x1-a/component_registry.json \
  rider/private/health/x1-a/events/0001-preflight.json \
  --event-id PREFLIGHT-0001 \
  --timestamp-utc 2026-10-01T13:00:00Z \
  --event-type PREFLIGHT \
  --activity-type UNPOWERED_CONTROLLED_TEST
```

After the board has changed configuration, pass the current configuration ID explicitly:

```bash
  --configuration-id CFG-B
```

## 6. Core preflight

The required core checks are:

### Tire pressure and visible condition

Record actual pressure using the selected tire's approved range.

Check:

- all tires;
- visible cuts/bulges;
- bead condition;
- valve accessibility;
- unexpected pressure loss since the previous known state.

Do not use one generic X1 pressure forever.

Issue #28 ride-compliance work and the selected tire manufacturer define the valid tuning range.

### Wheel retention and axial play

Check:

- retention hardware;
- witness marks where applicable;
- unexpected wheel movement;
- spacer/stack condition;
- new axial play.

Any retention change is a STOP-level condition until understood.

### Bearing spin, noise, and play

Check for change from the established baseline:

- roughness;
- drag;
- noise;
- radial or axial play.

A new change is at least an inspection finding.

### Independent mechanical brake

Verify:

- available actuation;
- expected lever/actuator travel;
- release;
- no unexpected drag;
- cable/hose retention;
- no visible damage or contamination.

The friction brake remains an independent stopping layer.

A materially unavailable brake is STOP USE.

### Steering return and free motion

Verify:

- smooth left/right motion;
- expected return;
- no binding;
- no new asymmetry from damage;
- no cable/harness interference;
- no wheel/deck/guard interference.

Unexpected binding or interference is STOP USE.

### Critical witness marks

Inspect every currently declared critical mark.

A moved critical retention witness mark is not a "tighten it and ride" event.

Open a STOP finding, inspect the mechanism, and document the closure.

### Deck and truck-mount condition

Inspect:

- cracks;
- crushing;
- insert/mount damage;
- abnormal deformation;
- truck/hanger/axle alignment changes.

New structural cracking or permanent deformation is STOP USE.

### Rider-interface retention and step-off

Check:

- hardware retention;
- unexpected migration;
- surface condition;
- emergency step-off path remains unobstructed.

### Guard/skid retention and clearance

Check:

- wear state;
- retention;
- deformation;
- new snag geometry;
- critical clearance;
- no guard contacting moving systems.

### Drainage and contamination paths

Check:

- drains are not blocked;
- mud/grit is not packed against protected zones;
- no retained moisture is visible where it should be dry.

### Harness, hose, and connector condition

Check:

- chafe;
- strain relief;
- full seating;
- latch/retention;
- routing;
- no load-bearing connector;
- no entry into steering/wheel/drive sweep.

## 7. Conditional preflight items

### Remote deadman

Required when a `traction_remote` component is active.

Future powered operation cannot rely on a remote whose deadman behavior is unverified.

### Traction enclosure and service disconnect

Required when a `traction_battery_system` component is active.

This lifecycle check still does not energize or validate the battery.

### Lights / reflective visibility

Required when the event declares that the intended activity needs them.

This does not decide whether the intended public activity itself is allowed.

## 8. Preflight failures must create findings

A failed check cannot remain a red checkbox with no consequence.

Every `FAIL` check needs a linked finding at severity:

- `INSPECT`;
- `SERVICE`;
- or `STOP`.

Example:

```json
{
  "finding_id": "F-0042",
  "component_id": "BRAKE-A",
  "severity": "STOP",
  "trigger": "brake_unavailable_or_materially_degraded",
  "source_check_id": "mechanical_brake_function",
  "description": "Brake cable anchor slipped during lever test.",
  "evidence_ref": "private/photo-or-note-reference"
}
```

The evaluator rejects a failed check with no explicit finding.

## 9. Automatic escalation triggers

The reference snapshot currently defines minimum severity for recurring high-value conditions.

### STOP minimum

- critical witness mark moved;
- wheel retention changed or new axial play appeared;
- new structural crack/permanent deformation;
- independent brake unavailable/materially degraded;
- steering binding or unexpected interference.

### SERVICE minimum

- protected-zone moisture/ingress;
- harness or hose chafe.

### INSPECT minimum

- increased bearing play/noise/roughness;
- unexpected tire-pressure loss;
- significant impact/crash.

A more severe finding is always allowed.

A less severe finding than the declared trigger minimum is rejected.

## 10. Post-activity event

After a meaningful ground test or future ride, create a `POST_ACTIVITY` event.

Record changes rather than repeating every pristine detail.

Useful observations include:

- new tire pressure loss;
- wheel or bearing change;
- brake feel/drag change;
- witness-mark movement;
- guard/skid contact;
- new deck/truck damage;
- contamination;
- moisture;
- harness chafe;
- unexpected steering behavior;
- future thermal/fault events.

Because the latest event is no longer a preflight, the evaluator returns `INSPECTION_REQUIRED` before the next activity.

That is intentional.

The next session starts with a new preflight.

## 11. Impact event

Create an `IMPACT` event after a meaningful strike, crash, drop, curb/root hit, or other event that could plausibly alter retention or alignment.

Do not wait for the next preflight to remember it.

At minimum inspect the affected path:

```text
contact surface
  -> skid / guard / wheel
  -> carrier / truck / mount
  -> deck / enclosure / drivetrain
  -> neighboring brake / harness / steering interfaces
```

A visually minor impact can still shift a witness mark or cable route.

## 12. Contamination event

Use `CONTAMINATION_EXPOSURE` for significant mud, wet, grit, or other exposure beyond the ordinary clean baseline.

Issue #39 controls environmental test qualification.

Issue #41 records what happened to this particular vehicle afterward.

Keep those roles separate.

## 13. Service event

Use `SERVICE` to record a real maintenance action.

A service action identifies:

- component;
- action;
- source/reference;
- whether the action resets an applicable service interval;
- notes/evidence.

Only mark `resets_service_interval=true` when the performed action actually corresponds to the sourced interval.

A wipe-down does not reset a bearing replacement interval.

## 14. Closing findings

Findings can close only in:

- `INSPECTION`;
- `SERVICE`;
- `COMPONENT_REPLACEMENT`;
- `CONFIGURATION_CHANGE`.

A closure must record:

- the finding ID;
- corrective/inspection action;
- verification.

A later `PREFLIGHT` cannot silently close an earlier STOP condition.

After closure, a fresh preflight is still required before READY can return.

## 15. Component replacement and configuration lineage

Do not edit `BRAKE-A` into `BRAKE-B`.

Create a `COMPONENT_REPLACEMENT` or `CONFIGURATION_CHANGE` event.

The event:

1. references the old configuration ID;
2. removes the old component;
3. installs a new unique component ID;
4. declares a new configuration ID.

Example lineage:

```text
CFG-A
  BRAKE-A
     |
     | component replacement
     v
CFG-B
  BRAKE-B
```

All later events reference `CFG-B`.

This preserves the fact that earlier evidence belonged to different hardware.

## 16. Odometer and ride-hour policy

When trustworthy counters exist:

- odometer cannot decrease;
- ride hours cannot decrease.

Before powered telemetry exists, counters may legitimately be null.

But if a selected component has a sourced mileage/hour interval and the corresponding counter is unavailable, the evaluator does not guess.

It returns `INSPECTION_REQUIRED` with the service due state marked unknown.

## 17. Service interval policy

There is no universal X1 schedule such as:

- tighten every 50 miles;
- replace bearings every 100 miles;
- service brakes every 20 hours.

Those numbers would be fiction before final hardware selection.

When real component guidance exists, encode it.

If later X1 evidence establishes a shorter interval because trail duty is harsher, that qualified interval can become the source.

The earliest applicable sourced condition wins.

A condition finding can always require service sooner.

## 18. Evaluate lifecycle health

Example:

```bash
python tools/evaluate_x1_lifecycle_health.py \
  rider/private/health/x1-a/component_registry.json \
  --rolling-chassis-authority \
    rider/private/chassis/donor-a/chassis_authority.json \
  --event rider/private/health/x1-a/events/0001-baseline.json \
  --event rider/private/health/x1-a/events/0002-preflight.json \
  --out rider/private/health/x1-a/health_state.json
```

The report is fingerprinted:

`x1_lifecycle_health_state`

It reports:

- data validity;
- active configuration;
- active component IDs;
- chassis fingerprint;
- latest counters;
- open findings;
- service due;
- unknown service-due states;
- preflight completeness;
- health state;
- ready/not-ready boolean.

It always reports:

```text
powered_operation_authorized = false
public_operation_authorized = false
dog_accompanied_operation_authorized = false
```

## 19. Future telemetry

After powered commissioning eventually exists, the same event system can ingest trustworthy derived counters such as:

- odometer;
- ride hours;
- motor/controller thermal exposure;
- battery temperature events;
- overcurrent/undervoltage/overvoltage faults;
- slip-control interventions;
- deadman/remote faults;
- brake/regen transition anomalies.

Do not make raw telemetry automatically close maintenance findings.

Telemetry can open or support findings.

Inspection/service closes them.

## 20. Rider-facing routine

The intended human interaction should stay compact.

### Before an allowed activity

1. inspect pressures/tires;
2. check wheels/bearings;
3. test mechanical brake;
4. sweep steering;
5. inspect critical marks and structure;
6. inspect rider interface;
7. inspect guards/drains/harness;
8. run conditional remote/battery/light checks;
9. record any finding;
10. evaluate health.

If the result is not `READY_FOR_ALLOWED_ACTIVITY`, address the reason first.

### After an ordinary clean activity

Record a post-activity event when meaningful new observations exist, then inspect again before the next session.

### After impact, mud/wet exposure, fault, or unusual behavior

Create the specific event immediately.

Do not compress it into memory.

## 21. Future powered commissioning rule

The central build-authority graph now exposes the gate `lifecycle_health_ready`.

Every staged commissioning **action** requires that current gate in addition to its stage prerequisites. Future powered, public, and dog-accompanied operation paths also require it.

Issue #45 separately binds each actual commissioning-stage authority to explicit pre/post lifecycle-health evidence, so the generic gate does not replace stage-specific freshness checks.

The logical relationship is:

```text
current lifecycle health == READY_FOR_ALLOWED_ACTIVITY
+ stage-specific commissioning prerequisites
+ any venue/environmental requirements
+ the independent activity authority
```

The health state is necessary but never sufficient.

## Exit condition for this tranche

Issue #41 software architecture is complete when:

1. the workspace is chassis-fingerprint anchored;
2. component registry and event schemas exist;
3. history is append-only;
4. chronology and counters are validated;
5. configuration changes create lineage;
6. serious triggers enforce minimum severity;
7. findings persist until explicit closure;
8. sourced intervals are supported without inventing defaults;
9. missing counters fail closed;
10. a fresh preflight is required after service/change/post-activity events;
11. CI exercises the entire path;
12. every health report preserves all operation-authority blocks.
