# Worcester X1 Issue #59 fit-pilot hardware provenance

**Purpose:** bind the exact Issue #4 active load cell and HX711 to fingerprinted Cart A evidence before calibration begins.

**Authority emitted:** `x1_fit_pilot_hardware_selection`

**Physical sensor qualification:** no.

**Four-zone duplication:** no.

**Powered/public/dog operation:** no.

Issue #56 proves what was already owned, ordered, and received.

Issue #59 answers the next question:

> Which exact physical load cell and HX711 are the active Issue #4 evidence path, and which exact units remain untouched spares?

That choice must be explicit before the one-zone calibration session exists.

## Why this gate exists

The Issue #4 calibration can produce excellent linearity, hysteresis, noise, and validation metrics while still being scientifically useless if the hardware identity is wrong.

Examples:

- calibrating the untouched spare instead of the unit identified as active;
- replacing an HX711 after a wiring problem while keeping the old calibration session;
- using a similar load cell that was never accepted as exact evidence hardware;
- copying stable IDs by hand from a different receiving record;
- qualifying one physical stack and later treating another stack as equivalent.

Issue #59 closes those paths.

## Canonical flow

```text
Day-0 owned inventory
        |
        v
Issue #56 checkout evidence
        |
        +-----------------------------+
        |                             |
        v                             v
ORDER                         USE_OWNED_EXACT
        |                             |
        v                             |
Issue #56 receiving                   |
stable received IDs                   |
        +-------------+---------------+
                      |
                      v
Issue #59 hardware selection
  active load cell + untouched spare
  active HX711     + untouched spare
  optional MCU provenance
                      |
                      v
x1_fit_pilot_hardware_selection
                      |
                      v
Issue #4 one-zone session
                      |
                      v
x1_one_zone_pilot
```

## Path A: ordered and received hardware

After Issue #56 receiving is complete, the receiving record must contain, for both `LC-3135` and `ADC-HX711`:

- exactly one `PILOT_ACTIVE_CANDIDATE`;
- exactly one `SPARE_UNTOUCHED`;
- stable unique hardware IDs;
- exact-part confirmation;
- packaging/markings evidence;
- no unresolved visible damage.

Initialize the selection:

```bash
python tools/init_x1_fit_pilot_hardware_selection.py \
  rider/private/physical_kickoff/pilot_hardware_selection.json \
  --inventory rider/private/physical_kickoff/owned_inventory.json \
  --checkout rider/private/physical_kickoff/cart_a_checkout.json \
  --checkout-authority rider/private/physical_kickoff/cart_a_checkout_authority.json \
  --receiving rider/private/physical_kickoff/cart_a_receiving.json \
  --receiving-authority rider/private/physical_kickoff/cart_a_receiving_authority.json \
  --selection-id PILOT-HW-001 \
  --selected-at-utc <ACTUAL_TIME>
```

If the ESP32-S3 is being used and its received hardware ID is known, also pass:

```text
--mcu-id <ACTUAL_MCU_HARDWARE_ID>
```

The initializer selects the hardware units from the roles recorded in receiving. Do not type a different load-cell or HX711 ID into Issue #4 later.

Validate:

```bash
python tools/validate_x1_fit_pilot_hardware_selection.py \
  rider/private/physical_kickoff/pilot_hardware_selection.json \
  --inventory rider/private/physical_kickoff/owned_inventory.json \
  --checkout rider/private/physical_kickoff/cart_a_checkout.json \
  --checkout-authority rider/private/physical_kickoff/cart_a_checkout_authority.json \
  --receiving rider/private/physical_kickoff/cart_a_receiving.json \
  --receiving-authority rider/private/physical_kickoff/cart_a_receiving_authority.json \
  --out rider/private/physical_kickoff/pilot_hardware_selection_authority.json
```

A passing report must say:

```text
authority = x1_fit_pilot_hardware_selection
valid = true
exact_evidence_hardware_verified = true
untouched_spares_preserved = true
physical_qualification_authority = false
four_zone_duplication_authorized = false
powered_operation_authorized = false
```

## Path B: exact unused owned stock

A Cart A purchase is not required if the Day-0 inventory already proves enough exact evidence hardware.

For each required sensor item:

- inventory status must be `OWNED_EXACT_UNUSED`;
- `exact_part_match=true`;
- `unused_or_known_history=true`;
- at least two physically verified units must exist.

The Issue #56 checkout must resolve the item as `USE_OWNED_EXACT`.

Assign private stable hardware IDs to the four physical units before creating the selection.

Example:

```bash
python tools/init_x1_fit_pilot_hardware_selection.py \
  rider/private/physical_kickoff/pilot_hardware_selection.json \
  --inventory rider/private/physical_kickoff/owned_inventory.json \
  --checkout rider/private/physical_kickoff/cart_a_checkout.json \
  --checkout-authority rider/private/physical_kickoff/cart_a_checkout_authority.json \
  --selection-id PILOT-HW-OWNED-001 \
  --selected-at-utc <ACTUAL_TIME> \
  --owned-load-cell-active-id <LC_ACTIVE_ID> \
  --owned-load-cell-spare-id <LC_SPARE_ID> \
  --owned-hx711-active-id <ADC_ACTIVE_ID> \
  --owned-hx711-spare-id <ADC_SPARE_ID>
```

Receiving evidence is omitted for an owned-only path.

The validator still requires:

- active/spare separation;
- unique IDs;
- exact quantity;
- exact-part status;
- known/unused history;
- matching checkout/inventory fingerprints.

## Mixed-source path

A mixed path is allowed.

Examples:

- ordered/received load cells + exact-unused owned HX711 boards;
- exact-unused owned load cells + ordered/received HX711 boards.

Supply receiving evidence if **any** required sensor uses `RECEIVED_ORDER`.

Each hardware class is validated against its own checkout resolution.

## The untouched spare is not a hot replacement

`SPARE_UNTOUCHED` means evidence reserve.

Do not wire it, solder it, mechanically install it, or swap it into the current Issue #4 session.

If the active load cell or HX711 becomes suspect:

1. stop the current Issue #4 session;
2. document the reason privately;
3. decide whether the spare should become a new active candidate;
4. create a new Issue #59 hardware selection with new roles/evidence as appropriate;
5. create a new Issue #4 session;
6. calibrate the new physical path from zero.

Do not inherit calibration from the previous hardware.

## Add Issue #61 mass-reference evidence before Issue #4

A valid Issue #59 hardware selection is necessary but no longer sufficient to initialize calibration.

Follow:

`docs/x1_fit_pilot_mass_reference.md`

Create and validate:

```text
pilot_mass_reference.json
pilot_mass_reference_authority.json
```

The mass authority locks:

- at least three calibration mass IDs/values;
- exactly one independent validation mass;
- uncertainty for every mass;
- the source/evidence path used to establish each value.

Then initialize Issue #4 from **both** authorities:

```bash
PYTHONPATH=. python tools/init_one_zone_pilot_session.py \
  rider/private/fit_rig/issue4-pilot \
  --hardware-selection rider/private/physical_kickoff/pilot_hardware_selection.json \
  --hardware-selection-authority rider/private/physical_kickoff/pilot_hardware_selection_authority.json \
  --mass-reference rider/private/physical_kickoff/pilot_mass_reference.json \
  --mass-reference-authority rider/private/physical_kickoff/pilot_mass_reference_authority.json \
  --pod-id <POD_ID> \
  --zone-pad-id <ZONE_PAD_ID> \
  --channel left_heel \
  --sps 10
```

The initializer copies the exact Issue #59 and Issue #61 records/authorities into the session `provenance/` directory and derives all calibration/validation mass values from the Issue #61 authority.

Free-form mass CLI values are intentionally removed.

## Qualification re-verifies provenance

`fit/pilot_qualification.py` does not trust the copied IDs by themselves.

Before sensor metrics can pass, it verifies:

- copied selection authority fingerprint;
- copied selection-record fingerprint;
- manifest selection fingerprint;
- selected active load-cell ID;
- selected active HX711 ID;
- optional MCU ID;
- untouched-spare IDs;
- active/spare uniqueness;
- Issue #59 authority boundaries;
- copied Issue #61 source-record fingerprint;
- canonical recomputation of the Issue #61 authority;
- manifest mass IDs/values/uncertainties against that authority.

Only then does it evaluate calibration metrics, including conservative propagation of reference-mass uncertainty.

A manually edited manifest that swaps active and spare IDs must fail.

A tampered selection file must fail even if R² and validation error are excellent.

## Downstream chassis release

Issue #25 also re-validates the Issue #4 authority contract.

A fit-pilot authority must now include:

- `authority=x1_one_zone_pilot`;
- `scope=unpowered_fit_rig_only`;
- `qualified_for_four_zone_duplication=true`;
- nonempty Issue #59 selection authority fingerprint;
- nonempty Issue #59 selection-record fingerprint;
- `powered_operation_authorized=false`;
- a valid authority fingerprint.

Legacy provenance-less pilot reports cannot release chassis/brake purchasing.

## Exit condition

Issue #59 is complete for one pilot path when:

1. checkout/inventory evidence is valid;
2. receiving evidence is valid when ordered hardware is used;
3. one exact active load cell is selected;
4. one exact untouched load-cell spare remains identified;
5. one exact active HX711 is selected;
6. one exact untouched HX711 spare remains identified;
7. all stable IDs are unique;
8. optional MCU provenance is recorded when used;
9. `x1_fit_pilot_hardware_selection` validates;
10. Issue #4 session is initialized from that exact selection authority.

The next authority remains Issue #4 physical sensor qualification.
