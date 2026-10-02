# Worcester X1 Rev-C environmental durability and service recovery

**Status:** inert packaging/service qualification program.  
**Issue:** #39.  
**IP rating:** none claimed.  
**Waterproof claim:** none.  
**Powered wet operation:** not authorized.

Worcester X1 is intended to tolerate ordinary trail contamination without requiring heroic maintenance after every ride.

That means environmental durability is not just "seal the battery box."

The complete contamination path includes:

- wheel spray;
- airborne dust and grit;
- mud accumulation;
- cable and hose entries;
- enclosure seams;
- service disconnects and connectors;
- drainage paths;
- bearings;
- steering interfaces;
- brake hardware;
- sacrificial armor and guards;
- cleaning and drying.

A board that survives a splash but cannot be safely cleaned or serviced is not environmentally robust.

## 1. Design principle

Use this hierarchy:

```text
shed contamination
    -> shield direct exposure
    -> drain what gets past the shield
    -> keep protected zones isolated
    -> make inspection easy
    -> make cleaning/drying repeatable
    -> replace sacrificial contamination parts
```

Do not begin with the assumption that every component must be hermetically sealed.

Sealing can create its own failures when water gets in and cannot drain.

## 2. Reference standards without certification claims

The dated reference snapshot is:

`hardware/rev_c_environmental_durability_snapshot_2026-10-01.json`

ISO 20653:2023 is used as a conceptual reference for dust/foreign-object and water protection of road-vehicle electrical enclosures.

ASTM B117-26 is used only as a reference for controlled comparative corrosion testing. ASTM explicitly cautions against treating salt-fog duration as a stand-alone predictor of natural service life.

X1 does not claim compliance with either standard from these project fixtures.

No project-generated splash or grit trial creates an IP rating.

## 3. Why Issue #39 sits before final power freeze

Issue #21 first creates a physically realistic inert pack/enclosure mass and mounting system.

Issue #39 then tests the candidate enclosure/interface geometry for:

- contamination shedding;
- ingress paths;
- drainage;
- connector servicing;
- wheel/brake/steering recovery;
- retained moisture;
- seal damage;
- chafe;
- corrosion/fretting indicators.

That happens **before** final power architecture freeze so obvious enclosure and harness mistakes can still be changed cheaply.

Passing Issue #39 does not validate the final energized battery, ESC, BMS or high-voltage harness.

Those remain future electrical-environmental work.

## 4. Initial safety boundary

The first environmental campaign must have:

- no live traction battery;
- no traction voltage;
- no charger connected;
- no powered vehicle;
- no pressure washer;
- no immersion;
- no intentional energized wet connector;
- no ride test.

Use:

- inert enclosure surrogates;
- disconnected connector specimens or installed inert/disconnected interfaces;
- low-energy mechanical fixtures;
- visible/absorbent ingress witnesses as appropriate.

The purpose is to discover bad geometry and service assumptions without high energy present.

## 5. Session initialization

Create the private session only after qualified rolling-chassis and dummy-pack authorities exist:

```bash
python tools/init_rev_c_environmental_session.py \
  rider/private/environmental/session-01 \
  --chassis-authority rider/private/chassis/donor-a/chassis_authority.json \
  --dummy-pack-authority rider/private/dummy_pack/v1/dummy_pack_authority.json \
  --candidate-enclosure-id INERT-ENC-A \
  --harness-revision-id HARNESS-SURROGATE-A
```

The initializer verifies both upstream fingerprints before creating the workspace.

## 6. Interface inventory

Before applying any contamination, inventory every exposed interface.

Examples:

- enclosure perimeter seam;
- cover screws and washers;
- service disconnect cover;
- charge-port cover;
- ESC/sensor enclosure seam;
- cable glands;
- CAN/sensor connector entries;
- brake cable/hose path;
- motor cable exits;
- bearings;
- tire valves;
- skid/guard joints;
- drainage holes;
- cooling openings.

Every inventory entry needs:

- stable ID;
- function;
- exposure location;
- protection method;
- drainage/shedding method;
- external inspection method;
- service method;
- external protection that can be inspected without breaking the primary seal;
- strain relief or explicit not-applicable state;
- direct-spray orientation/shielding check.

The goal is not paperwork. It is to eliminate "I forgot that connector exists."

## 7. Exposure cycle A: dry grit

Use a declared inert dry-grit surrogate.

Record:

- media description;
- quantity;
- exposure duration;
- board/enclosure orientation;
- application method.

Do not use a high-energy abrasive blast.

The test asks:

- does grit accumulate in steering/brake/wheel motion?
- does it pack into drain paths?
- does it reach protected witness zones?
- can the guard/enclosure still be serviced?
- do cable/hose paths start chafing?
- do exposed fasteners become difficult to inspect?

The media and method must be repeatable enough that a later redesign can be compared.

## 8. Exposure cycle B: splash

Use an inert enclosure and a declared clean-water splash surrogate.

Record:

- total water quantity;
- duration;
- orientation;
- distance/application method.

Do not pressure wash the board to discover whether it leaks.

The initial splash test asks:

- does the exterior shed water away from vulnerable entries?
- do drip loops work?
- do drains remain functional?
- does a protected-zone witness remain dry?
- does water pool against a seal or connector?
- does water enter the brake/steering service path in a way that prevents normal function?

A passing surrogate splash trial is not an IP test.

## 9. Exposure cycle C: mud surrogate

Mud is different from water because it can block a drainage path after the water is gone.

Use a declared inert, non-energized mud surrogate.

Look for:

- blocked drains;
- packed debris around bearings;
- brake mechanism restriction;
- steering return degradation;
- buried connector latches;
- clogged guard exits;
- contamination trapped against the enclosure shell;
- service fasteners becoming inaccessible.

