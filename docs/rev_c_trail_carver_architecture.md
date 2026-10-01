# Worcester X1 Rev-C Trail-Carver architecture

**Status:** architecture trade study, 2026-09-30.  
**Purchase authority:** inexpensive fit-pilot parts only. Chassis, brake, wheel, drive, ESC and traction-battery purchases remain held until the Rev-C release conditions in `hardware/rev_c_requirements.json` are closed.

## Why Rev-C exists

The original X1 program correctly prioritized controllability, redundant stopping, rider-specific fit, inspectable mechanical interfaces and evidence-first commissioning. That remains the safety foundation.

Rev-C changes the product target. X1 is no longer merely "an off-road electric mountainboard." It is being optimized as a compact **electric trail-carver** with four simultaneous jobs:

1. progressive, snowboard-inspired carving on dirt, gravel and brush paths;
2. enough compliance and traction to stay composed over loose and irregular ground;
3. practical mixed-surface range for ordinary exploration;
4. an intentionally calm, low-jerk mode for riding near a leashed dog.

Headline acceleration and top speed are not design priorities.

## Product thesis

The target is not a Onewheel clone, a suspension buggy, or a conventional high-power e-skate with mountainboard wheels.

The target is:

> a light-ish four-wheel pneumatic mountainboard with a rider-scaled deck, progressive steering, an independent friction-or-hydraulic stopping system, modular energy capacity, sacrificial trail armor, and optional bounded traction/carve assistance.

Rev-C borrows product lessons from three distinct families without importing their whole architecture:

- **Onewheel Rally XL:** large pneumatic air volume, low ride height, digital ride shaping and smooth low-speed response;
- **MBS Agent:** electric-ready Matrix hardware, quick-swap energy, sealed geared drive, skid protection and high-volume Explorer tires;
- **Propel Endeavor:** evidence that suspension dramatically improves rough-terrain isolation, while also showing the mass and complexity tax that Rev-C should avoid unless simple compliance proves insufficient.

## Design principles

### 1. Snowboard feel is a system property

"Carvy trucks" alone do not create snowboard feel. X1 must tune the full roll-to-yaw chain:

```
rider ankle/knee input
        ↓
footbed + binding leverage
        ↓
deck torsion/flex
        ↓
truck roll/steer response
        ↓
pneumatic tire lateral compliance
        ↓
optional small bounded differential torque bias
        ↓
vehicle yaw response
```

A change anywhere in that chain can make the board feel dead, twitchy or natural.

The rider-fit program therefore becomes a handling program too. Rev-B foot geometry should measure not only static comfort but leverage, emergency step-off, remount repeatability and how much roll input is required to produce steering response.

### 2. Pneumatics are the first suspension stage

Independent suspension remains a fallback, not a default.

Rev-C uses compliance in layers:

1. pneumatic tire deformation for sharp trail chatter;
2. deck and truck compliance for slower chassis motion;
3. local elastomer/footpad compliance for high-frequency vibration;
4. rider joints as the final active suspension stage.

Only if this stack fails measured terrain-control tests should an independent-suspension chassis reopen.

The executable tuning protocol is `docs/rev_c_ride_compliance_program.md`. Its order is deliberately cheap and reversible: stock 200x50 pneumatics → Matrix III shock-block position → wheelbase where adjustable → real deck/footbed behavior → alternate elastomer hardness → larger-volume wheel architecture → independent suspension. Objective IMU metrics and rider observations remain separate; the program does not produce a single "snowboard feel" score.

### 3. Use tire volume before tire diameter

A taller tire buys obstacle clearance but raises axle height and therefore the rider.

A wider, higher-volume tire can add flotation, bump absorption and loose-surface contact area without the same ride-height increase.

That is why the MBS Explorer 200x70 architecture is now a first-class Rev-C study branch rather than jumping directly from 8-inch tires to nominal 9-inch tires.

Important limitation: the current MBS Explorer tire requires Rockstar Pro II XL hubs, while MBS currently lists the V5 brake as compatible with Rockstar/Rockstar II rather than Pro II XL. This is an unresolved interface, not permission to fabricate a spacer.

### 4. Independent friction or hydraulic braking remains mandatory

Regenerative/motor braking is useful but not independent stopping authority.

The current MBS V5 documentation places that specific brake on the rear of the board. Rev-C therefore does not casually move the V5 to the front to make drivetrain packaging easier.

However, a vendor-engineered **front** mountainboard brake architecture also exists: TRAMPA's Infinity truck integrates Magura HS11 hydraulics with custom wheel discs and explicitly mounts the brakes at the front. That does not make TRAMPA brakes a drop-in Matrix/Rockstar solution. It does prove that "rear 2WD + independent front braking" is a legitimate architecture family worth studying rather than dismissing.

