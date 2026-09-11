# Worcester X1 procurement snapshot — 2026-09-11

This snapshot is a **shopping authority**, not a fabrication or powered-operation authority. Prices and stock are time-sensitive. The repo should preserve the gating logic even when storefront prices change.

## Buying rule

Use three buckets only:

1. **BUY_NOW** — inexpensive parts needed to close an already-open physical evidence gate.
2. **MEASURE_FIRST** — parts whose exact geometry must be measured before the surrounding chassis is frozen.
3. **POWER_GATED** — high-energy drivetrain/power parts that stay blocked until the unpowered chassis and mechanical brake interfaces qualify.

## BUY_NOW — one-zone fit-rig pilot

| Qty | Part | Current direct-vendor reference | Snapshot unit price | Snapshot subtotal | Why now |
|---:|---|---|---:|---:|---|
| 2 | Phidgets 3135_0 50 kg single-point load cell | Phidgets | $7.00 | $14.00 | one active pilot cell + untouched spare |
| 2 | SparkFun SEN-13879 HX711 | SparkFun | $4.95 | $9.90 | one active ADC + spare; existing firmware supports 10/80 SPS |
| 1 | ESP32-S3 DevKitC-1 compatible board | reputable electronics vendor | target <=$20 | <=$20 | omit if already owned |
| 1 | USB data cable | local/owned | target <=$5 | <=$5 | logger power/data |
| 1 | M5 metric screw/washer assortment | local hardware / McMaster equivalent | target <=$12 | <=$12 | sensor fixed/loaded-end fit trials |
| 1 | M4 screw/washer/nyloc assortment | local hardware | target <=$10 | <=$10 | pilot pod/carrier fastening |
| 1 | flexible 4-conductor hookup wire + heatshrink | electronics supplier | target <=$10 | <=$10 | strain-relieved sensor wiring |
| 1 | digital caliper | generic 0.01 mm display class | target <=$20 | <=$20 | geometry screening, not metrology certification |
| 1 | feeler gauge set | generic | target <=$10 | <=$10 | overload-stop gap screening |
| 1 | rigid pilot base material | scrap plywood/aluminum preferred | target <=$10 | <=$10 | bench fixture |

**Pilot target:** about **$44 without tools/MCU**, or **about $120 including every convenience item**. Do not spend more to make the pilot pretty.

## MEASURE_FIRST — chassis/brake evidence

Do not buy the entire rolling chassis yet. The cheapest useful physical evidence purchase is the **brake interface itself**, because the public manual does not expose enough dimensions to CAD it faithfully.

| Part | Current reference | Snapshot price | Gate it closes |
|---|---|---:|---|
| MBS V5 Brake System | MBS 15006 | $89.95 | Issue #14 brake-arm/rotor/cable measurements |
| Matrix III 400 mm truck | MBS 12300/12302 family | about $119.95–$124.95 each | selected brake-first truck envelope |
| 70 mm Matrix III axle | MBS 12342 | $24.95 each | later drive-clearance/coexistence study |
| Rockstar II hub | MBS 1323x | $14.95 each | wheel/brake rotor interface reference |
| 9 in T2 tire | MBS 13120 | $29.95 each | real tire envelope; nominal storefront page also reports loaded shape dimensions |
| 9 in tube | MBS 13013 | $12.95 each | complete wheel measurement stack |

### Cheapest brake-measurement strategy

Do **not** buy two trucks + four wheels immediately. Buy the smallest stack that can close dimensional uncertainty:

- 1 brake-compatible Matrix III 400 mm truck
- 1 V5 brake kit
- 1 Rockstar II hub
- 1 T2 9 in tire
- 1 tube

This is enough to measure truck brake mounting, rotor/hub interface, wheel envelope, cable sweep and a single real wheel/brake assembly. Duplicate only after CAD + bench evidence pass.

## POWER_GATED — do not order yet

| Part | Current reference | Snapshot price | Why blocked |
|---|---|---:|---|
| dual sealed G1 gear drive | MBS 16101 | $399.95 | brake/drive coexistence and final axle choice unresolved |
| 2× 6374-class sensored motors | current market roughly $79–$129 each | ~$158–$258 | KV, shaft, mount pattern and voltage depend on final drive |
| dual VESC-class controller | Flipsky/MakerX market roughly $160–$245 | ~$160–$245 | voltage/current/thermal enclosure not yet frozen |
| 12S4P high-drain battery | reputable assembled pack | roughly $490–$600 | enclosure, range target, connector/BMS and crash protection unresolved |
| charger/BMS/contactors/fuse | pack-dependent | TBD | must be selected as one power architecture |

Buying these now can easily strand **$1,200+** behind a geometry change.

## Cost architecture

The cheapest credible X1 is not the cheapest part in every row. It is the build with the fewest expensive re-buys.

### Low-cost development path

- Stage A, one-zone sensing: **~$44–$120**
- Stage B, one-wheel brake/truck measurement stack: **roughly $270–$300** before shipping, depending truck SKU and whether existing hardware/tools can be reused
- Stage C, full unpowered rolling chassis: target **$550–$800** total cumulative spend, finalized only after Issues #12/#14
- Stage D, 2WD belt-drive powered prototype: target **$1,300–$1,700** total build cost if mechanical evidence supports the inexpensive belt path
- Stage E, sealed-gear premium version: likely **$1,700–$2,200+**, mainly because battery + G1 gear drive + ESC dominate cost

These are budget envelopes, not purchase authorizations.

## Where to save money

Save aggressively on generic low-risk items: wire, heatshrink, bench plywood, ordinary M4/M5 hardware, printed pilot parts, feeler gauges and non-certified screening calipers.

Do **not** economize blindly on: lithium battery assembly, high-current connectors/fusing, ESC thermal design, motor shaft quality, brake hardware or structural truck/axle interfaces.

## Vendor strategy

- **Phidgets direct** for the 3135_0 cells: direct geometry/source, very low unit price.
- **SparkFun direct** for SEN-13879: direct design revision, documentation and 10/80 SPS behavior.
- **MBS direct** for truck/brake/wheel interface parts: compatibility claims and technical drawings matter more than a small reseller discount.
- **Digi-Key/Mouser/Adafruit or an already-owned genuine-compatible board** for ESP32-S3: avoid paying $30–$50 for a commodity MCU board unless shipping consolidation makes it rational.
- **Local hardware store / McMaster only for critical known-grade fasteners**; generic assortments are fine for nonstructural pilot iteration.
- **Professionally assembled reputable battery vendor** for the traction pack. Do not make the first high-current pack a DIY cost-saving exercise.

## Promotion gates

- BUY_NOW -> MEASURE_FIRST only after Issue #4 produces real sensor evidence.
- MEASURE_FIRST -> rolling chassis duplication only after Issues #12/#14 pass their physical geometry/brake gates.
- POWER_GATED -> orderable only after unpowered rolling chassis, mechanical braking, enclosure volume and final drivetrain ratio/voltage are frozen.