The correct design often uses geometry to keep mud moving through the system rather than trying to exclude every particle.

## 10. Connector service recovery

Connector trials remain disconnected and unenergized.

For each exposed connector type:

1. identify connector and role;
2. record the selected manufacturer's service/cleaning guidance where available;
3. apply only the declared contamination surrogate;
4. clean using the documented compatible method;
5. inspect seal and contacts;
6. re-seat normally;
7. verify positive latch/retention;
8. confirm the cable was never used as a pull handle.

Fail if:

- contamination passes the intended seal;
- a contact/pin is damaged;
- a seal moves or tears;
- the connector cannot fully seat;
- retention is ambiguous;
- cleaning requires an unapproved aggressive solvent or tool.

A connector cap is useful only if it remains attached, cleanable and serviceable.

## 11. Wheel, bearing, brake and steering recovery

After the exposure block and cleaning:

- all wheels must free-spin appropriately;
- new bearing play is a failure;
- tire valves remain accessible;
- mechanical brake must release without drag;
- brake actuation must remain normal;
- brake friction surfaces must not be contaminated by cleaner/lubricant runoff;
- steering must return freely;
- wheel/brake/steering service must not require opening the traction enclosure.

This is where environmental durability becomes a maintenance-system property rather than an enclosure property.

## 12. Drying and post-exposure inspection

Define one drying method before the campaign.

Record:

- drying method;
- declared drying time;
- drain-path state;
- visible moisture;
- hidden-zone witness state;
- corrosion/discoloration;
- fretting;
- harness chafe;
- fastener/witness movement;
- cracks or seal damage;
- contamination-guard condition.

The initial candidate fails if visible or witnessed retained moisture remains in a protected zone after the declared dry process.

If drying requires disassembling the primary enclosure every time, treat that as a design deficiency unless the final manufacturer explicitly intends that service pattern.

## 13. Cleaning policy

Prefer the least aggressive method that works.

Default hierarchy:

1. let loose dirt dry when appropriate;
2. brush/vacuum/wipe bulk debris from exterior surfaces;
3. use low-pressure compatible cleaning only where the selected parts allow it;
4. dry and inspect;
5. service individual wear interfaces as needed.

Do not assume:

- pressure washer compatibility;
- immersion compatibility;
- arbitrary solvents;
- arbitrary degreasers;
- compressed air directly into seals/bearings/connectors;
- lubricants near brake friction surfaces.

The final maintenance instructions must follow the selected components' actual guidance.

## 14. Corrosion screening

Do not run a DIY salt-fog test on the assembled traction system.

If material/coating choices remain ambiguous, use representative coupons or an appropriate lab.

ASTM B117 can provide comparative corrosion information for controlled specimens, but the project must not convert "hours in salt fog" directly into years of trail life.

Natural exposure depends on:

- contaminants;
- wet/dry cycling;
- material couples;
- coating damage;
- temperature;
- cleaning;
- trapped moisture;
- local geometry.

## 15. Qualification

After the manifest is complete:

```bash
python tools/qualify_rev_c_environmental_durability.py \
  rider/private/environmental/session-01/environmental_manifest.json \
  --chassis-authority rider/private/chassis/donor-a/chassis_authority.json \
  --dummy-pack-authority rider/private/dummy_pack/v1/dummy_pack_authority.json \
  --out rider/private/environmental/session-01/environmental_authority.json
```

A passing report is:

`x1_environmental_inert_candidate`

It must still report:

```text
ip_rating_claimed = false
waterproof_claimed = false
corrosion_life_claimed = false
electrical_wet_operation_qualified = false
live_battery_test_authorized = false
procurement_authority = false
powered_operation_authorized = false
```

## 16. Future energized environmental validation

After final power architecture exists, a separate electrical program will still be required.

That future work should verify the selected system's actual:

- battery enclosure;
- BMS;
- ESC;
- high-voltage connectors;
- service disconnect;
- fuse/precharge interfaces;
- low-voltage harness;
- insulation/fault behavior;
- drying/service instructions.

No energized wet test should be invented casually from this document.

Use qualified equipment, manufacturer guidance and appropriate test expertise.

## 17. Future dirty/wet ground testing

Wet or contaminated powered ground testing requires, separately:

- future powered-operation authority;
- authorized venue evidence;
- completed electrical environmental validation;
- independent mechanical braking;
- controlled low-speed progression;
- post-run inspection.

No public trail or park permission is implied.

## 18. Maintenance loop

Environmental durability should eventually become a short rider maintenance loop:

### Before ride

- tire pressure;
- wheel/bearing condition;
- brake operation;
- visible connector/cable state;
- drain/guard obstruction check;
- enclosure/guard fastener witness marks.

### After dry dusty ride

- remove loose debris;
- inspect guards/drains;
- inspect bearing/brake contamination;
- check harness abrasion;
- record unusual ingress.

### After wet/muddy exposure

- remove bulk mud using approved low-aggression method;
- keep runoff away from brake friction surfaces;
- clear drains;
- dry using qualified procedure;
- inspect protected witness/indicator strategy;
- inspect connectors externally;
- service bearings/brake only as their actual condition requires.

The best maintenance plan is short enough that it gets performed.

## Exit condition

The inert environmental candidate closes when:

1. upstream chassis and dummy-pack fingerprints are valid;
2. every exposed interface is inventoried;
3. dry grit, splash and mud-surrogate cycles pass;
4. protected zones show no prohibited ingress;
5. drains/shedding paths work;
6. connector service recovery passes;
7. wheel/bearing/brake/steering recovery passes;
8. no retained moisture, seal damage, chafe, migration or corrosion indicator remains;
9. no live energy was used;
10. the report remains explicit about what it does **not** qualify.

Only then should final power architecture freeze around that enclosure/interface concept.
