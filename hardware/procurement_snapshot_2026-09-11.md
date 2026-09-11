# Worcester X1 procurement snapshot — 2026-09-11

This snapshot is a **shopping authority**, not fabrication or powered-operation authority. Prices and stock are time-sensitive. Refresh storefront state immediately before checkout.

## Buying rule

Use three buckets only:

1. **BUY_NOW** — inexpensive parts needed to close an already-open physical evidence gate.
2. **MEASURE_FIRST** — parts whose exact geometry must be measured before the surrounding chassis is frozen.
3. **POWER_GATED** — high-energy drivetrain/power parts that stay blocked until the unpowered chassis and mechanical brake interfaces qualify.

`hardware/order_sources_2026-09-11.json` records the direct/example storefronts used for this snapshot. Repository authority wins over a shopping page.

## BUY_NOW — one-zone fit-rig pilot

| Qty | Part | Current reference | Snapshot unit price / ceiling | Why now |
|---:|---|---|---:|---|
| 2 | Phidgets 3135_0 50 kg single-point load cell | Phidgets direct | $7.00 | one active pilot cell + untouched spare |
| 2 | SparkFun SEN-13879 HX711 | SparkFun direct | $4.95 | one active ADC + spare; 10/80 SPS supported |
| 1 | ESP32-S3 DevKitC-1 compatible board | official Espressif DevKitC-1 example from Mouser | $15 example / <=$20 authority | omit if already owned |
| 1 | USB data cable | local/owned | <=$5 | logger power/data; must be data-capable |
| 1 | M5 metric screw/washer assortment | local / example retail kit | <=$12 | real load-cell stack chooses final length |
| 1 | M4 screw/washer/positive-locking hardware | local / example retail kit | <=$10 | pilot pod/carrier fastening |
| 1 | flexible stranded wire + heatshrink | electronics supplier | <=$10 | strain-relieved sensor wiring |
| 1 | digital caliper | screening class only | <=$20 | geometry screening, not metrology certification |
| 1 | feeler gauge set | generic/local | <=$10 | overload-stop gap measurement |
| 1 | rigid pilot base material | scrap plywood/aluminum preferred | <=$10 | bench fixture |

The machine-readable all-convenience ceiling is **$120.90**. A current example cart using the verified $15 official Espressif board and inexpensive retail screening tools is lower than that before shipping/tax. Skip every optional item you already own in equivalent form.

Do not purchase calibration masses merely to make the rig look laboratory-grade. The session initializer accepts actual known values. Borrowed/owned masses are acceptable if their chosen reference values and uncertainty are documented honestly.

## MEASURE_FIRST — chassis/brake evidence

The preferred chassis strategy is **donor-first**. The MBS Comp 95 packages the coherent structural interfaces more cheaply than reconstructing the major assemblies one row at a time.

### Preferred donor: MBS Comp 95 (10303)

Snapshot direct price: **$499.95**.

The current product definition includes:

- two 400 mm Matrix III CNC trucks;
- 12 mm axles and 12x28 mm bearings;
- Rockstar II hubs;
- four 8 in T1 pneumatic tires/tubes;
- Comp 95 PowerLam deck;
- F5 bindings and mounting hardware;
- brake-compatible truck/hub architecture;
- Matrix III trucks that may later accept 70 mm axles for gear-drive study.

**Best-value target:** a structurally healthy used current-generation Comp 95 at **<=$350**. Verify Matrix III generation and inspect deck cracks/delamination, hanger/axle damage, bearing play, stripped threads/fasteners, bindings and wheel condition before counting a used donor as evidence hardware.

The new donor + V5 brake pair is **$589.90 before shipping/tax**. For minimum cash burn, normally finish Issue #4 first, then place the chassis/brake order. A rare verified used donor <=$350 is the main reason to deviate from that timing.

### 9-inch upgrade is optional and is **not** a drop-in Rockstar II tire swap

The MBS 13120 T2 page lists FiveStar, Tri-Spoke, and Rockstar Pro II XL compatibility. It does **not** list the standard Rockstar II hub supplied on the Comp 95. The FiveStar product description explicitly notes that it modifies the Rockstar II design to support both 8- and 9-inch tires.

