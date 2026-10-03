# X1 Ride Signature: bench now, trail later

Status: descriptive analysis architecture only. No fabrication, ride, or powered-operation authority.

## Why two tiers

X1 already has two different evidence domains and they should stay separate:

1. **SnowDeck Bench Signature**: unpowered Fit Rig force evidence used to compare reversible rider-interface conditions.
2. **Trail Ride Signature**: future vehicle telemetry derived from the canonical X1 flight recorder after the relevant physical and powered gates exist.

The two tiers may eventually share names such as CONTROL or FLOAT, but they must never silently mix evidence.

## SnowDeck Bench Signature

The bench signature intentionally does not create a single score.

A condition is represented by a response vector:

- neutral left/right load distribution;
- neutral left/right forefoot fractions;
- remount-to-remount standard deviation;
- heel-biased to toe-biased forefoot transfer for each foot;
- deep-knee shift relative to neutral;
- total-load repeatability;
- explicit safety/rejection observations from the SnowDeck bench session.

Stable left/right asymmetry is not penalized merely for being asymmetric.

### Canonical force-log format

Private force logs used by the summarizer are CSV with:

```text
trial_id,pose,left_heel,left_forefoot,right_heel,right_forefoot
trial-01,NEUTRAL,...
trial-01,DEEP_KNEE,...
trial-01,HEEL_BIASED,...
trial-01,TOE_BIASED,...
...
```

Each row is one settled sample. A trial/pose pair may contain many rows.

Required poses are:

- `NEUTRAL`
- `DEEP_KNEE`
- `HEEL_BIASED`
- `TOE_BIASED`

The analysis requires at least three independent trials.

The input values must already be calibrated force values in consistent units. This tool does not establish load-cell calibration authority.

## Immediate-reject separation

The force response vector and mechanical rejection state are separate outputs.

A condition is blocked from progression if the linked bench session reports any of:

- unexpected rocking;
- insert or fastener migration;
- fixture interference;
- persistent deformation;
- overload-stop contact;
- failed emergency step-off;
- post-trial fastener migration;
- insert shift;
- fixture damage;
- residual deformation.

A mechanically rejected condition may still have an analyzable force vector. The analysis must not turn that vector into permission to continue the configuration.

## Pairwise comparison

`tools/compare_snowdeck_signatures.py` compares one variant against one declared baseline, usually S0.

It reports signed deltas only.

It does not:

- rank all configurations;
- claim larger heel/toe transfer is always better;
- reward symmetry;
- combine comfort and sensor evidence;
- convert a bench result into ride geometry;
- authorize fabrication.

This preserves the real engineering question: which mechanical change caused which measurable response, and what tradeoff came with it?

## Future Trail Ride Signature

After the existing rolling-chassis, topology, power, commissioning, and telemetry gates exist, the canonical flight recorder can support a trail signature with separate domains:

### CONTROL
- roll/yaw response;
- steering-return behavior;
- slip/control-intervention events;
- commanded versus observed stopping response.

### FLOAT
- vertical acceleration RMS by frequency band;
- impact peaks;
- jerk;
- vibration transmissibility when a rider/board comparison sensor exists.

### TRAIL
- wheel-speed disagreement / slip proxies;
- impact and anomaly counts;
- thermal exposure;
- terrain-labelled response.

### EFFICIENCY
- Wh/km or Wh/mi;
- speed distribution;
- current/power distribution;
- repeated route/configuration comparisons.

Those quantities remain configuration-specific telemetry products. A future analyzer should consume fingerprint-valid telemetry sessions rather than creating a second recorder format.

## Synthetic visualization fixture

Before physical sensing exists, the committed showcase examples may exercise the exact viewer path.

Synthetic outputs must declare:

- `synthetic_fixture=true`;
- `physical_evidence_eligible=false`;
- all authority flags false.

A comparison containing either synthetic input remains synthetic.

The one-command preview is:

```bash
python tools/prepare_x1_showcase.py --synthetic-snowdeck-demo
```

Synthetic data must never be copied into a physical qualification report.

## Viewer integration

The digital twin may load a local SnowDeck Bench Signature for visualization, but real rider force data stays private.

A viewer presentation should show:

- response-vector values;
- baseline deltas;
- mechanical reject state;
- provenance hash;

without exporting private raw traces into the public repository.

## Authority boundary

SnowDeck Bench Signature output always keeps:

- `physical_authority=false`
- `fabrication_authority=false`
- `ride_authority=false`
- `powered_operation_authorized=false`

The Trail Ride Signature likewise remains analysis unless a separate project gate explicitly consumes it.
