# Worcester X1 Rev-C chassis trade

**Snapshot date:** 2026-10-01  
**Authority:** analysis only. This document cannot release procurement or powered operation.

Machine-readable facts live in `hardware/rev_c_chassis_trade_snapshot_2026-10-01.json`. Derived deltas are checked by `tools/analyze_rev_c_chassis_trade.py`.

## The three chassis hypotheses

| Property | Comp 95 | Pro Warren III | Agent Air |
|---|---:|---:|---:|
| Deck length | 950 mm | 980 mm | 1020 mm |
| Max deck width | 251 mm | **244 mm** | 284 mm |
| Deck construction | Power Lam | **Snowboard composite** | Snowboard composite |
| Published deck character | Medium | Stiff / high pop | Not captured |
| Deck mass | 5.0 lb | 5.8 lb | 7.2 lb |
| Complete unpowered mass | **14.6 lb** | 15.9 lb | Unknown in captured page |
| Wheelbase | 940 mm | **910–970 mm** | Unknown in captured page |
| Stock wheel | T1 200×50 / RSII | T1 200×50 / RSII | T3 200×50 / RSII |
| Brake path | Published compatible | Published compatible | Exact truck configuration must be verified |
| Electric integration | Retrofit path | Retrofit path | **Native AGENT ecosystem** |
| Current listed price | $499.95 | $649.95 | from $599.95 |
| Current availability note | page listed | waitlist | stock state not used as authority |

The table deliberately leaves unknowns as unknowns.

## Why the Pro Warren III changed the trade

The original Rev-C comparison had an awkward coupling:

- Comp 95 represented compact geometry;
- Agent represented snowboard-composite construction.

That made it impossible to know whether a preference came from width, length, construction, or electric integration.

The Warren breaks that coupling:

- it is 7 mm narrower than the Comp 95;
- its 980×244 mm rectangular envelope proxy is only about **0.28% larger** than the Comp 95's 950×251 mm proxy;
- it uses snowboard-composite construction;
- it is only 1.3 lb heavier complete than the Comp 95 reference;
- its published 910–970 mm wheelbase range is centered exactly on the Comp 95's 940 mm reference.

This makes Warren unusually useful as an experimental chassis.

If a received Warren is set to roughly 940 mm axle-to-axle, we can compare its deck/interface behavior against the Comp reference without intentionally changing wheelbase. We can then move to roughly 910 and 970 mm to explore the first-order wheelbase effect separately.

For the same effective steer angle, a bicycle-model sensitivity proxy makes curvature inversely proportional to wheelbase. The 910-to-970 mm Warren range therefore spans about a 1.066× curvature ratio. This is **not** a mountainboard handling prediction. It simply shows that the adjustment range is large enough to be worth measuring.

## Finished-mass pressure

The chassis trade is already constrained by battery mass before motors, ESC, guards, mounts or wiring enter the picture.

Using the current commercial mass references only:

| Reference | 35 lb trail target after 15 lb battery | 45 lb range target after 20 lb battery |
|---|---:|---:|
| Comp 95, 14.6 lb | 5.4 lb remaining | 10.4 lb remaining |
| Pro Warren III, 15.9 lb | 4.1 lb remaining | 9.1 lb remaining |
| Agent AIR | Unknown | Unknown |

These are **remaining budgets**, not feasibility claims.

The Warren's 1.3 lb complete-chassis penalty is small enough that it remains a serious experimental candidate, but large enough to matter when the trail target has only a few pounds left for the entire drive/control/protection stack.

That is another reason to preserve the modular energy strategy: if the range pack damages handling and carryability, a lighter installed trail pack plus cold-swapped spare energy can be a better product than forcing the maximum battery onto every ride.

## Wheel trade: air volume versus unsprung/rotating mass

The current MBS tire references create a surprisingly sharp trade:

| Tire | Published diameter | Width | Tire mass each |
|---|---:|---:|---:|
| T1 200×50 | 194 mm | 51 mm | 232 g |
| T3 200×50 | 194 mm | 51 mm | 235 g |
| Explorer 200×70 | 194 mm | **80 mm** | **540 g** |

The Explorer gets roughly 57% more published width without increasing published diameter.

But four Explorer tires add approximately:

- **1232 g / 2.72 lb** relative to four T1 tires;
- **1220 g / 2.69 lb** relative to four T3 tires;

before accounting for the hub change.

Explorer also requires Rockstar Pro II XL hubs. Those hubs are published at 370 g each, but the current Rockstar II product page does not publish a comparable mass, so the complete wheel-system delta is intentionally left unknown.

