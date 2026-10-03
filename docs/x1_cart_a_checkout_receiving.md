# Worcester X1 Cart A checkout and receiving evidence

**Issue:** #56  
**Scope:** Issue #4 BUY_NOW bench hardware only.  
**New procurement authority:** none.  
**Physical qualification authority:** none.

This workflow closes the gap between the Day-0 shopping checklist and the physical evidence path.

It records what was actually ordered, verifies that the checkout stayed inside current BUY_NOW authority, and then reconciles the delivered hardware against that exact order.

## 1. Start from the Day-0 inventory

First create the normal private kickoff workspace:

```bash
python tools/init_x1_physical_kickoff.py \
  rider/private/physical_kickoff
```

Physically inspect what you already own and update:

`rider/private/physical_kickoff/owned_inventory.json`

Every item must become one of:

- `NEED_BUY`;
- `OWNED_EQUIVALENT`;
- `OWNED_EXACT_UNUSED`.

Do not mark something owned from memory alone.

Required evidence hardware such as the load cells and HX711 boards can avoid a duplicate purchase only when the existing exact-part / quantity / known-history rules pass.

## 2. Initialize the checkout record

After inventory is resolved:

```bash
python tools/init_x1_cart_a_checkout.py \
  rider/private/physical_kickoff/cart_a_checkout.json \
  --inventory rider/private/physical_kickoff/owned_inventory.json \
  --checkout-id CART-A-2026-10-02-A
```

The initializer:

- consumes the current build-authority graph;
- consumes the current procurement manifest;
- fingerprints the dated source snapshot;
- refuses to initialize around an unexpectedly open non-BUY_NOW item;
- converts verified owned items into owned resolutions;
- converts explicit `NEED_BUY` inventory into `ORDER` rows;
- leaves uncertain inventory `UNRESOLVED`.

It does not place an order.

## 3. READY_TO_ORDER validation

Before checkout:

1. set `status` to `READY_TO_ORDER`;
2. record the timezone-aware intended checkout timestamp;
3. recheck stock for every ordered item;
4. for refreshed exact-source rows, recheck the same listed product page;
5. record actual unit prices;
6. calculate the merchandise total.

Then run:

```bash
python tools/validate_x1_cart_a_checkout.py \
  rider/private/physical_kickoff/cart_a_checkout.json \
  --inventory rider/private/physical_kickoff/owned_inventory.json \
  --out rider/private/physical_kickoff/cart_a_checkout_authority.json
```

A valid READY report means:

- every current BUY_NOW item is either ordered or physically accounted for;
- no blocked chassis/brake/power item entered the cart;
- merchandise stays inside the public BUY_NOW ceiling;
- required refreshed sources are still inside the public freshness window;
- refreshed source stock was rechecked;
- refreshed source price/SKU/source still matches the public snapshot.

It does **not** create new procurement authority.

## 4. Source freshness rule

The source-age limit is owned by:

`hardware/procurement_manifest.json`

The private checkout record cannot relax it.

Current policy:

- refresh-scope maximum age: **7 days**;
- refresh-scope stock must be rechecked at checkout;
- any recorded price or stock change requires refreshing the public source snapshot first.

This is deliberately strict for the exact evidence hardware.

Generic local convenience hardware remains bounded by the procurement-manifest price ceiling and must still be physically verified.

## 5. Record the completed order

After payment:

- set checkout `status` to `ORDERED`;
- record an order-confirmation reference for each ordered line;
- record shipping and tax;
- record the final order total.

Run the same checkout validator again.

The resulting fingerprinted report is:

`x1_cart_a_checkout_evidence`

For a complete order it has:

```text
valid = true
checkout_ready = true
order_record_complete = true
procurement_authority = false
physical_qualification_authority = false
fabrication_authority = false
powered_operation_authorized = false
```

Keep vendor order numbers, addresses, receipts, and other private purchase details under `rider/private/`.

## 6. Initialize receiving

When the shipment begins arriving:

```bash
python tools/init_x1_cart_a_receiving.py \
  rider/private/physical_kickoff/cart_a_receiving.json \
  --checkout rider/private/physical_kickoff/cart_a_checkout.json \
  --checkout-authority rider/private/physical_kickoff/cart_a_checkout_authority.json \
  --receiving-id CART-A-RECEIVE-01
```

The receiving record is fingerprint-bound to the completed checkout evidence.

It contains only items that were actually ordered.

Owned items are already represented by the Day-0 inventory and do not pretend to be newly received.

## 7. Receiving inspection

For every delivered line record:

- quantity received;
- observed package SKU;
- substitution state;
- visible shipping damage;
- backorder/missing quantity when applicable.

For the tracked electronic evidence hardware also assign stable IDs.

### Phidgets 3135

For two received units:

- one `PILOT_ACTIVE_CANDIDATE`;
- one `SPARE_UNTOUCHED`.

Example IDs:

- `LC-PILOT-A`;
- `LC-SPARE-A`.

### SparkFun HX711

For two received units:

- one `PILOT_ACTIVE_CANDIDATE`;
- one `SPARE_UNTOUCHED`.

Example IDs:

- `ADC-PILOT-A`;
- `ADC-SPARE-A`.

### ESP32-S3, if ordered

Assign one `PILOT_ACTIVE_CANDIDATE` hardware ID.

For each tracked unit record:

- exact-part match;
- packaging/markings captured privately;
- visible damage state;
- a concise physical-condition note.

Do not open/use the untouched spare just to prove it exists.

## 8. Partial shipments

A backorder can produce a valid `PARTIAL` receiving record.

That record must:

- state the received quantity;
- include a missing/backorder note;
- preserve stable IDs for the units actually received.

A partial report has:

`receiving_complete = false`

and cannot say all Issue #4 materials are accounted for.

## 9. Complete receiving validation

When all ordered lines arrive:

```bash
python tools/validate_x1_cart_a_receiving.py \
  rider/private/physical_kickoff/cart_a_receiving.json \
  --checkout rider/private/physical_kickoff/cart_a_checkout.json \
  --checkout-authority rider/private/physical_kickoff/cart_a_checkout_authority.json \
  --out rider/private/physical_kickoff/cart_a_receiving_authority.json
```

A complete report rejects:

- quantity mismatch;
- unexpected substitution;
- exact-source package-SKU mismatch;
- visible damage left unresolved;
- checkout fingerprint mismatch;
- duplicate hardware IDs;
- missing active/spare roles;
- missing condition/marking evidence.

The result is:

`x1_cart_a_receiving_evidence`

It still reports:

```text
physical_qualification_authority = false
fabrication_authority = false
powered_operation_authorized = false
public_operation_authorized = false
dog_accompanied_operation_authorized = false
```

## 10. What happens next

Only after receiving inspection should the hardware move into **Issue #59 selection**, then **Issue #61 mass-reference evidence**, then Issue #4. Receiving proves what arrived; it does not choose or qualify the sensor path or establish calibration masses.

Follow `docs/x1_fit_pilot_hardware_provenance.md`.

For ordered/received evidence hardware, Issue #59 must bind the stable IDs carrying `PILOT_ACTIVE_CANDIDATE` and `SPARE_UNTOUCHED` roles into a fingerprinted `x1_fit_pilot_hardware_selection` authority.

Only after that selection authority passes should the active pilot path move into Issue #4:

1. confirm the received load-cell geometry;
2. confirm fixed versus loaded end;
3. confirm HX711 revision and physical RATE state;
4. measure the real screw/washer stack;
5. generate the one-zone pilot CAD;
6. preserve the spare sensor and ADC untouched;
7. create and validate Issue #61 calibration/validation mass-reference evidence;
8. initialize the private one-zone qualification session from both Issue #59 and Issue #61 authorities.

Receipt evidence proves identity and condition at delivery.

Issue #4 proves whether the **Issue #59-selected** assembled sensor path actually performs against the **Issue #61-qualified** reference masses. If the active load cell or HX711 changes, do not reuse the old calibration session; create a new selection authority and a new Issue #4 session.

Those are intentionally different authorities.
