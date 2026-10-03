# Worcester X1 complete staged ordering guide

> **REV-C PROCUREMENT OVERRIDE — 2026-09-30**
>
> The Comp 95, V5 brake, wheel/axle upgrades, drivetrain, ESC and traction-battery sections below are reference material only until Issue #25 produces a qualified `x1_rev_c_chassis_release` authority. The only intentionally orderable hardware before that is the inexpensive Issue #4 fit-pilot stack. The executable handoff is `docs/rev_c_chassis_release_playbook.md`.

This guide answers one question: **what should I buy, from whom, in what order, and what must remain unbought until evidence opens the next gate?**

It is intentionally conservative. Ordering a part is not fabrication authority, and fabrication authority is not powered-operation authority.

## 0. Before buying anything

If no parts have been ordered yet, initialize the complete private Day-0 workspace first:

```bash
python tools/init_x1_physical_kickoff.py rider/private/physical_kickoff
```

Then physically inventory `owned_inventory.json` and re-render the evidence-aware kickoff packet:

```bash
python tools/render_physical_kickoff_packet.py \
  --inventory rider/private/physical_kickoff/owned_inventory.json \
  --out rider/private/physical_kickoff/DAY0_KICKOFF.md
```

Issue #51 is convenience only. It reuses the same build/procurement authority below and must fail if any non-`BUY_NOW` item opens in the public/no-evidence state.

Check whether you already own equivalent versions of these optional Issue #4 items:

- ESP32-S3 DevKitC-1-compatible board;
- known-good USB data cable;
- M4 hardware and M4x0.7 positive-locking nuts;
- M5 screw/washer assortment;
- flexible stranded hookup wire and heatshrink;
- digital caliper suitable for geometry screening;
- metric/SAE feeler gauges;
- rigid scrap plywood or aluminum for the pilot base.

Do not rebuy owned tools just to match a storefront example. The manifest ceiling is a worst-case convenience budget, not a spending target.

Generate the live repository packet at any time:

```bash
PYTHONPATH=. python tools/render_procurement_packet.py \
  --out rider/private/current_procurement_packet.md
```

### Issue #56 checkout record

Once `owned_inventory.json` is resolved, do not jump directly from the rendered packet to an undocumented order.

Initialize:

```bash
python tools/init_x1_cart_a_checkout.py \
  rider/private/physical_kickoff/cart_a_checkout.json \
  --inventory rider/private/physical_kickoff/owned_inventory.json \
  --checkout-id CART-A-2026-10-02-A
```

Before payment, make the record `READY_TO_ORDER`, recheck stock and actual price, and run `tools/validate_x1_cart_a_checkout.py`.

Current public checkout policy requires:

- refreshed exact-source entries no older than seven days;
- stock rechecked at checkout;
- public source snapshot refresh if the price or stock state changed;
- every current BUY_NOW line resolved to order or physically verified owned stock;
- no MEASURE_FIRST or POWER_GATED item in the checkout;
- merchandise inside the BUY_NOW ceiling.

After payment, record confirmation references, shipping/tax, final total, set `ORDERED`, and validate again.

When shipments arrive, use `tools/init_x1_cart_a_receiving.py` and `tools/validate_x1_cart_a_receiving.py`. The receiving record is fingerprint-bound to the completed checkout, rejects unresolved substitutions/damage, and records one active candidate plus one untouched spare for the load-cell and HX711 paths.

Then create Issue #59 `x1_fit_pilot_hardware_selection` evidence with `tools/init_x1_fit_pilot_hardware_selection.py` and `tools/validate_x1_fit_pilot_hardware_selection.py`. Receiving proves what arrived; Issue #59 locks which exact physical units Issue #4 may calibrate.

Full procedures: `docs/x1_cart_a_checkout_receiving.md` and `docs/x1_fit_pilot_hardware_provenance.md`.

## 1. Cart A: order now for Issue #4

### October 1 source refresh

`hardware/order_sources_2026-10-01.json` live-refreshes only the three exact Cart A evidence-hardware anchors:

