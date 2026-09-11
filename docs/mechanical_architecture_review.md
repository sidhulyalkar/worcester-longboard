# Worcester X1 mechanical architecture review and build plan

Status: **design-review authority for planning only**. Physical evidence still wins.

This document answers a harder question than “which parts fit?”:

> What sequence of proven mechanisms, measurements, failure-mode controls, and low-energy tests gives Worcester X1 the best chance of becoming a reliable off-road board without discovering a fundamental mechanical incompatibility after the expensive parts are purchased?

The answer is to preserve known-good mountainboard interfaces as long as possible, separate brake and drive claims until they are physically demonstrated together, and make every common trail failure observable before it becomes a rider event.

## 1. Executive architecture decision

### Keep

The preferred base remains a current-generation **MBS Comp 95 donor** because it supplies a coherent unpowered mountainboard instead of making X1 invent its own safety-critical truck, deck, hub, bearing, wheel, and binding interfaces simultaneously.

The first physical configuration is:

- Comp 95 PowerLam deck;
- Matrix III CNC 400 mm trucks;
- stock 50 mm axle configuration;
- Rockstar II hubs;
- stock T1 200x50 pneumatic tires/tubes;
- F5 bindings as removable reference hardware;
- MBS V5 mechanical brake as the first stopping-system reference;
- no traction motors, live traction battery, drivetrain, or custom structural rider-interface drilling.

### Change from earlier X1 work

The earlier generic rolling-chassis CAD used a 250 mm / 9-inch-class wheel and an 820 mm wheelbase. That was useful for envelope exploration but did not match the donor-first strategy.

The current published Comp 95/T1 reference is now the baseline:

- deck tip-to-tip: 950 mm;
- deck maximum width: 251 mm;
- axle-to-axle: 940 mm;
- T1 product class: 200x50;
- current T1 published physical tire diameter: 194 mm;
- current T1 published physical width: 51 mm;
- donor board mass reference: 6.6 kg;
- truck end-to-end reference: 400 mm.

Published dimensions remain **catalog references**, not proof of the received board.

### Do not freeze yet

The final drivetrain is intentionally unresolved.

The important conflict is real:

1. Matrix III 400 mm / 50 mm is the MBS brake-first configuration.
2. Matrix III 420 mm / 70 mm is the MBS electric/G1 configuration and is explicitly not MBS-brake compatible.
3. G1 requires 70 mm Matrix III axles.
4. MBS states that the 300 mm hanger from the 400-series can be upgraded to 70 mm axles, creating an approximately 440 mm drivetrain-capable reference.
5. The V5 manual installs its two rotors on the rear wheels.
6. Moving a wheel 20 mm outward with a longer axle can invalidate V5 rotor/pad axial alignment even if the hanger still contains brake-arm bosses.

Therefore “rear V5 + rear G1” is a **hypothesis**, not an architecture decision.

Issue #19 now prevents the power architecture from freezing until exactly one brake/drive topology is physically qualified.

## 2. What comparable builds teach us

The dated machine-readable source set lives in `hardware/mechanical_reference_benchmarks_2026-09-11.json`.

### MBS Comp 95

What it proves:

- 400 mm Matrix III CNC, 12 mm axle, Rockstar II, 8-inch T1, F5 and a 950 mm-class deck form a production mountainboard system;
- brake compatibility is part of the product family;
- an unpowered donor can establish real steering, wheel, deck and brake evidence before electrification.

What X1 should copy:

- the structural interfaces;
- wheel/bearing/hub compatibility;
- stock 8-inch development wheelset;
- truck and binding mounting strategy until better evidence exists.

What X1 should not infer:

- that donor geometry automatically supports a future drivetrain;
- that generic catalogue dimensions are precise enough for brake/drive coexistence;
- that the stock binding placement is the final rider-specific placement.

### MBS Agent

What it proves:

- Matrix III can support a serious production electric mountainboard;
- wide drive geometry, steel helical gears, replaceable skid protection, large motors and top-side battery protection are credible off-road choices;
- 8-inch tires remain viable on a high-performance production electric model.

