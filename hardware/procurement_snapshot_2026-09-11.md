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

The preferred chassis sourcing strategy is now **donor-first**, because a complete compatible mountainboard is cheaper than reconstructing its major assemblies from individual retail parts.

### Preferred donor: MBS Comp 95

Snapshot direct price: **$499.95**.

The current Comp 95 already provides:

- two 400 mm Matrix III CNC trucks
- Rockstar II hubs and 12x28 mm bearings
- four 8 in T1 pneumatic wheels/tubes
- Comp 95 PowerLam deck
- F5 bindings and mounting hardware
- a brake-compatible rolling chassis
- Matrix III trucks explicitly upgradeable to 70 mm axles for MBS gear-drive compatibility

At snapshot direct prices, reconstructing only the two trucks, deck, F5 bindings, four hubs, four 8 in tires/tubes and bearing set is roughly **$701 before miscellaneous hardware and duplicated shipping**. The complete Comp 95 therefore saves about **$200** while giving us a fully assembled reference platform.

**Best value target:** a structurally healthy used Comp 95 with Matrix III trucks at **<=$350**. Inspect deck delamination/cracks, truck/axle damage, bearing play and stripped hardware before treating a used donor as authority.

### 9-inch upgrade is optional, not default

Do not replace the donor's complete 8-inch wheelset just because X1 was initially modeled around nominal 9-inch tires. A four-wheel T2 + 9-inch tube conversion is about **$171.60** at current direct prices. First characterize clearance/terrain needs with the donor 8-inch wheels; upgrade only if the extra obstacle clearance materially improves the intended trail use.

### Brake evidence purchase

The V5 brake remains the first specialized chassis part worth purchasing because its public manual does not expose enough dimensions to CAD the interface faithfully.

| Part | Current reference | Snapshot price | Gate it closes |
|---|---|---:|---|
| MBS V5 Brake System | MBS 15006 | $89.95 | Issue #14 brake-arm/rotor/cable measurements |
| Complete MBS Comp 95 donor | MBS 10303 | $499.95 new | two Matrix III CNC trucks + complete rolling chassis |
| 70 mm Matrix III axle | MBS 12342 | $24.95 each | later drive-clearance/coexistence study |
| 9 in T2 tire | MBS 13120 | $29.95 each | optional real 9-inch terrain envelope |
| 9 in tube | MBS 13013 | $12.95 each | optional complete 9-inch wheel stack |

### Cheapest measurement strategies

**Strategy A, recommended if building the whole board:** buy one Comp 95 donor + V5 brake. This costs about **$589.90** new before shipping and immediately gives a complete unpowered chassis suitable for Issues #12/#14. A good used donor can reduce this dramatically.

**Strategy B, minimum laboratory-only spend:** one 400 mm Matrix III truck + V5 brake + one Rockstar II hub + one tire/tube. This remains useful if a donor cannot be sourced, but it produces less reusable hardware for nearly the same interface-measurement effort.

Do not buy 70 mm axles or a gear drive until the brake-first 50 mm axle configuration is measured and the coexistence question is modeled.

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
- Stage B, donor chassis + brake measurement: **~$590 new**, ideally **~$300–$440** with a good used donor
- Stage C, qualified unpowered chassis: little incremental cost if the donor survives qualification; custom guards/interfaces add material cost rather than replacing the chassis
- Stage D, 2WD belt-drive powered prototype: target **$1,200–$1,600 total** if we preserve the donor chassis and use a well-engineered belt drive
- Stage E, sealed-gear premium version: likely **$1,650–$2,100+ total**, mainly because battery + G1 gear drive + ESC dominate cost

These are budget envelopes, not purchase authorizations.

## Where to save money

Save aggressively on generic low-risk items: wire, heatshrink, bench plywood, ordinary M4/M5 hardware, printed pilot parts, feeler gauges and non-certified screening calipers.

Save structurally by buying **compatible assemblies**, not mystery structural parts. A complete donor board can be cheaper than individually sourcing known-good trucks, deck, hubs, bearings, bindings and wheel hardware.

Do **not** economize blindly on: lithium battery assembly, high-current connectors/fusing, ESC thermal design, motor shaft quality, brake hardware or structural truck/axle interfaces.

## Vendor strategy

- **Phidgets direct** for the 3135_0 cells: direct geometry/source, very low unit price.
- **SparkFun direct** for SEN-13879: direct design revision, documentation and 10/80 SPS behavior.
- **MBS direct** for truck/brake/wheel interface parts and the new-donor fallback: compatibility claims and technical drawings matter more than a small reseller discount.
- **Used market** for a Comp 95 donor only when the exact truck generation and physical condition can be verified. A target <=$350 creates meaningful savings; a $450 used board is not attractive versus a $499.95 new reference.
- **Digi-Key/Mouser/Adafruit or an already-owned genuine-compatible board** for ESP32-S3: avoid paying $30–$50 for a commodity MCU board unless shipping consolidation makes it rational.
- **Local hardware store / McMaster only for critical known-grade fasteners**; generic assortments are fine for nonstructural pilot iteration.
- **Flipsky/MakerX direct** are sensible future ESC/motor comparison points; choose only after the voltage/thermal architecture freezes.
- **Professionally assembled reputable battery vendor** for the traction pack. Do not make the first high-current pack a DIY cost-saving exercise.

## Promotion gates

- BUY_NOW -> MEASURE_FIRST only after Issue #4 produces real sensor evidence.
- Donor purchase does not imply final rider-interface drilling or powered use.
- MEASURE_FIRST -> rolling chassis authority only after Issues #12/#14 pass their physical geometry/brake gates.
- POWER_GATED -> orderable only after unpowered rolling chassis, mechanical braking, enclosure volume and final drivetrain ratio/voltage are frozen.