- Phidgets `3135_0`: $7.00, direct page reported 339 available;
- SparkFun `SEN-13879`: $4.95, direct page reported In stock;
- Espressif `ESP32-S3-DevKitC-1-N8R8` via Mouser: $15.00 current example, with roughly 1,050 immediately shippable; the Mouser page notes an 8% tariff may apply for U.S. shipment.

The load-cell and HX711 manifest prices therefore remain unchanged, and the MCU remains a `$20` ceiling/skip-if-owned item rather than being hard-coded to one storefront total.

Other tool, fastener, chassis, brake, wheel and drive entries in the October snapshot remain historical sourcing references unless their individual `last_verified_as_of` says otherwise. Every item still requires a final price/stock check at payment time.

### Required new evidence hardware

#### 2 x Phidgets 3135_0 50 kg single-point load cells

- Seller: Phidgets direct
- SKU: `3135_0`
- Snapshot price: `$7.00 each`
- Direct page: https://www.phidgets.com/?prodid=226
- Order quantity: `2`
- Role: one active pilot sensor + one untouched spare

Received-part checks:

- label the active unit `LC-PILOT-A` and keep the second physically separate;
- confirm no visible body/cable damage;
- confirm `M5x0.8` threaded interfaces;
- compare the real body and 40 mm mounting reference against the vendor drawing;
- identify the fixed/wire end versus loaded/free end before assembly.

Do **not** choose final M5 screw length from the catalog drawing. The real stack and safe thread engagement choose it.

#### 2 x SparkFun HX711 load-cell amplifiers

- Seller: SparkFun direct
- SKU: `SEN-13879`
- Snapshot price: `$4.95 each`
- Direct page: https://www.sparkfun.com/sparkfun-load-cell-amplifier-hx711.html
- Order quantity: `2`
- Role: one active ADC + one spare

Received-part checks:

- record the exact board revision/markings;
- inspect solder pads/connectors;
- identify the physical RATE configuration;
- start the qualification path at 10 SPS and confirm the logger header agrees with the hardware state.

### MCU: buy only if you do not already own a compatible board

Recommended exact current example:

- Espressif `ESP32-S3-DevKitC-1-N8R8`
- Mouser # `356-EP32S3DVKTC1N8R8`
- Snapshot price: `$15.00`
- Direct page: https://www.mouser.com/en/ProductDetail/Espressif-Systems/ESP32-S3-DevKitC-1-N8R8

This is preferable to a mystery clone because the firmware target and pin behavior remain tied to a documented Espressif DevKitC-1 family board. If you already own a known-compatible ESP32-S3 board, use it first.

### Pilot hardware

#### M5 sensor screw-length assortment

Target:

- thread: `M5x0.8`;
- several useful lengths spanning roughly 8-30 mm;
- flat washers;
- total target cost: `<= $12`.

Example convenience kit from the dated source snapshot is acceptable for **bench fit-up only**. Final screw length is selected after measuring the received load cell, pod/pad interface, washers and thread engagement.

Never allow an M5 screw to bottom into the sensor body or enter/clamp the flexure-sensitive region.

#### M4 pilot carrier hardware

Target:

- `M4x0.7` through-fasteners in several lengths;
- flat washers;
- at least four M4x0.7 nylon-insert lock nuts or equivalent positive locking;
- total target cost: `<= $10`.

These fasteners attach the one-zone pod to the pilot carrier only. They are not ride-structure fasteners.

### Wiring

Use a small quantity of flexible stranded wire, roughly `24-30 AWG`, plus heatshrink and strain relief. The 3135 itself uses fine 30 AWG cable, so the goal is not a giant harness. The goal is a quiet, mechanically supported bench connection that does not pull the sensor cable or HX711 pads.

Budget ceiling: `<= $10` if not already owned.

### USB cable

Use a cable that has already transferred data successfully, not merely charged a device. Match the connector on your selected DevKitC-1 board and host computer.

Budget ceiling: `<= $5`; skip if owned.

### Screening caliper

A cheap digital caliper is acceptable for the Issue #4 **geometry screen**, because the critical stop gap is measured with feeler gauges. Do not confuse display resolution with accuracy.

The dated source snapshot includes a low-cost WEN 10761 example at `$13.26`. Its display can resolve 0.01 mm, while current product Q&A puts absolute accuracy closer to +/-0.2 mm. That is acceptable for the repo's stated screening role, not for precision metrology.

