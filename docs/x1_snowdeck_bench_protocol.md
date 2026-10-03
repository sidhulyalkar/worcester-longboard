# X1 SnowDeck v0.1 bench protocol

Status: **unpowered, non-riding, reversible rider-interface experiment only**.

This protocol turns the SnowDeck idea into measurements without granting fabrication or ride authority.

## Objective

Determine whether changes to rider-interface geometry or a thin compliant layer produce a repeatable, useful change in static control proxies without introducing rocking, slow return, interference, or retention problems.

The experiment deliberately separates:

1. geometry;
2. compliance;
3. rider-force behavior.

Do not change all three at once.

## Prerequisites

Before any rider-force comparison:

- Issue #4 one-zone pilot must pass;
- Issue #63 platform repeatability must pass;
- the four-zone Fit Rig must be duplicated only under its existing authority;
- no SnowDeck study part is attached permanently to a ride chassis.

Pure geometry mockups may be inspected earlier with no load-cell claims.

## Conditions

### S0: rigid control

- zero cant;
- no compliant insert;
- neutral ramp geometry;
- independently adjustable front/rear yaw and position.

This is the reference condition.

### S1: cant-only study

Use one reversible cant geometry while keeping the interface rigid.

Suggested CAD study pieces are 2 and 4 degrees because they sit inside the current 0-5 degree visualization range. They are **study points, not safe or recommended ride angles**.

### S2: heel/toe leverage geometry

Change only the rigid underfoot leverage geometry. Record the exact reversible spacer/ramp geometry privately.

Do not add compliance in the same first comparison.

### C1/C2: compliance study

Only after rigid geometry is understood, add one compliant insert at a time.

Record:

- material;
- nominal thickness;
- supported footprint;
- preload/compression method;
- whether the insert creeps, rocks, takes a permanent set, or shifts.

No material is approved merely because it feels comfortable.

## Static sequence

For each condition:

1. inspect all fasteners and contact surfaces;
2. mount the fixture on a rigid bench/floor;
3. zero only according to the qualified Fit Rig procedure;
4. perform at least three independent natural remounts;
5. hold neutral stance;
6. hold a controlled deep-knee stance;
7. hold controlled heel-biased and toe-biased static carve poses;
8. step completely off between trials;
9. perform a deliberate bilateral emergency step-off check;
10. inspect for movement, rocking, insert migration, fastener migration, or fixture damage.

Do not turn these poses into dynamic balance or ride simulation.

## Measurements

When four-zone evidence is available, capture for each settled pose:

- front-foot total load;
- rear-foot total load;
- each foot's heel/forefoot split;
- left/right total load if the fixture coordinate system supports it;
- center-of-pressure proxy derived only from qualified zone geometry;
- remount-to-remount spread;
- zero return after unloading.

Also record qualitative observations separately:

- support feels stable;
- heel/toe leverage feels adequate;
- deep-knee stance remains comfortable;
- emergency step-off remains unobstructed;
- rocking observed;
- delayed return observed;
- audible or visible insert movement;
- fastener migration;
- fixture interference.

Do not collapse subjective comfort and sensor measurements into one score.

## Compliance characterization

For a candidate insert, use controlled known loads rather than bodyweight alone.

Measure:

- loaded thickness or displacement;
- unload return;
- repeated-cycle set;
- left/right or heel/toe asymmetry;
- settling time after load application;
- whether load-cell readings change materially with contact position.

A compliant layer that corrupts the force measurement is not a valid personalization signal until that error is understood.

## Compliance-cartridge characterization

For C1/C2-style insert studies, keep underfoot force-transfer comparisons separate from the material/cartridge mechanics.

Start from:

`hardware/snowdeck_compliance_trial_template.json`

Record repeated controlled normal load-displacement and torsional moment-angle cycles, plus zero return and settling time. The public summarizer is:

```bash
python tools/summarize_snowdeck_compliance_trial.py \
  rider/private/snowdeck/C1/compliance_trial.json \
  --out rider/private/snowdeck/C1/compliance_signature.json
```

The output reports repeated-cycle descriptors only:

- loading/unloading normal stiffness in N/mm;
- normal hysteresis-loop work proxy in mJ;
- vertical zero return and settling time;
- loading/unloading torsional stiffness in N·m/rad;
- torsional hysteresis-loop work in J;
- angular zero return and settling time;
- separate rocking/migration/damage reject observations.

No generic stiffness target, damping target, wear limit, material family, or "snowboard feel" optimum is encoded. Those values become useful only by comparing controlled candidates against the rigid S0/S1 response map and by preserving emergency step-off and measurement integrity.

A cartridge with interesting stiffness data but rocking, migration, fastener movement, damage, or persistent deformation remains blocked from further bench progression.

## Immediate reject observations

A study configuration is rejected from further progression if any of these occur:

- unexpected rocking;
- loss of positive support;
- fastener or insert migration;
- interference with the fixture or intended step-off path;
- persistent deformation after unloading;
- obvious cross-axis instability;
- overload-stop contact or other invalidation of the qualified Fit Rig measurement path.

Rejection here means only "do not progress this bench configuration." Passing does not authorize riding.

## Force-response summarization

After the private force log is complete, summarize the four-zone data without creating a ranking:

```bash
python tools/summarize_snowdeck_force_log.py \
  rider/private/snowdeck/S1/force.csv \
  --session rider/private/snowdeck/S1/session.json \
  --out rider/private/snowdeck/S1/signature.json
```

The CSV uses calibrated, settled samples with columns:

`trial_id,pose,left_heel,left_forefoot,right_heel,right_forefoot`

and requires NEUTRAL, DEEP_KNEE, HEEL_BIASED and TOE_BIASED groups for at least three independent trials.

The signature keeps force response and mechanical rejection separate. A condition with useful force transfer but observed rocking or migration remains blocked from further progression.

## Comparison rule

Compare one change against S0 at a time.

```bash
python tools/compare_snowdeck_signatures.py \
  rider/private/snowdeck/S0/signature.json \
  rider/private/snowdeck/S1/signature.json \
  --out rider/private/snowdeck/S1/vs_s0.json
```

The comparison reports signed variant-minus-baseline deltas and explicitly sets `winner_selected=false`.

The most useful outcome is not a single "best" setup. It is a response map:

- geometry that increases heel/toe authority;
- geometry that reduces remount repeatability;
- compliance that attenuates high-frequency input later;
- compliance that makes static force transfer ambiguous;
- adjustments that preserve emergency step-off.

That map will later inform Rev-B rider-interface geometry.

## Public/private boundary

Public repository artifacts may contain:

- generic geometry;
- condition IDs;
- non-personal protocol fields;
- sanitized aggregate conclusions.

Keep private:

- actual foot/body measurements;
- exact rider-specific stance;
- raw force traces;
- comfort notes tied to personal anatomy;
- any personally identifying video.

## Authority boundary

This protocol never emits:

- chassis fabrication authority;
- permanent drilling authority;
- retention-system authority;
- ride authority;
- powered-operation authority.

Its output is experimental evidence for later rider-interface decisions only.
