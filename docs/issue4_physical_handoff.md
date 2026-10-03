# Issue #4 physical handoff: checkout -> capture -> authority

This is the shortest current path from repository software to real Worcester X1 evidence. It qualifies **one unpowered fit-rig force zone only**. It does not qualify a rideable deck, chassis, brake, drivetrain, battery, or powered operation.

## 1. Generate the live checkout packet

```bash
PYTHONPATH=. python tools/render_procurement_packet.py \
  --out rider/private/issue4_procurement_packet.md
```

The generated packet has three deliberately different sections:

- **Issue #4 bench checkout**: inexpensive `BUY_NOW` items; the complete no-tools-owned ceiling must stay at or below $125.
- **Eligible measurement-stage sourcing**: currently the preferred Comp 95 donor and V5 brake; these are not part of the pilot checkout.
- **Blocked candidates**: fallback truck/hub while donor-first is active, unqualified 9-inch options, deferred axle study, and all traction-power hardware.

Do not turn a blocked row into a purchase by copying it into a separate shopping list. Change and review the repository authority instead.

## 2. Create the Issue #59 hardware selection

Issue #56 receiving or exact-unused owned-stock evidence must exist before the calibration session.

Follow `docs/x1_fit_pilot_hardware_provenance.md` to create and validate:

```text
pilot_hardware_selection.json
pilot_hardware_selection_authority.json
```

The selection authority locks:

- the exact active load-cell hardware ID;
- the exact untouched load-cell spare ID;
- the exact active HX711 hardware ID;
- the exact untouched HX711 spare ID;
- optional MCU provenance.

The pod and zone pad still receive durable local IDs such as `POD-PILOT-A` and `PAD-PILOT-A`.

Do not silently substitute or swap a spare into the same calibration session. A changed active sensor path requires a new Issue #59 selection authority and a new Issue #4 session.

## 3. Create the Issue #61 mass-reference authority

Issue #4 no longer accepts free-form "known mass" numbers.

Follow `docs/x1_fit_pilot_mass_reference.md`.

Create the private record:

```bash
PYTHONPATH=. python tools/init_x1_fit_pilot_mass_reference.py \
  rider/private/physical_kickoff/pilot_mass_reference.json \
  --reference-set-id MASS-REF-001 \
  --measured-at-utc <ACTUAL_TIME_WITH_TIMEZONE>
```

Populate at least three unique positive calibration masses plus one independent validation mass. Every mass must be `<=20 kg` and carry explicit uncertainty evidence.

Allowed evidence paths are:

- documented reference mass with stated uncertainty;
- repeated measurement on an independent scale with recorded manufacturer/model, resolution, accuracy source, zero checks and readings.

A nominal plate/object label by itself is not authority.

Validate:

```bash
PYTHONPATH=. python tools/validate_x1_fit_pilot_mass_reference.py \
  rider/private/physical_kickoff/pilot_mass_reference.json \
  --out rider/private/physical_kickoff/pilot_mass_reference_authority.json
```

The authority must report `valid=true` and still keep NIST traceability, legal metrology, load-cell performance, four-zone duplication, fabrication and operation authority false.

## 4. Create the private Issue #4 session

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

The initializer revalidates both authorities, copies both records and both authorities into the session `provenance/` directory, derives the load sequence from Issue #61, and writes each mass ID plus uncertainty into the manifest.

There are no free-form calibration/validation mass arguments. Changing a mass value, uncertainty, evidence source, active load cell, or active HX711 requires a new authority/session.

## 5. Assemble and capture exactly one zone

Follow `hardware/one_zone_pilot_assembly.md` and `docs/one_zone_pilot.md` for the mechanical checks, HX711 rate verification, settled plateau capture, stop-gap measurements, and logger format.

The generated private `NOTES.md` contains the exact mass sequence. Keep transient loading/unloading out of plateau CSVs. Do not manufacture or duplicate the other three sensor pods merely because the CAD exists.

## 6. Qualify the real session

After replacing the manifest's mechanical `false`/`null` fields with the measurements and checks from the real hardware:

```bash
PYTHONPATH=. python tools/qualify_one_zone_pilot.py \
  rider/private/fit_rig/issue4-pilot/pilot_manifest.json \
  --out rider/private/fit_rig/issue4-pilot/pilot_authority.json
```

A failed report is evidence, not something to edit around. Repair the physical/setup cause and capture a new session where required.

## 7. Ask the project-wide authority what changed

```bash
PYTHONPATH=. python tools/evaluate_build_authority.py \
  hardware/build_authority.json \
  hardware/procurement_manifest.json \
  --evidence rider/private/fit_rig/issue4-pilot/pilot_authority.json \
  --out rider/private/fit_rig/issue4-pilot/build_authority.json
```

Only a valid fingerprinted `x1_one_zone_pilot` report with `qualified_for_four_zone_duplication=true`, preserved Issue #59 hardware provenance, **and preserved Issue #61 mass-reference provenance** may open the four-zone duplication capability. Rider-fit Rev-B, unpowered chassis fabrication, power ordering, and powered operation remain separately gated.