If you already own a better steel caliper, use it.

### Feeler gauges

Use a metric/SAE blade set that covers the sub-millimeter region. The Harbor Freight Pittsburgh 63665 example was `$4.99` in the dated source snapshot. Stack clean blades when measuring a larger gap.

The two critical pilot boundaries are:

- unloaded stop gap: `0.30-2.00 mm`;
- minimum loaded clearance at the largest pilot mass: `>=0.15 mm`.

### Pilot base

Use a flat, rigid scrap board or aluminum plate large enough to clamp/bolt the generated 130 x 70 x 8 mm carrier securely. Spend as close to `$0` as practical. The base is not allowed to slide around while the load cell is carrying the test mass.

### Cart A cost rule

Repository hard ceiling if every convenience line must be purchased: **$120.90 before shipping/tax**.

A current example cart using the verified $15 official Espressif board and inexpensive example hardware/tools lands materially below that ceiling. The exact total is less important than refusing to buy unnecessary duplicates.

## 2. Fabrication needed for Cart A

Generate the one-zone CAD package:

```bash
PYTHONPATH=. python cad/generate_one_zone_pilot.py
```

You need only the one-zone carrier, pod, zone pad, reference cell and alignment-jig outputs required by `hardware/one_zone_pilot_assembly.md`.

For this low-load bench fixture, printed prototype parts may be used only if they are rigid, undamaged and positively fastened. If you outsource printing/machining, send the generated STL/STEP files rather than redrawing the geometry from screenshots.

Do not fabricate the other three sensor pods until Issue #4 qualifies.

## 3. Calibration-mass plan before assembly day

You need:

- at least three unique positive calibration masses;
- one independent validation mass not equal to a calibration mass;
- every mass `<=20 kg`.

Good practical sequencing is low / medium / high calibration masses with the lower two repeated on the descending path, followed by the independent validation mass.

The important word is **known**. Record the values you are actually treating as mass authority and how you obtained them. Do not type a nominal plate label and then describe it as laboratory calibration.

Create the private session only after those numeric values are known:

```bash
PYTHONPATH=. python tools/init_one_zone_pilot_session.py \
  rider/private/fit_rig/issue4-pilot \
  --hardware-selection rider/private/physical_kickoff/pilot_hardware_selection.json \
  --hardware-selection-authority rider/private/physical_kickoff/pilot_hardware_selection_authority.json \
  --pod-id POD-PILOT-A \
  --zone-pad-id PAD-PILOT-A \
  --channel left_heel \
  --sps 10 \
  --calibration-mass-kg <LOW> \
  --calibration-mass-kg <MID> \
  --calibration-mass-kg <HIGH> \
  --validation-mass-kg <VALIDATION>
```

## 4. Cart B: REV-C HOLD — source/watch only

### Currently instantiated donor purchase path: MBS Comp 95, part 10303

- New snapshot price: `$499.95`
- Direct page: https://www.mbs.com/shop/p/comp-95-mountainboard-silver-hex

This is the only complete donor currently represented by an orderable manifest item. That makes it the instantiated measurement path, **not** the automatically preferred Rev-C chassis. The donor includes:

- 2 x Matrix III CNC 400 mm trucks;
- 12 mm axles;
- 12x28 mm bearings;
- 4 x Rockstar II hubs;
- 4 x 8 inch T1 tires/tubes;
- Comp 95 PowerLam deck;
- F5 bindings and hardware.

Do not separately order a pair of trucks, hubs, bearings, wheels and bindings if the Comp donor path is the one eventually released.

### Other live Rev-C chassis candidates

The physical stance experiment now includes two additional candidates:

- **MBS Pro Warren III**: 980 x 244 mm deck envelope, snowboard-composite construction, adjustable 910–970 mm wheelbase, 15.9 lb complete published mass, brake-compatible Matrix III / Rockstar II architecture. The current product page is waitlisted and exposes a 10407 page heading versus 10406 embedded spec block, so it is **not** currently a checkout item.
- **MBS Agent AIR**: 1020 x 284 mm exact deck maximum from the dedicated deck spec, snowboard-composite construction, native AGENT electrification ecosystem. Current complete unpowered mass, exact wheelbase, and brake-compatible truck state remain unresolved in the captured evidence, so it is **not** currently a checkout item.