This changes the development order:

1. qualify 200×50 tire pressure/tread behavior first;
2. identify a real compliance or loose-surface traction deficiency;
3. only then pay the Explorer mass/rotational-inertia tax;
4. re-check the independent brake path because V5's captured hub list does not include Pro II XL.

The Explorer remains a valuable option, but not a free comfort upgrade.

### What about 9-inch T2?

The current 9-inch T2 reference is:

- 219 mm published diameter;
- 67 mm width;
- 581 g per tire;
- not compatible with Rockstar II hubs.

Relative to the 194 mm T1 reference, that buys roughly **25 mm more tire diameter**, or only **12.5 mm of nominal axle-height/ground-clearance gain**.

Four T2 tires alone add about **1396 g / 3.08 lb** versus four T1 tires, before the hub conversion. They are also 13 mm narrower than the 200×70 Explorer tire.

Therefore 9-inch is now a measured-failure fallback:

> keep the 194 mm wheel architecture unless real trail testing shows ground clearance is inadequate enough that ~12.5 mm nominal extra axle height is worth the mass, inertia, hub and brake-interface costs.

## Brake and drive constraints that cannot be averaged away

### Matrix III CNC 400 mm

MBS describes the 400 mm CNC truck as light/nimble and brake-compatible.

It is not directly AGENT G1 compatible in its stock 50 mm axle state. MBS says fitting 70 mm axles produces an ultra-wide 440 mm configuration that is G1-compatible.

That does **not** establish simultaneous V5 + G1 coexistence.

### Matrix III CNC 420 mm

The 420 mm CNC truck ships with 70 mm axles and is AGENT gear-drive compatible.

MBS explicitly lists it as not compatible with the MBS brake system.

This branch therefore cannot be treated as a universal electric+brake truck.

### G1

The G1 requires Matrix III 70 mm axles and supports couplers for Rockstar II and Rockstar Pro II XL hubs.

This makes drivetrain compatibility broader than brake compatibility.

## Current experimental sequence

### 1. Three-way stance geometry

Use the generated full-scale envelopes:

- `rev_c_comp95_deck_envelope.svg`
- `rev_c_pro_warren_iii_deck_envelope.svg`
- `rev_c_agent_deck_envelope.svg`

The cardboard/foam experiment can answer:

- usable heel/toe leverage;
- natural stance/yaw;
- stance width;
- deep-knee geometry;
- emergency step-off;
- repeatable remounting.

It **cannot** answer real deck flex or trail vibration.

### 2. Pre-purchase topology trade

Keep all four topology branches explicit.

The front-vs-rear traction sweep remains a rejection tool. Rear propulsion has the expected uphill load-transfer advantage, but that alone cannot select the brake architecture.

### 3. Inert pack envelope

Run the trail and range envelope test against the chassis that won the stance/deck decision.

The inert-pack authority must name the same chassis family as the final Issue #25 release.

### 4. Selection-aware procurement

A valid Issue #25 release no longer unlocks a generic preferred donor.

The procurement item must match the release authority's selected chassis/brake values.

Today the manifest contains a live purchase path only for the Comp 95/V5 reference. Therefore:

- if Issue #25 selects **Comp 95 + V5**, that measurement-stage path may open;
- if Issue #25 selects **Pro Warren III**, the old Comp 95/V5 cart stays blocked until Warren receives a fresh source/stock/price procurement entry;
- if Issue #25 selects **Agent**, the Comp cart likewise stays blocked;
- if the topology selects front vendor-hydraulic braking, V5 stays blocked.

This is intentional. Evidence chooses architecture; the manifest then proves the exact item being purchased matches that architecture.

## Current hypothesis, not a selection

The two strongest compact hypotheses are now:

**Comp 95**
- lowest known complete mass;
- lowest price of the three references;
- current brake-first geometry is well understood;
- simplest existing procurement path.

**Pro Warren III**
- narrowest envelope;
- snowboard-composite construction;
- adjustable wheelbase centered on the Comp reference;
- brake-compatible Matrix/RSII platform;
- small complete-mass penalty;
- direct F5X stance-angle support.

The deciding evidence is now appropriately physical rather than rhetorical:

> Does Warren's narrower snowboard-composite platform actually improve repeatable stance leverage and later trail feel enough to justify its extra mass, cost, availability uncertainty and custom electric packaging?

Until that evidence exists, neither candidate is purchase-authorized merely because it looks better in a table.
