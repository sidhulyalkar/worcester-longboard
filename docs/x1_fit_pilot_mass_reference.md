# Worcester X1 Issue #61 calibration-mass reference

**Purpose:** make every Issue #4 calibration/validation mass a fingerprinted measurement with an explicit uncertainty budget.

**Authority emitted:** `x1_fit_pilot_mass_reference`

**NIST traceability claim:** no.

**Commercial/legal metrology claim:** no.

**Sensor qualification:** no.

Issue #59 answers **which physical sensor stack is being calibrated**.

Issue #61 answers **what physical loads are being treated as known during that calibration**.

Both must be fixed before the Issue #4 session is created.

## Why this matters

A load-cell regression can produce nearly perfect R² even when every reference mass is biased.

Therefore:

- a nominal gym-plate label is not automatically mass authority;
- a kitchen/bench scale resolution is not the same thing as accuracy;
- repeated measurements establish repeatability, not absolute accuracy;
- the reference uncertainty must be carried into the final sensor error budget.

The project deliberately avoids pretending a home setup is NIST-traceable. NIST defines metrological traceability through a documented unbroken calibration chain with each calibration contributing uncertainty. X1 only claims the evidence actually recorded.

## X1 screening uncertainty rule

Issue #4's independent validation gate is currently 2%.

Issue #61 limits the declared expanded uncertainty of each positive reference mass to:

```text
<= 0.5% of that mass
```

This is an X1 engineering screening rule, chosen so reference-mass uncertainty consumes no more than one quarter of the 2% validation-error budget.

It is not a general metrology standard.

The one-zone qualifier evaluates conservatively:

```text
combined calibration residual
  = observed residual + calibration-reference uncertainty contribution

combined validation error
  = observed validation error + validation-reference relative uncertainty
```

The combined values must satisfy the existing Issue #4 gates.

## Allowed method A: independent scale with manufacturer accuracy

Use:

`INDEPENDENT_SCALE_MANUFACTURER_SPEC`

The scale/reference system must have recorded:

- manufacturer;
- model;
- capacity;
- display resolution;
- manufacturer's stated absolute accuracy;
- source for that accuracy specification;
- at least three zero checks.

For each mass:

- identify the physical object;
- record at least five repeated measurements;
- record the accepted mass;
- declare a conservative expanded uncertainty;
- preserve the source/session reference.

The declared uncertainty may not be smaller than the largest of:

- stated absolute scale accuracy;
- half one scale division;
- half the repeated-measurement span;
- half the zero-check span.

It must also satisfy the X1 0.5% relative limit.

### Practical implication

A scale that reads to 1 g but is only accurate to +/-20 g does **not** justify a 1 g uncertainty claim.

Use the accuracy specification, not the prettiest number on the display.

## Allowed method B: calibrated reference masses

Use:

`CALIBRATED_REFERENCE_MASSES`

Record:

- reference-set manufacturer/model;
- certificate/reference identifier;
- certificate expanded uncertainty;
- nominal/accepted values;
- the declared uncertainty used by X1.

X1 does not infer NIST traceability merely because a seller uses words such as "calibration weight."

Traceability should be claimed only when the actual documentation supports the relevant chain.

## Required mass set

Issue #4 needs:

- at least three unique positive `CALIBRATION` masses;
- exactly one positive `VALIDATION` mass;
- validation mass different from every calibration mass;
- every applied mass <=20 kg.

The validation object should be independently identified from the calibration values even if all are measured with the same reference system.

## Create the private record

Start from:

`hardware/x1_fit_pilot_mass_reference_template.json`

Copy it under `rider/private/`, for example:

```text
rider/private/physical_kickoff/pilot_mass_reference.json
```

Fill the real values and evidence.

Do not commit private scale serials, receipts, certificates, or photos unless intentionally sanitized.

## Validate

```bash
python tools/validate_x1_fit_pilot_mass_reference.py \
  rider/private/physical_kickoff/pilot_mass_reference.json \
  --out rider/private/physical_kickoff/pilot_mass_reference_authority.json
```

A passing report must include:

```text
authority = x1_fit_pilot_mass_reference
scope = issue4_mass_reference_only
valid = true
nist_traceability_claimed = false
commercial_legal_metrology_claimed = false
physical_sensor_qualification_authority = false
four_zone_duplication_authorized = false
powered_operation_authorized = false
```

It also records:

- calibration masses;
- validation mass;
- declared uncertainty for every reference;
- conservative uncertainty floor;
- maximum relative uncertainty;
- record fingerprint;
- authority fingerprint.

## Initialize Issue #4

After Issue #59 hardware selection **and** Issue #61 mass reference both validate:

```bash
python tools/init_one_zone_pilot_session.py \
  rider/private/fit_rig/issue4-pilot \
  --hardware-selection rider/private/physical_kickoff/pilot_hardware_selection.json \
  --hardware-selection-authority rider/private/physical_kickoff/pilot_hardware_selection_authority.json \
  --mass-reference rider/private/physical_kickoff/pilot_mass_reference.json \
  --mass-reference-authority rider/private/physical_kickoff/pilot_mass_reference_authority.json \
  --pod-id POD-PILOT-A \
  --zone-pad-id PAD-PILOT-A \
  --channel left_heel \
  --sps 10
```

The initializer derives the load sequence directly from the mass authority.

There are no free-form `--calibration-mass-kg` or `--validation-mass-kg` arguments.

The session copies:

```text
provenance/hardware_selection.json
provenance/hardware_selection_authority.json
provenance/mass_reference.json
provenance/mass_reference_authority.json
```

## Qualification

The Issue #4 qualifier re-verifies both provenance chains before sensor-performance metrics can pass.

It rejects:

- altered mass values;
- altered uncertainty;
- tampered mass-reference record;
- mismatched authority fingerprint;
- missing reference IDs;
- changed active hardware;
- changed spare lineage.

The result reports both raw and conservative uncertainty-inclusive metrics.

A clean sensor with inadequate mass evidence remains unqualified.

## Changing the mass set

Do not edit an existing Issue #4 manifest to "correct" a mass after capture.

If a reference value or source changes materially:

1. preserve the old private evidence;
2. create a new Issue #61 reference record/authority;
3. create a new Issue #4 session;
4. repeat the affected physical captures.

This preserves the calibration experiment as an auditable unit.

## What this does not require

Issue #61 does not require expensive laboratory weights merely for the first X1 screen.

A sufficiently accurate independent scale can be usable when:

- its accuracy is actually documented;
- its resolution is adequate;
- repeated measurements are stable;
- the conservative uncertainty passes the X1 0.5% rule.

If the available scale cannot meet that rule, use smaller/better-suited loads, borrow better equipment, or use documented reference masses rather than inventing precision.

## Exit condition

Issue #61 is complete for one Issue #4 session when:

1. the reference method is declared;
2. the measurement system/reference documentation is recorded;
3. zero checks pass;
4. at least three calibration masses validate;
5. one distinct validation mass validates;
6. every declared uncertainty exceeds its conservative floor;
7. every relative uncertainty is <=0.5%;
8. `x1_fit_pilot_mass_reference` validates;
9. the Issue #4 session is initialized from that exact authority.

Only then should sensor capture begin.