If Issue #25 selects Warren or Agent, the Comp 95 item stays blocked. A fresh sourced procurement entry for the selected chassis must be added and validated before checkout.

### Used-donor rule

A used current-generation Comp 95 is compelling at **<=$350** only when you can verify:

- it really has Matrix III trucks, not an older generation being described loosely;
- no deck crack, suspicious delamination or crushed insert area;
- no bent/damaged hanger or axle;
- no excessive wheel/bearing play;
- no stripped structural threads or obviously substituted hardware;
- bindings are present and serviceable;
- wheel/hub condition is adequate for measurement work.

A `$450` used board has little value advantage over the `$499.95` new reference once unknown wear and missing hardware enter the picture.

### Mechanical brake: MBS V5, part 15006

- Snapshot price: `$89.95`
- Direct page: https://www.mbs.com/shop/p/15006-mbs-v5-brake-system

MBS lists Matrix truck and Rockstar/Rockstar II hub compatibility. That makes it the right physical brake reference for the donor path, but the catalog does not replace Issue #14. We still measure the received rotor, brake-arm, cable and motion clearances and perform the unpowered brake tests.

### Cart B normal new-hardware subtotal

- Comp 95: `$499.95`
- V5 brake: `$89.95`
- combined: `$589.90` before shipping/tax

Do not place Cart B during the Rev-C trade study. A good used listing may be monitored, but low price is not permission to bypass the chassis release conditions.

## 5. Do not order the piecemeal fallback while donor-first is active

The following are reference/fallback components, not a second simultaneous shopping cart:

- Matrix III 400 mm truck `12300/12302` family;
- Rockstar II hub `1323x` family.

The current 400 mm CNC `12302` page was waitlisted in the dated vendor pass anyway. More importantly, buying it now duplicates interfaces already included in the donor.

Switch to piecemeal only by deliberately changing the repository strategy after the donor path fails sourcing, condition, or compatibility review.

## 6. Do not order 9-inch wheels yet

The MBS T2 9-inch tire `13120` is **not a drop-in tire replacement on the Comp 95's standard Rockstar II hubs**.

MBS currently lists T2 compatibility with:

- FiveStar;
- Tri-Spoke;
- Rockstar Pro II XL.

MBS's FiveStar description explicitly says that hub was modified from the Rockstar II design to support both 8- and 9-inch tires.

So a real four-wheel 9-inch conversion is not merely four `$29.95` tires plus four `$12.95` tubes. It also requires a compatible hub architecture and re-verification of bearings, brake geometry and drivetrain clearance.

At snapshot prices, even the inexpensive FiveStar route pushes the example wheel conversion to roughly `$231.40` before shipping; the Rockstar Pro II XL route is roughly `$351.40` before shipping.

The correct default is therefore simple: **use the donor's complete 8-inch wheelset first.**

## 7. Cart C: four-zone sensing after Issue #4 passes

Do not place this order now.

Once a real fingerprinted one-zone authority report contains `qualified_for_four_zone_duplication=true`, complete the four active sensor channels by adding:

- 2 more Phidgets 3135_0 load cells;
- 2 more SparkFun HX711 boards;
- the remaining three qualified pod/pad/carrier assemblies;
- four-channel harnessing/strain relief;
- the fixture IMU required by the Rev-B fit-session quality gate.

At that point the untouched pilot spare pair may enter service. If you want to preserve a spare after all four zones are active, buy a fifth load-cell/HX711 pair **then**, not now.

## 8. Future complete-board BOM, but no purchase authority yet

The full board will eventually require the categories below. Exact powered parts are deliberately not frozen because choosing one early can force several other expensive choices.

### Drivetrain

- MBS G1 dual gear drive `16101` or qualified alternative;
- 2 x sensored 6374-class motors;
- final motor KV, shaft, connector, mount pattern and gearing selected together;
- 70 mm Matrix III axles only if the measured brake/drive coexistence study requires them;
- motor/gear guards and service consumables.