What X1 should copy:

- protected drivetrain thinking;
- replaceable impact/skid parts;
- top-side or otherwise impact-protected battery packaging as a candidate;
- serviceable couplers and guards;
- deliberate truck-resistance tuning.

What X1 should not copy automatically:

- 18S voltage;
- 6890 motor size;
- 41 mph performance;
- battery mass/capacity;
- lack of an independent mechanical friction brake in the electric product architecture.

X1 is trail-control-first, not spec-sheet-first.

### Ownboard Prometheus

What it proves:

- MBS Matrix III + dual 6384 + gear drive + 8-inch pneumatics is a commercially used high-power packaging family;
- a roughly 20.5 kg complete board can package a 1170 Wh battery and dual gear drive.

X1 lesson:

A Matrix III donor is not a dead end for electrification. But X1 should attempt to remain materially lighter and lower-energy unless measured terrain/range requirements force otherwise.

### TRAMPA spur gear systems

What they prove:

- robust trail drives use guards, positive clamping, keyed torque paths and serviceable seals;
- final gear backlash is an **assembly-state measurement**, not a CAD constant;
- serious off-road ownership assumes routine inspection and service.

X1 lesson:

The future drivetrain qualification must include final assembled backlash/tension/alignment, guard clearance and service inspection. A CAD model of nominal gears is insufficient.

### TRAMPA open belt systems

What they prove:

- belts remain attractive because they are simple, light, ratio-flexible and easy to service;
- a trail belt architecture also assumes spare belts, debris exposure and tension maintenance.

X1 lesson:

Do not dismiss belt drive merely because sealed gears look cleaner. If belt packaging uniquely preserves a qualified mechanical brake, it deserves a topology candidate. But belt debris/tension/idler failure modes must be paid for explicitly.

### TRAMPA front hydraulic brake board

This is the most strategically useful counterexample.

TRAMPA currently sells a dedicated mountainboard using front-mounted Magura HS11 hydraulic friction brakes and explicitly cites forward load transfer as the reason for front braking.

X1 lesson:

Front friction braking is mechanically credible **when the truck/hanger/brake system is designed for it**. This does not mean X1 should fabricate an ad-hoc Matrix III front-brake adapter. It means Issue #19 should not assume rear braking is the only possible final topology.

### DIY electric-mountainboard community

The useful lesson is not any one parts list. It is the repetition of mundane failures:

- wheel-retention hardware loosens;
- motor mounts creep or bend;
- pulleys/gears slip;
- belts lose tension or ingest debris;
- bearings fail;
- enclosures loosen or crack;
- cables and connectors become load-bearing by accident;
- water and dirt find unprotected paths;
- a successful drivetrain can still be undermined by a bad battery-box mount.

X1 should therefore optimize for **inspection and graceful degradation**, not merely high nominal strength.

## 3. Current X1 work: what is strong

Several decisions already survive this critique well.

### Donor-first procurement

This is stronger after the benchmark review, not weaker. Production boards repeatedly rely on coherent truck/hub/wheel/deck systems. Buying a complete known family avoids inventing structural compatibility from retail fragments.

### Stock 8-inch wheels first

Also stronger. MBS Agent Air, Ownboard Prometheus, Comp 95 and many DIY Matrix builds use 8-inch pneumatic wheels. Nine-inch wheels are not necessary to prove the architecture and introduce hub/brake/drive changes.

### One-zone fit evidence before four-zone duplication

This remains exactly right. The rider interface should be a measured layer added to a mechanically coherent board, not a reason to redesign truck geometry before the sensor stack even qualifies.

### Mechanical braking before power

Still right. The critique is not “remove the brake.” It is “stop pretending the final brake and final drive necessarily occupy compatible geometry.”

### Fail-closed power procurement

This is one of the most valuable repo mechanisms. Issue #19 now makes it harder for later enthusiasm to erase today’s mechanical uncertainty.

