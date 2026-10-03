# Worcester X1 Issue #61 fit-pilot mass-reference evidence

**Purpose:** establish the actual calibration and independent-validation masses used by Issue #4, with explicit evidence quality and conservative uncertainty.

**Authority emitted:** `x1_fit_pilot_mass_reference`

**NIST traceability claim:** no.

**Legal/commercial metrology authority:** no.

**Load-cell performance authority:** no.

**Four-zone duplication authority:** no.

Issue #59 answers **which sensor hardware is being calibrated**.

Issue #61 answers **what physical masses are being treated as the reference input**.

Both must exist before an Issue #4 session is initialized.

## Why this gate exists

A load-cell calibration can have excellent R² against bad reference values.

Examples that are no longer acceptable:

- typing `2`, `5`, and `10` kg because those numbers are printed on plates;
- weighing an object once and copying every displayed decimal digit as exact truth;
- using a scale without recording its resolution or stated accuracy;
- changing a calibration object's assumed mass after capture;
- using one set of mass values in the session manifest and another in a notebook.

Issue #61 makes the input side of the experiment auditable.

## Screening policy

Current X1 screening rules are:

- at least **3** unique positive calibration masses;
- exactly **1** independent validation mass;
- validation mass must not equal a calibration mass;
- every mass must be `<=20 kg`;
- every nonzero mass needs an explicit positive uncertainty;
- relative reference uncertainty must be `<=0.5%` of the declared mass.

The 0.5% reference-uncertainty ceiling is an X1 engineering screening rule. It is one quarter of the canonical Issue #4 2% independent-validation-error limit, so the reference uncertainty cannot dominate that sensor gate.

This is not a legal-metrology tolerance.

## Allowed path A: documented reference mass

Use this when the physical mass has documentation that states both mass and uncertainty/tolerance appropriate for the intended reference role.

For each object record:

- stable `mass_id`;
- role: `CALIBRATION` or `VALIDATION`;
- `evidence_type = REFERENCE_MASS`;
- documented source reference;
- documented mass;
- documented uncertainty;
- declared mass;
- declared conservative uncertainty.

The declared uncertainty may be larger than the documented uncertainty. It may not be smaller.

A nominal product label without uncertainty/tolerance evidence is not this path.

## Allowed path B: independent scale

This is the practical low-cost path when you do not own documented reference masses.

For each object:

1. choose an independent scale whose capacity covers the object;
2. record scale manufacturer/model;
3. record display resolution;
4. record the manufacturer/source accuracy statement;
5. convert that statement conservatively into an absolute `conservative_accuracy_limit_kg` for the relevant reading;
6. verify zero before measurement;
7. take at least three repeated readings without cherry-picking;
8. verify zero again;
9. record all readings.

The validator computes:

```text
uncertainty floor
  = conservative accuracy limit
  + half one display increment
  + repeatability half-range
```

where:

```text
repeatability half-range = (max repeated reading - min repeated reading) / 2
```

The declared uncertainty must be at least that large.

This deliberately **adds** the uncertainty components rather than using a smaller root-sum-square estimate. For the inexpensive Issue #4 screen, conservative and understandable is preferable to false sophistication.

The declared mass must agree with the arithmetic mean of the repeated readings within half one display increment.

## Initialize the private record

Create an empty record:

```bash
PYTHONPATH=. python tools/init_x1_fit_pilot_mass_reference.py \
  rider/private/physical_kickoff/pilot_mass_reference.json \
  --reference-set-id MASS-REF-001 \
  --measured-at-utc <ACTUAL_TIME_WITH_TIMEZONE>
```

Then populate `masses[]` using one of the two evidence paths above.

The public template is:

`hardware/x1_fit_pilot_mass_reference_template.json`

Keep photos, scale serials, certificates, receipts, and other private details under `rider/private/`.

## Validate the reference set

Run:

```bash
PYTHONPATH=. python tools/validate_x1_fit_pilot_mass_reference.py \
  rider/private/physical_kickoff/pilot_mass_reference.json \
  --out rider/private/physical_kickoff/pilot_mass_reference_authority.json
```

A passing report must contain:

```text
authority = x1_fit_pilot_mass_reference
valid = true
nist_traceable = false
legal_metrology = false
load_cell_performance_authority = false
four_zone_duplication_authorized = false
powered_operation_authorized = false
```

The report contains:

- normalized calibration masses;
- the one validation mass;
- declared uncertainty for each;
- relative uncertainty;
- evidence summary;
- source-record SHA-256;
- authority fingerprint.

## Create Issue #4 only after Issue #59 and Issue #61 pass

```bash
PYTHONPATH=. python tools/init_one_zone_pilot_session.py \
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

There are no free-form `--calibration-mass-kg` or `--validation-mass-kg` arguments anymore.

The initializer:

- revalidates Issue #59 hardware provenance;
- revalidates Issue #61 mass provenance;
- recomputes the canonical Issue #61 authority from the source record;
- copies both records and both authorities into the private session;
- derives the ascending/descending calibration sequence from the authority;
- derives the independent validation mass from the authority;
- copies each mass ID and uncertainty into the manifest.

Changing any mass value, uncertainty, evidence source, active load cell, or active HX711 requires a new session.

## How Issue #4 uses uncertainty

`fit/pilot_qualification.py` revalidates the copied Issue #61 source record and authority.

It reports both nominal and conservative metrics.

### Calibration residual

The nominal residual is retained for diagnosis.

The qualification residual adds the declared calibration-mass uncertainty and uses a conservatively reduced full-scale reference.

### Independent validation

The report includes:

- `validation_error_nominal`: sensor error against the declared central mass value;
- `validation_reference_uncertainty_relative`;
- `validation_error`: conservative bound including the validation-reference uncertainty.

The canonical 2% validation gate applies to the conservative `validation_error`, not the nominal-only number.

This means a reference uncertainty can make an otherwise excellent sensor fail the screening gate. That is intentional. Better mass evidence should be collected instead of editing around the failure.

## Downstream authority

The project-wide `fit_pilot_qualified` gate now requires:

- fingerprinted Issue #59 hardware provenance;
- fingerprinted Issue #61 mass provenance;
- successful one-zone sensor/mechanical metrics;
- valid one-zone authority fingerprint.

A legacy Issue #4 report without Issue #61 provenance cannot release four-zone duplication or the Rev-C chassis purchase gate.