### Motor control

- dual VESC-class controller or two matched controllers;
- voltage/current/ERPM/thermal headroom tied to the selected pack and motors;
- enclosure and CAN layout;
- remote/receiver interface.

### Traction power

- professionally assembled or qualified integrated traction pack;
- Rev-C trail energy class target roughly 500-650 Wh;
- Rev-C range energy class target roughly 950-1150 Wh;
- exact voltage/cell topology intentionally TBD;
- pack-builder-selected BMS with balancing and temperature monitoring;
- battery/system-approved matched charger;
- passive charge-cradle hardware only after the battery/charger/connector interfaces are frozen;
- DC-rated main fuse;
- service disconnect;
- precharge / anti-spark strategy;
- correctly sized high-current cable and connectors;
- crash-protected serviceable enclosure.

The first traction battery is **not** a DIY cost-saving exercise.

The current MBS 540/1080 packs and 530 W/1050 W chargers are **dated architecture references only**. Do not add any of them to a checkout packet merely because their voltage or connector appears compatible. Charger selection freezes with the professional battery/BMS architecture, and Issue #30 initially qualifies only an inert mechanical cradle.

### Supervisory electronics

- ESP32-S3 ECU;
- 3.3 V-compatible CAN transceiver;
- two front-wheel digital Hall sensors and magnets;
- low-noise 6-axis IMU;
- high-endurance microSD;
- optional GNSS;
- water-resistant low-voltage connectors;
- twisted-pair CAN;
- abrasion protection and strain relief.

### Enclosures and spares

- battery enclosure after pack-builder envelope signoff;
- ESC/ECU tray;
- bulkhead interfaces after connectors are selected;
- installed-size inner tube spare;
- installed-size bearings;
- exact installed fuse;
- spare Hall sensor/magnets;
- brake and drive consumables only after the received revisions are known.

See `hardware/planned_system_bom.json` for the machine-readable subsystem map.

## 9. Receiving inspection workflow

For every non-generic part:

1. photograph/record packaging and SKU/revision privately;
2. assign a stable hardware ID before assembly;
3. inspect for shipping damage;
4. measure the interface that matters to the next gate;
5. record discrepancies instead of modifying CAD until it 'fits';
6. preserve an untouched spare when the current plan calls for one;
7. keep receipts and vendor revision information with the private session notes.

A storefront description is evidence about what was sold. The received physical part is authority for what you actually have.

## 10. Ordering sequence summary

**Today:**

1. inventory owned tools/materials;
2. order 2 x 3135 + 2 x HX711;
3. buy the official ESP32-S3 board only if needed;
4. fill only the missing cheap hardware/tool gaps;
5. create the Issue #59 active/spare hardware selection;
6. fabricate one pilot stack using only the selected active sensor path;
7. collect real Issue #4 evidence.

**While fit-pilot parts are shipping:**

1. generate the Comp 95-class, Pro Warren III-class, and Agent-class full-scale deck envelopes;
2. compare stance width, heel/toe leverage and emergency step-off on the two envelopes;
3. monitor chassis availability only as market information, not purchase authority;
4. do not buy chassis, brake, standalone trucks/hubs, wheel upgrades, drivetrain, motors, ESC, battery, charger, or charge-dock electrical parts.

**After Issue #4 passes:**

1. complete the Rev-C full-scale deck comparison;
2. run the front-vs-rear traction sweep and four-branch pre-purchase topology trade;
3. qualify trail/range inert pack-envelope plausibility;
4. close Issue #25 and emit the chained `x1_rev_c_chassis_release` authority;
5. regenerate the procurement packet with the Issue #4 + Issue #25 evidence files;
6. only then place the released chassis/brake measurement order;
7. complete the four-zone sensing rig and qualify rider fit;
8. physically qualify the brake and unpowered chassis;
9. resolve final Issue #19 brake/drive topology;
10. only then continue toward the power freeze;
11. after the final pack/approved-charger/connector interfaces exist, prototype Issue #30 with an inert connector and pack fixture before any live charging integration.

That sequence is cheaper because every expensive purchase closes a measured interface rather than opening a new compatibility question.
