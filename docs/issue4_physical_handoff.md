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

## 2. Assign physical IDs on receipt

Before wiring or assembly, give the actual pilot parts durable local IDs, for example:

- one load cell: `LC-PILOT-A`
- its HX711: `ADC-PILOT-A`
- printed/machined pod: `POD-PILOT-A`
- zone pad: `PAD-PILOT-A`

Keep the second load cell/HX711 untouched as spares until the first zone qualifies. Record wrong revision, visible damage, or incompatible geometry in the private session notes rather than silently substituting hardware.

## 3. Measure the calibration masses you will actually use

The initializer no longer invents 2/5/10/7.5 kg values. Supply the **actual measured values** for at least three unique ascending calibration masses and one independent validation mass. Each must be >0 and <=20 kg.

Do not type nominal plate labels unless those are the values you have chosen to treat as the known-mass authority. Better mass reference uncertainty produces better calibration evidence.

## 4. Create the private session

Replace every `<...>` mass below with the real numeric value in kg:

```bash
PYTHONPATH=. python tools/init_one_zone_pilot_session.py \
  rider/private/fit_rig/issue4-pilot \
  --load-cell-id LC-PILOT-A \
  --hx711-id ADC-PILOT-A \
  --pod-id POD-PILOT-A \
  --zone-pad-id PAD-PILOT-A \
  --channel left_heel \
  --sps 10 \
  --calibration-mass-kg <measured-low-kg> \
  --calibration-mass-kg <measured-mid-kg> \
  --calibration-mass-kg <measured-high-kg> \
  --validation-mass-kg <measured-independent-kg>
```

The initializer sorts the calibration masses, creates an ascending sequence, creates paired descending plateaus below the maximum, creates the independent validation filename, and refuses duplicate/nonpositive/>20 kg values.

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

Only a valid fingerprinted report with `qualified_for_four_zone_duplication=true` may open the four-zone duplication capability. Rider-fit Rev-B, unpowered chassis fabrication, power ordering, and powered operation remain separately gated.