## 4. Current X1 work: what needed correction

### Problem A: donor-first prose, nine-inch CAD

Fixed in this tranche. The brake-first CAD now uses the published Comp 95/T1 geometry.

### Problem B: wheel center incorrectly placed at axle tip

The previous reference placed wheel centers at half total truck width. For a 300 mm hanger + two 50 mm axle extensions, that treats the center of the wheel as the outer end of the axle.

The reference now places the wheel center approximately halfway along each axle extension until the physical hub stack is measured:

`wheel_center_y = hanger/2 + axle_extension/2`

For the 300/50 reference that is 175 mm from centerline. With a 51 mm tire width, the estimated outer wheel envelope is about 401 mm.

This is still a packaging model. Received bearing/hub/spacer geometry replaces the approximation.

### Problem C: brake and drive branch could be mentally recombined

Fixed structurally. The CAD now exposes three separate references:

- `brake_first_400mm`: 300 mm hanger + 50 mm axles, brake reference true, G1 drive false;
- `drive_clearance_420mm`: 280 mm hanger + 70 mm axles, drive reference true, MBS brake false;
- `brake_hanger_70mm_topology_study`: 300 mm hanger + 70 mm axles, approximately 440 mm end-to-end, drive reference true, **brake alignment unknown and deliberately not marked compatible**.

### Problem D: power gate had no dedicated topology authority

Fixed. `power_architecture_frozen` now requires a fingerprinted `x1_brake_drive_topology` report from Issue #19.

## 5. Brake/drive topology decision tree

There are four candidates worth taking seriously.

### Candidate A: rear V5 + rear drive on the same truck

Why we want it:

- conventional rear traction drive;
- preserves documented rear V5 placement;
- one rear assembly carries propulsion and friction braking;
- front truck remains mechanically simple.

Why it may fail:

- G1 requires axial space and 70 mm axles;
- V5 rotor/pads were defined around the brake-first wheel position;
- gear coupler, brake rotor, brake arm and guard may compete for the same inner-wheel volume;
- moving brakes outward with custom spacers changes brake-arm bending loads and is not automatically acceptable.

Test priority: **first topology to investigate physically**, because success gives the cleanest conventional layout.

Rule: if it requires an improvised safety-critical brake-arm extender/spacer whose structural behavior is not independently qualified, reject it rather than rationalizing it.

### Candidate B: rear V5 + front 2WD

Why it is attractive:

- preserves V5 exactly where its manual expects it;
- separates drive and brake axial packaging completely.

Why it is not preferred:

- acceleration transfers normal force rearward, reducing available front-drive traction;
- loose uphill terrain magnifies the problem;
- torque disturbances act through the steering truck;
- front drive changes handling at precisely the terrain moments where traction matters most.

This remains a fallback candidate, not the default.

### Candidate C: rear 2WD + front friction brake

Why it is attractive:

- conventional rear propulsion;
- braking load transfer favors front friction braking;
- production mountainboard precedent exists.

Why it is difficult:

- MBS V5 is documented as a rear system;
- TRAMPA’s successful front hydraulic architecture uses a dedicated brake hanger/truck family;
- mixing unrelated front/rear truck kinematics can create steering imbalance;
- designing our own brake adaptor would create a new safety-critical structural component.

Rule: prefer a commercially proven complete front brake/truck architecture over an improvised adaptor. If no coherent compatible system exists, do not force this topology.

### Candidate D: alternate rear drive that preserves brake-first geometry

Possibilities include belt or chain architectures whose wheel coupling occupies different volume from G1.

Why it is attractive:

- may preserve conventional rear drive and documented rear braking;
- may cost less and be easier to repair.

Why it may fail:

- wheel pulley/sprocket may still collide with rotor space;
- belt/chain adds debris/tension/guard failure modes;
- mounts can creep under repeated torque;
- exposed systems are more vulnerable off-road.

Rule: alternate drive wins only if total system risk is lower, not merely because its first CAD screenshot looks compatible.

## 6. Mechanical risk register priorities

