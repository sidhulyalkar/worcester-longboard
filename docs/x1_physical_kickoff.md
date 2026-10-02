# Worcester X1 Day-0 physical kickoff

**Issue:** #51
**Purpose:** turn the current repository state into one executable first physical session.
**New authority created:** none.

The Day-0 workflow combines the existing public procurement authority, Issue #4 one-zone fit-pilot checkout, and Issue #25 zero-cost chassis-release workspace without changing any of them.

## What you can do now

With no private evidence supplied, the repository currently permits only the Issue #4 BUY_NOW bench stack.

The public state must continue to hold:

- chassis/brake MEASURE_FIRST: blocked;
- wheel upgrades: blocked;
- drive/motors/ESC/battery: blocked;
- powered operation: blocked;
- public operation: blocked;
- dog-accompanied operation: blocked.

At the same time, the Comp 95 / Pro Warren III / Agent stance-envelope experiment costs essentially nothing and can begin immediately.

## One-command setup

Run:

    python tools/init_x1_physical_kickoff.py rider/private/physical_kickoff

The initializer creates a private workspace containing:

- DAY0_KICKOFF.md;
- NEXT_STEPS.md;
- owned_inventory.json;
- workspace_manifest.json;
- the existing Rev-C chassis-release templates and all three full-scale deck-envelope SVGs.

Nothing in this directory is procurement, fabrication, or ride authority.

## Inventory before shopping

Open rider/private/physical_kickoff/owned_inventory.json.

Allowed states are UNASSESSED, NEED_BUY, OWNED_EQUIVALENT, and OWNED_EXACT_UNUSED.

For optional-if-owned convenience items, a physically verified equivalent can avoid duplicate spending.

For required load-cell/HX711 evidence hardware, a vaguely similar part is not enough. A possible no-buy case requires an exact part match, enough verified quantity, and unused or known physical history. It still must be verified against the Issue #4 guide.

## Render the live checkout

After inventorying what you already own:

    python tools/render_physical_kickoff_packet.py --inventory rider/private/physical_kickoff/owned_inventory.json --out rider/private/physical_kickoff/DAY0_KICKOFF.md

The renderer consumes hardware/build_authority.json and hardware/procurement_manifest.json. It does not maintain its own orderability policy.

It deliberately refuses to run if the no-evidence state unexpectedly makes any non-BUY_NOW item orderable.

## Fingerprint the actual checkout

Issue #56 adds a private checkout/receiving evidence layer after the inventory is resolved.

Before payment, initialize a checkout record:

```bash
python tools/init_x1_cart_a_checkout.py \
  rider/private/physical_kickoff/cart_a_checkout.json \
  --inventory rider/private/physical_kickoff/owned_inventory.json \
  --checkout-id CART-A-2026-10-02-A
```

Set the record to `READY_TO_ORDER`, recheck stock/price, and validate it with:

```bash
python tools/validate_x1_cart_a_checkout.py \
  rider/private/physical_kickoff/cart_a_checkout.json \
  --inventory rider/private/physical_kickoff/owned_inventory.json \
  --out rider/private/physical_kickoff/cart_a_checkout_authority.json
```

The private record cannot relax the public source-freshness policy. Current refreshed exact-source entries have a maximum seven-day age, require stock recheck, and require the public source snapshot to be refreshed if price or stock changes.

After payment, record confirmation references, shipping/tax, and final total, switch to `ORDERED`, and validate again.

When packages arrive, use `docs/x1_cart_a_checkout_receiving.md` to create the fingerprint-bound receiving record before Issue #4 assembly.

This layer records what was actually bought and received. It does not qualify the sensor path.

## Current Cart A

The no-inventory worst-case ceiling remains **$120.90 before tax/shipping**.

The current Issue #4 set is:

- 2 x Phidgets 3135_0 50 kg load cells;
- 2 x SparkFun SEN-13879 HX711 boards;
- ESP32-S3 DevKitC-1-compatible board only if needed;
- known-good USB data cable if needed;
- M5 screw/washer assortment;
- M4 through-fastener/washer/nyloc assortment;
- flexible sensor wire and heatshrink;
- screening caliper if needed;
- feeler gauges if needed;
- rigid pilot base if needed.

The authoritative detail remains hardware/one_zone_pilot_bom.md, docs/complete_ordering_guide.md, and hardware/procurement_manifest.json.

## Zero-cost chassis experiment in parallel

Use the generated rev_c_release/deck_templates directory.

Build all three stance envelopes from taped paper, cardboard, foam board, or another harmless flat mockup. Do not use the envelope SVGs as structural deck CAD or hole-pattern authority.

Follow docs/rev_c_no_parts_chassis_experiment.md.

The useful questions are natural stance width, heel/toe leverage, repeatable remount, deep-knee carve posture, bilateral emergency step-off, and whether the envelope feels too narrow, wide, or long.

The experiment cannot measure real deck flex.

## When Cart A arrives

Before assembly:

1. photograph packaging/SKU/revision privately;
2. assign stable physical IDs;
3. inspect shipping condition;
4. preserve the untouched spare path;
5. verify real load-cell geometry and fixed/loaded orientation;
6. verify HX711 revision and RATE state;
7. measure the real fastener stack before choosing M5 screw length.

Generate the fixture with:

    python cad/generate_one_zone_pilot.py

Then follow hardware/one_zone_pilot_assembly.md.

Do not build all four sensing zones yet.

## Calibration masses are evidence

Before creating the Issue #4 session, establish the numeric masses you will actually use.

Requirements:

- at least three unique positive calibration masses;
- one independent validation mass;
- every mass <= 20 kg;
- validation mass not equal to a calibration mass.

Do not type a nominal dumbbell or plate label into the manifest and call it measured truth.

Only after the actual values are known should tools/init_one_zone_pilot_session.py be initialized with them.

## What not to buy

Do not use Day-0 as an excuse to buy:

- Comp 95, Pro Warren III, or Agent;
- V5 brake;
- standalone trucks/hubs;
- 9-inch wheel conversion;
- 70 mm axles;
- G1 drive;
- motors;
- VESC/ESC;
- traction battery;
- charger;
- high-voltage connectors;
- charge-dock electrical hardware.

Those remain governed by their existing gates.

## Day-0 exit condition

Day-0 is complete when:

1. owned optional items are physically inventoried;
2. the live Cart A packet has been rendered;
3. only actually-needed Cart A items are ordered or positively accounted for;
4. any placed order has a valid Issue #56 checkout record;
5. received shipments are reconciled through Issue #56 before assembly;
6. all three stance envelopes exist;
7. zero-cost chassis trials can begin;
8. every expensive and powered stage remains blocked.

The next evidence milestones remain:

    Issue #4 one-zone fit pilot
            +
    Issue #25 pre-purchase chassis evidence
            -> qualified Rev-C chassis release
            -> selected MEASURE_FIRST chassis/brake checkout

Issue #51 exists to make reaching those gates easy, not to bypass them.