Four live topology branches remain:

#### A. Rear V5 + front 2WD

**Why it exists:** cleanest way to preserve the documented rear brake.

**What could kill it:** inadequate front traction on loose uphill terrain, undesirable steering torque, or unacceptable front/rear track-width mismatch.

#### B. Rear V5 + rear 2WD on shared wheel-end geometry

**Why it exists:** best conventional drive traction if packaging is clean.

**What could kill it:** brake rotor, brake arm, cable, drive coupler, gearbox and guard physically competing for the same axial/swept space.

The vendor statement that a 400 mm Matrix III can accept 70 mm axles for Agent gear-drive compatibility does **not** prove that V5 geometry still works after the wheel is moved outward.

#### C. Rear 2WD + vendor-engineered front hydraulic braking

**Why it exists:** rear drive preserves favorable uphill traction and leaves the front axle responsible for independent stopping. TRAMPA demonstrates this as a complete commercial truck/wheel/brake system.

**What could kill it:** the TRAMPA front-brake ecosystem is not mechanically interchangeable with Matrix/Rockstar hardware. Mixing truck families may create steering geometry, track-width, wheel-bearing, spare-part and service problems. Front brake balance also needs controlled low-energy testing.

This branch is permission to study a complete proven subsystem or compatible chassis family, **not** permission to invent a safety-critical adapter between unrelated systems.

The non-authoritative `simulation/rev_c_topology_traction_sweep.py` now sweeps grade, normalized CG position/height and acceleration to compare the friction coefficient demanded by front versus rear 2WD. Its job is to cheaply reject a traction-poor topology before we spend money on packaging. It deliberately uses normalized geometry rather than rider-specific measurements and cannot qualify real tire/terrain grip.

#### D. Alternate rear drive preserving the V5 envelope

A belt or other compact drive may win if it provides a cleaner safety-critical mechanical stack than the sealed G1 path.

"Simpler to package safely" beats "more elegant drivetrain."

### 5. Low center of mass competes with ground clearance

A giant under-deck battery is attractive dynamically but vulnerable on trail obstacles.

A giant top battery is protected but raises roll inertia and center of mass.

Rev-C therefore treats pack placement as an optimization problem rather than a style choice. The final solution may use:

- a compact low-profile central top pack;
- a protected shallow under-deck pack with a sacrificial skid;
- or another measured arrangement that preserves rider stance and serviceability.

The live battery will never be used to discover whether the enclosure hits roots.

### 6. Range is modular, not permanently heavy

Two energy classes are targeted:

- **Trail:** roughly 500-650 Wh. Keep the vehicle playful and carryable.
- **Range:** roughly 950-1150 Wh. Prioritize exploration and round-trip margin.

The board interface should support both without redesigning the chassis.

A pack change is initially a powered-off cold swap. Hot swapping is out of scope unless the eventual battery/ESC system explicitly supports and qualifies it.

### 6A. Finished mass is now an explicit feasibility gate

Current commercial reference masses make the original 35 lb trail / 45 lb range goals aggressive:

- Comp 95 unpowered reference: 14.6 lb;
- MBS AGENT 540 battery reference: 15 lb;
- MBS AGENT 1080 battery reference: 20 lb.

That creates a simple lower-bound warning:

```
trail target: 35.0 - 14.6 - 15.0 = 5.4 lb remaining
range target: 45.0 - 14.6 - 20.0 = 10.4 lb remaining
```

Those remaining budgets still have to cover drivetrain, motors, controller, guards, mounting hardware, harness changes and any structural additions. Positive headroom therefore does **not** prove either target is achievable.

`simulation/rev_c_mass_budget.py` makes this accounting executable. Rev-C should prefer reducing installed energy, duplicated structure and enclosure mass before sacrificing independent braking, trail armor or positive battery retention merely to hit a cosmetic weight number.

A two-pack strategy remains especially attractive if one small installed pack plus a carried/swapped spare preserves handling better than permanently carrying the full range mass.

### 7. Charging must be mundane

A successful daily vehicle should not need a ritual involving exposed high-current connectors.

Rev-C targets:

- a stable parking/charging stand;
- protected charge alignment;
- no traction contacts exposed to accidental shorts;
- moderate normal charging;
- battery-builder-approved faster charging only when useful;
- a routine daily 80-90% SOC option if supported by the selected BMS/charger;
- 100% trip charge when maximum range is actually required.

The charger should remain off-board unless a future requirement justifies carrying its mass and heat.

## Current chassis comparison

### Comp 95 reference

Current published facts:

- 950 mm deck length;
- 251 mm maximum deck width;
- 940 mm axle-to-axle;
- 6.6 kg complete unpowered mass;
- Matrix III CNC 400 mm trucks;
- Rockstar II hubs;
- T1 200x50 tires;
- V5 brake compatibility.