The complete machine-readable register is `hardware/mechanical_risk_register.json`.

The highest-priority unresolved risks are:

### Battery/enclosure mount

This earns the highest current risk score because a trail enclosure is not luggage. It is a repeated-shock structural load path around a high-energy object.

Control strategy:

- no live pack during initial mechanical enclosure qualification;
- use a dummy mass matching final pack mass and center of mass;
- positive retention independent of adhesive;
- load spreading into known deck structure;
- impact/skid shielding;
- service removal without disturbing truck structure;
- inspection for insert pull-through, cracked enclosure, fretting and fastener migration.

### Brake/drive packaging

This is the architecture risk that can strand the most expensive purchases.

Control strategy:

- measure V5 first;
- generate actual rotor/pad/arm/cable envelope;
- introduce candidate drive envelope only after brake geometry exists;
- no power purchase before topology authority.

### Drive mount retention

Community failures make this boring but critical.

Control strategy:

- no friction-clamp-only assumption without a vendor-proven clamp/load path;
- witness marks;
- static torque-reaction fixture;
- sacrificial guards below drive;
- post-test mount-angle measurement.

### Brake fade

A brake that stops once on a cool driveway is not a downhill brake qualification.

Control strategy:

- cold static/rolling qualification first;
- later repeated-stop thermal characterization before powered hills;
- record rotor/pad temperature and stopping-distance change;
- regen remains supplemental heat relief, never the sole stopping path.

### Structural/retention fasteners

Control strategy:

- define locking method per joint;
- do not apply threadlocker indiscriminately;
- use manufacturer torque where published;
- witness-mark critical joints;
- any moved witness mark triggers investigation rather than routine re-tightening and forgetting.

## 7. Optimal complete build sequence

The project should be built in **evidence order**, not final-assembly order.

### Phase 0: paper/digital authority

Do now:

- keep benchmark source registry current;
- keep mechanical risk register machine-readable;
- generate all three chassis reference branches;
- maintain power hard-block;
- run CI validators.

Exit:

- no source-of-truth conflict;
- no powered item orderable;
- donor geometry reflects the actual selected donor family.

### Phase 1: one-zone fit sensor

Build only the Issue #4 bench fixture.

Exit criteria already defined by Issue #4 include calibration linearity, hysteresis, validation accuracy, noise and mechanical stop clearances.

Why this stays first:

It is cheap, gives useful rider-interface information, and does not commit the vehicle architecture.

### Phase 2: acquire and receive the donor

Normal path:

- Comp 95 donor;
- stock 8-inch wheels;
- no 9-inch conversion;
- no axle conversion;
- no drivetrain.

Incoming inspection:

1. assign IDs to deck, both trucks, four hubs/wheels, bindings and all structural fastener groups;
2. measure wheel/tire physical diameter and width at recorded pressure;
3. measure axle-to-axle and truck end-to-end;
4. inspect deck faces, edges, inserts and truck mount zones;
5. inspect axle straightness/runout qualitatively and quantitatively where practical;
6. verify bearing play/free-spin;
7. inspect hub screws, tire/tube condition and wheel spacer stack;
8. photograph and record exact Matrix III revision.

Do not modify anything before the baseline measurements are captured.

### Phase 3: stock unpowered rolling-baseline test

Purpose: prove the donor itself before adding our own variables.

Tests:

- wheel free-spin and axial play;
- static steering effort left/right;
- return-to-center;
- full lean/steer interference check;
- walking push/coast;
- jogging push/coast in a controlled area;
- low obstacle/rough-surface push test;
- post-test wheel, truck, deck and fastener inspection.

Pass means the donor is a known mechanical baseline.

### Phase 4: V5 brake interface and stopping test

Install V5 according to received revision/manual.

Measure:

- rotor OD/ID/thickness/bolt circle;
- hub spacer stack;
- rotor axial location relative to hanger/axle datum;
- brake-arm pivot and spring-pin geometry;
- released/applied arm envelope;
- pad alignment range;
- cable path and minimum bend radius;
- actual inflated wheel geometry.