Therefore the old **$171.60** four-tire/four-tube figure was incomplete. A real 9-inch conversion also requires a compatible hub architecture. At snapshot direct prices:

- 4 x T2 tires: $119.80
- 4 x 9-inch tubes: $51.80
- 4 x $14.95 FiveStar hubs, if an appropriate color/revision is available: +$59.80
- minimum example wheel conversion: **about $231.40**, before shipping and before verifying bearing/brake compatibility
- 4 x $44.95 Rockstar Pro II XL hubs instead would raise the wheel conversion to **about $351.40** before shipping

This makes the donor's complete 8-inch wheelset the correct default. Do not buy 9-inch parts until terrain need, inflated geometry, hub/bearing compatibility, brake coexistence and drivetrain clearance are all measured.

### Brake evidence purchase

| Part | Current reference | Snapshot price | Gate it closes |
|---|---|---:|---|
| MBS V5 Brake System | 15006 | $89.95 | Issue #14 brake-arm/rotor/cable measurements and stop tests |
| Complete MBS Comp 95 donor | 10303 | $499.95 | Issues #12/#14 physical chassis |
| 70 mm Matrix III axle | 12342 | $24.95 each | deferred drive-clearance/coexistence study only |
| 9 in T2 tire | 13120 | $29.95 each | blocked optional terrain study |
| 9 in tube | 13013 | $12.95 each | blocked with optional 9-inch architecture |

The V5 page lists Matrix truck and Rockstar/Rockstar II compatibility. Exact received rotor, brake-arm, cable and clearance geometry still wins over the catalog.

## POWER_GATED — do not order yet

| Part | Current reference | Snapshot price | Why blocked |
|---|---|---:|---|
| MBS G1 dual gear drive | 16101 | $399.95 | brake/drive coexistence and final axle choice unresolved |
| 2x sensored 6374-class motors | model TBD | ~$158–$258 comparison envelope | KV, shaft, mount, connectors and voltage depend on final drive |
| dual VESC-class controller | model TBD | ~$160–$245 comparison envelope | voltage/current/thermal enclosure not frozen |
| professional 12S4P-class high-drain battery | builder/model TBD | ~$490–$600 comparison envelope | enclosure, range, cell/BMS/current architecture unresolved |
| charger/BMS/fuse/precharge/service disconnect/connectors | pack-dependent | TBD | must be selected as one power architecture |

Buying these now can strand **$1,200+** behind one mechanical-interface change. `hardware/planned_system_bom.json` records the full future subsystem map without pretending those TBDs are purchase decisions.

## Low-cost development path

- Stage A, Issue #4 one-zone evidence: **<= $120.90** all convenience items, usually lower when tools/materials are already owned.
- Stage B, donor chassis + V5 brake: **$589.90 new** before shipping/tax, or target **<=$439.95** with a <=$350 used donor plus new brake.
- Stage C, four-zone fit and Rev-B: buy only the additional sensor/harness/fabrication quantity opened by the Issue #4 authority.
- Stage D, qualified unpowered rolling chassis: preserve donor assemblies wherever the physical tests allow.
- Stage E, traction power: select one voltage/ratio/current/enclosure architecture only after the power gate freezes.

These are cost envelopes, not permission to skip gates.

## Where to save money

Save aggressively on generic low-risk bench items: wire, heatshrink, scrap base material, ordinary pilot hardware, screening calipers, feeler gauges and printed pilot parts.

Save structurally by buying **compatible assemblies**, not mystery structural pieces. Do not economize blindly on the traction battery, high-current fusing/connectors, brake hardware, structural truck/axle interfaces, or final power electronics thermal design.

## Promotion gates

- Issue #4 physical evidence opens four-zone duplication; software/CAD alone does not.
- Donor purchase does not imply final rider-interface drilling or powered use.
- Issues #12/#14 must qualify the unpowered chassis and mechanical brake before surrounding geometry freezes.
- 9-inch wheels remain a measured-need option, not a default upgrade.
- POWER_GATED parts remain blocked until the complete power architecture is explicitly qualified.