Why Rev-C still likes it:

- narrower rider envelope;
- low mass;
- known brake path;
- high Matrix tuning range;
- relatively inexpensive donor-first mechanical baseline.

Why it is no longer automatically orderable:

- Rev-C must first decide whether its deck width/flex is better for the rider than the snowboard-composite options;
- the future powered topology could force wheel/hub/truck changes that erase the donor savings.

### Pro Warren III reference

Current published facts:

- 980 mm deck length;
- 244 mm maximum deck width;
- 910-970 mm adjustable axle-to-axle range;
- 15.9 lb complete unpowered mass;
- 5.8 lb deck mass;
- snowboard-composite construction;
- published stiff/high-pop deck character;
- Matrix III CNC / Rockstar II / T1 200x50 architecture;
- brake-compatible complete board;
- direct F5X snowboard-style binding support.

Why it matters:

This candidate breaks the previous Comp-vs-Agent trade in a useful way. It is **narrower than the Comp 95 while retaining snowboard-composite construction**, and the multiple truck positions give us an unusually large wheelbase-tuning experiment without fabricating a new deck.

Why it is not automatically selected:

- the stiff/high-pop construction could be too lively or fatiguing for the desired low-speed rough-trail feel;
- it adds 1.3 lb over the Comp 95 before electrification;
- its current product page is waitlisted;
- the current page exposes a 10407 page heading but a 10406 embedded spec identifier, so the exact received revision must be verified;
- battery packaging remains less integrated than the Agent ecosystem.

### Agent Air reference

Current published facts:

- 1020 x 284 mm snowboard-composite deck;
- 200x50 T3 tires on Rockstar II hubs;
- Matrix III steering;
- direct compatibility with the Agent electrical ecosystem.

Why it matters:

It is evidence that we can get real snowboard-style composite construction and a fully supported electric ecosystem without going to independent suspension.

Its 284 mm maximum width may, however, be excessive for the rider. Width that looks "stable" on paper can reduce edge leverage for small feet.

### Agent Explorer reference

Current published facts:

- same 1020 x 284 mm deck family;
- 200x70 Explorer tires;
- published Explorer tire physical reference about 194 mm diameter and 80 mm inflated width;
- Rockstar Pro II XL hubs;
- Agent electrical compatibility.

Why it matters:

This is the strongest current argument for studying **air volume before diameter**.

Why it is not automatically selected:

- V5 compatibility with the Pro II XL wheel architecture is unresolved;
- wider tires add mass and rotational inertia;
- extra footprint may add steering effort or scrub on firm surfaces.

## Onewheel lesson, translated rather than copied

The current Rally XL benchmark combines:

- a 12 x 7-6 treaded tire;
- increased pneumatic air volume;
- a deliberately low effective ride height;
- long stance leverage;
- software ride shaping;
- 18-28 mile published range;
- 34 lb published mass.

What X1 should copy:

- prioritize terrain conformity;
- lower the rider rather than merely making the wheel taller;
- make ride shaping part of the product;
- let a large pneumatic element absorb terrain before hard structure does.

What X1 should not copy:

- dependence on active balancing for basic static stability;
- a single traction/braking contact patch;
- the single-wheel failure geometry for dog-accompanied riding.

## Handling program

Rev-C handling development should proceed in five layers.

### Layer 0: unpowered rider-scale templates

Before buying the chassis, make full-scale deck envelopes for:

- Comp 95 class: 950 x 251 mm max envelope;
- Pro Warren III class: 980 x 244 mm max envelope;
- Agent class: 1020 x 284 mm max envelope.

These are not deck-shape CAD. They are stance/leverage proxies.

Evaluate:

- comfortable stance width;
- natural front/rear foot yaw;
- heel/toe leverage;
- emergency step-off;
- whether the 284 mm Agent envelope feels needlessly wide;
- whether the Warren's 244 mm envelope improves useful edge leverage without feeling cramped;
- whether a narrower effective foot platform should be created even if a wider structural deck is selected.

### Layer 1: rolling chassis

Tune only mechanical variables:

- tire pressure;
- Matrix shock-block position/hardness;
- kingpin state;
- foot position/yaw/cant;
- local toe/heel ramp compliance.

Record a handling matrix rather than choosing one setup by feel after one ride.

### Layer 2: inert range-pack mass

Before power, add the exact candidate battery mass/CG with an inert surrogate.

Repeat:

- static wheel loads;
- low-speed push/coast carve;
- emergency step-off;
- tight turn;
- rough-ground clearance;
- carry/lift test.

If the range pack destroys the board's playful handling, the correct answer may be a smaller installed pack plus a spare rather than a permanent 1 kWh brick.