Test:

- released free-spin;
- pad rebound symmetry;
- full application interference;
- cable sweep;
- static wheel brake torque;
- controlled unpowered stops;
- post-test hardware/cable/pad inspection.

Exit: Issue #14 authority only.

### Phase 5: unpowered chassis authority

Now close Issue #12 using the **actual donor + actual V5**.

Required additions beyond Phase 4:

- full steering sweep with brake installed;
- real static ground clearance;
- minimum clearance under a conservative static compression/load case;
- rider-interface keepout preserved;
- repeat rough-surface push/coast;
- critical fastener witness marks;
- wheel/tube service without disturbing unrelated systems;
- mass measurement.

Exit: fingerprinted rolling-chassis authority.

### Phase 6: brake/drive topology fixture, Issue #19

Do **not** install a traction battery.

The safest strategy is to use inert/reference hardware and geometry wherever possible.

Test Candidate A first:

1. record stock 50 mm V5 axial datums;
2. model the 300 mm hanger + 70 mm axle state;
3. if justified, obtain only the minimum 70 mm axle/reference-drive interface needed for measurement;
4. measure where the wheel, rotor, brake pad, gear coupler and guard would sit;
5. fail immediately on axial conflict, arm interference, unsafe spacer requirement, cable conflict or impossible wheel service;
6. if geometrically viable, perform static service/clearance tests before any torque test.

If A fails, compare B/C/D explicitly rather than “temporarily” buying a preferred drive anyway.

Exit: exactly one passing topology, all others explicitly rejected with reasons.

### Phase 7: four-zone rider fit and Rev-B interface

This can proceed in parallel once Issue #4 opens duplication.

Important mechanical rule:

Rider-interface customization may change foot placement, pads and adapter geometry. It should **not silently change front/rear truck geometry** to compensate for rider fit.

Before drilling:

- produce full-scale left/right template;
- verify binding/pad clearances at full steering;
- verify emergency step-off/release behavior unpowered;
- preserve access to structural truck fasteners and future enclosure service.

### Phase 8: power-architecture freeze on paper and bench

Only after rolling chassis, brake-drive topology and Rev-B template are qualified.

Select as one coupled system:

- drive type;
- ratio;
- wheel size;
- motor size/KV/shaft interface;
- voltage;
- ESC voltage/current/thermal headroom;
- battery capacity/current/physical envelope;
- BMS/charger;
- fuse/service disconnect/precharge;
- remote/failsafe architecture;
- enclosure and harness connectors.

Do not independently optimize those rows.

### Phase 9: drivetrain low-energy mechanical commissioning

Before traction battery installation:

- assemble drive mechanically;
- hand-rotate every wheel through full revolution;
- verify backlash/tension/alignment;
- verify wheel removal;
- verify guard/skid clearance;
- perform static mount torque-reaction test;
- run motors from a current-limited low-energy bench source if the future electrical authority permits;
- inspect bearing/mount temperature and witness marks.

### Phase 10: dummy-mass enclosure qualification

Use an inert mass matching intended pack mass/CG.

Tests:

- static load;
- tilt/inversion retention;
- deck flex/steer clearance;
- rough-surface unpowered test;
- service removal;
- fastener/insert/enclosure inspection.

Only then fabricate/order the final pack around the qualified envelope.

### Phase 11: traction system assembly

The first high-current battery remains professionally assembled.

Mechanical checks include:

- connector strain relief;
- cable abrasion and steering service loops;
- enclosure seal strategy without trapping unsafe heat;
- no cable acting as battery retention;
- fuse/disconnect physically accessible;
- charger port protected from wheel/ground/impact paths.

This phase still does not imply riding.

### Phase 12: future powered commissioning

A separate future authority contract is required.

Expected progression:

- wheels off ground;
- low current;
- low wheel speed;
- unloaded drivetrain thermal/retention observation;
- very low-speed flat rolling;
- braking/failsafe checks;
- incremental speed/load;
- repeated mechanical inspections between stages;
- no hill testing until repeated-stop thermal brake evidence exists.

