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

## 3. Qualify the Issue #61 mass reference

The initializer does not accept free-form mass numbers.

Follow `docs/x1_fit_pilot_mass_reference.md` to create:

```text
pilot_mass_reference.json
pilot_mass_reference_authority.json
```

The authority must contain at least three unique calibration masses and exactly one independent validation mass, all >0 and <=20 kg, with conservative declared uncertainty.

Nominal plate labels alone are not mass authority.

## 4. Create the private session

Replace every `<...>` mass below with the real numeric value in kg:

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

The initializer first verifies both Issue #59 hardware selection and Issue #61 mass-reference authorities, copies all four provenance files into the session, locks the active/spare IDs, and derives the mass sequence from the mass authority. It then sorts the calibration masses, creates the ascending/descending sequence, creates the independent validation filename, and refuses duplicate/nonpositive/>20 kg values.

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

Only a valid fingerprinted `x1_one_zone_pilot` report with `qualified_for_four_zone_duplication=true` **and preserved Issue #59 hardware provenance** may open the four-zone duplication capability. Rider-fit Rev-B, unpowered chassis fabrication, power ordering, and powered operation remain separately gated.