### Layer 3: symmetric powered control

No carve assist.

Qualify:

- smooth throttle;
- low jerk;
- reliable braking transitions;
- wheel-speed estimation;
- slip detection;
- thermal behavior.

### Layer 4: traction and carve assistance

Only after the symmetric controller is trustworthy.

Initial carve assist must:

- remain small;
- never be necessary to keep the board upright;
- revert to symmetric torque on any sensor fault;
- be disabled in Shasta mode at first;
- be qualified at walking/jogging speed before any faster test.

## Ride modes

### Powder

Goal: flowing carve response.

- soft initial throttle;
- low jerk;
- progressive torque build;
- conservative wheel-slip limiting;
- optional qualified carve bias.

### Trail

Goal: precise technical riding.

- more immediate low-speed torque than Powder;
- bounded slip allowance;
- stronger thermal awareness;
- predictable brake blending.

### Range

Goal: maximize useful distance, not merely cap speed.

- gentle acceleration;
- reduced current peaks;
- efficiency-biased torque request;
- adaptive Wh/mi estimator;
- reserve-based turn-around warning.

### Shasta

Goal: predictable companion-speed transport.

Initial behavior:

- <= 2.7 m/s (~6 mph) software cap;
- exceptionally low acceleration jerk;
- symmetric drive torque;
- carve assist disabled initially;
- no aggressive regenerative transition;
- lighting automatically enabled when fitted;
- clear remote deadman/release behavior.

The dog's leash must remain controlled by the rider, never attached to the board.

## Range model

Published commercial range is too dependent on rider mass, speed, tire pressure, surface and elevation to use as an X1 promise.

Rev-C instead uses an explicit planning envelope:

- mixed efficient surface: 22-30 Wh/mi;
- trail: 32-45 Wh/mi;
- keep a 20% planning reserve.

The model in `simulation/range_envelope.py` converts pack capacity and measured Wh/mi into conservative trip envelopes.

The point of the model is not to make today's estimate look precise. It is to replace assumptions with X1 telemetry after the first qualified rides.

## Durability architecture

Trail impacts should encounter cheap replaceable material before expensive systems.

Preferred impact hierarchy:

```
terrain
  -> tire
  -> sacrificial wheel/drive guard
  -> replaceable skid
  -> non-energy structural enclosure layer
  -> battery / motor / controller
```

Required features before powered trail use:

- no motor, gearbox or battery shell as the lowest exposed hard point;
- replaceable skid/guard pieces;
- positive drive-mount anti-rotation;
- witness marks on critical fasteners;
- strain relief before every vulnerable connector;
- abrasion sleeves in debris zones;
- drainage paths that do not route water toward connectors;
- wheel/tube service without opening the traction enclosure.

## Rev-C purchase decision

### Still orderable now

Only the inexpensive Issue #4 fit-pilot stack remains intentionally orderable.

That work cannot become obsolete if the chassis changes because rider-fit evidence is architecture-independent.

### Explicit hold

Do not yet buy:

- Comp 95 donor;
- V5 brake;
- Agent Air/Explorer chassis;
- Explorer wheel conversion;
- 9-inch wheel conversion;
- 70 mm axle conversion;
- G1 drive;
- motors;
- ESC;
- traction battery.

### Release conditions

The chassis/brake purchasing hold can close when all of the following are true:

1. rider-scale Comp 95 vs Pro Warren III vs Agent deck-envelope comparison is complete;
2. selected chassis/wheel family has a credible independent friction-or-hydraulic stopping path;
3. one drive/brake topology has a physical measurement plan without an unqualified safety-critical adapter;
4. the range-pack inert envelope can be placed without violating ground-clearance, steering, deck-flex or rider-interface keep-outs.

At that point the repository should deliberately select one chassis family and rewrite the ordering guide. It should not quietly fall back to the old Comp 95 assumption.

## Current working hypothesis

Rev-C now treats the **Comp 95 and Pro Warren III as the two strongest compact Matrix/RSII hypotheses** pending the three-way physical stance test. The Comp minimizes known mass and cost; the Warren offers the narrowest envelope, snowboard-composite construction, and adjustable wheelbase. The Agent remains the electric-native/wide-deck reference. Rear V5 braking remains attractive when it packages cleanly, while vendor-engineered front hydraulic braking remains a live alternative when it materially improves rear-drive traction and packaging.

The most promising product architecture to prove is:

> compact rider-scaled pneumatic chassis + high-air-volume tire option + independent friction/hydraulic stopping + 2WD topology selected by physical packaging and traction evidence + modular 500-650 / 950-1150 Wh energy classes + bounded traction/ride shaping.

That is the shortest path to a board that feels closer to a snowboard without becoming a 50-60 lb electric buggy.