## 8. Quantitative acceptance philosophy

X1 should avoid fake precision where the component has not been measured.

Three classes of number must remain visibly different:

### Published reference

Example: T1 published diameter 194 mm.

Useful for CAD and purchasing, but not a received-part measurement.

### Measured X1 hardware

Example: actual inflated tire diameter at recorded pressure.

This controls final interference and torque calculations.

### Qualification threshold

Example: maximum allowed witness-mark movement = none detectable by the defined inspection method.

This is a design decision that should be justified by consequence and measurement capability.

Never turn a published reference into a “measured” field merely to satisfy a gate.

## 9. Fastener and retention philosophy

There is no universal X1 instruction to “Loctite everything.”

For each critical joint record:

- fastener ID and grade/material where known;
- joint function;
- manufacturer torque if published;
- dry/lubricated/threadlocker state if relevant;
- locking mechanism: prevailing nut, lock nut, threadlocker, keyed interface, clamp, cotter/clip, etc.;
- witness mark;
- inspection interval.

Any witness-mark movement after qualification testing is a **failed retention event** until the cause is understood.

## 10. Guard and skid philosophy

The most vulnerable expensive component should not be the first thing that meets a rock.

Future drive/enclosure geometry should intentionally create a hierarchy:

1. tire;
2. cheap/replaceable skid or guard;
3. structural mount;
4. gearbox/motor/enclosure.

A guard that is stronger than the mount behind it can simply transfer impact into a more expensive failure. Guard interfaces must therefore be inspectable and replaceable.

## 11. Brake philosophy after this review

The independent friction brake remains a core X1 requirement, but with two refinements:

1. The V5 is the **measurement reference**, not automatically the final powered-board brake.
2. A single cold unpowered stop is not sufficient evidence for powered descents.

The final system should have:

- friction braking on at least two wheels;
- mechanical/hydraulic stopping independent of traction power state;
- regenerative braking as supplemental control/heat sharing only;
- an understood rider backup stopping/step-off plan appropriate to the final binding configuration;
- repeated-stop thermal evidence before sustained descents.

## 12. Binding and rider-interface philosophy

Bindings improve off-road control but also couple the rider more strongly to the board.

X1 therefore treats binding position as a rider-interface problem, not a generic mountainboard constant.

The final Rev-B process must verify:

- no painful pressure concentration in normal stance;
- sufficient retention for trail control;
- deliberate emergency release/step-off behavior;
- no interference with steering, brake cable, enclosure or service access;
- no structural drilling based on shoe-size labels or visual guesses.

## 13. What we can develop now while waiting for hardware

There is still useful software/CAD work to do without pretending it replaces metal:

- generate donor-grounded 400/420/440 reference CAD;
- build the Issue #19 topology-report initializer/example manifest;
- add a received-donor measurement manifest and qualifier;
- create a fastener/retention inspection manifest;
- create a four-corner static load and dummy-pack experiment plan;
- define repeated-stop thermal logging format;
- model front-drive traction as a rejection/acceptance tool for Candidate B;
- model brake/drive axial stack parametrically once V5 measurements arrive;
- create serviceability checklists for wheel/tube/brake/guard removal.

Do not spend this time picking an exact battery or motor KV. Those are downstream of the mechanical topology.

## 14. The shortest path to a reliable X1

The shortest reliable path is not the path with the fewest tests. It is the path with the fewest simultaneously novel interfaces.

That path is:

`one-zone sensor -> stock donor -> stock donor rolling baseline -> V5 brake -> measured unpowered chassis -> brake/drive topology -> rider-specific Rev-B -> coupled power architecture -> inert enclosure/drivetrain tests -> traction system -> incremental powered commissioning`

At every arrow, preserve the previous known-good configuration so a new failure can be attributed to the change that introduced it.

That is how X1 avoids becoming a pile of individually excellent components whose interfaces were never excellent together.
