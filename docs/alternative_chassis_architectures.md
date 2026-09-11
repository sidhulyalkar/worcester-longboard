# Worcester X1 alternative chassis architecture review

This note exists so X1 does not repeatedly reopen “should we use a completely different chassis?” every time a new high-end board appears.

It is a **decision record**, not a permanent ban. A rejected family can be reopened only when a named physical failure in the donor architecture gives us a reason to pay its complexity cost.

## Current decision

Use the MBS Comp 95 / Matrix III donor family as the first X1 chassis.

Do not begin X1 with independent suspension, four-wheel drive, hub motors, a custom truck, or a custom deck/truck suspension linkage.

The first board should minimize simultaneous novel mechanical interfaces. Personalization belongs in the rider interface, not in an unproven suspension system.

## Architecture A: conventional channel/spring truck + pneumatics

Representative families:

- MBS Matrix III / Comp / Agent
- TRAMPA mountainboards
- high-performance precision truck variants such as Lacroix Hypertruck

### Strengths

- comparatively low part count;
- low mass;
- easy wheel/tube access;
- tunable steering through shockblocks/bushings/kingpin settings;
- huge mountainboard service history;
- 8-inch pneumatic tires already absorb a large amount of trail texture;
- simple relationship between deck, truck and wheel geometry;
- donor-first approach lets X1 start from a complete production board rather than a pile of interfaces.

### Weaknesses

- no independent vertical wheel travel;
- wheel contact over very rough terrain depends on tire compliance, deck/truck compliance and rider technique;
- high-speed stability can be sensitive to steering resistance and rider input;
- drive/brake packaging happens close to the wheel and axle.

### X1 decision

**SELECTED FOR FIRST PHYSICAL ARCHITECTURE.**

This family only loses its preferred status if measured donor testing shows an unacceptable problem that cannot be solved with tire pressure, steering resistance, deck/interface tuning, wheel choice or a local guard/drive change.

## Architecture B: independent suspension

Representative families:

- BajaBoard G4/G4X/Pantera family
- Propel Endeavor family

BajaBoard describes a buggy-like chassis with independent suspension and up to roughly 60 mm travel rather than skate trucks. Propel uses its own independent suspension system and still commonly pairs it with 8-inch pneumatics.

### Strengths

- improved wheel contact over highly irregular ground;
- suspension can isolate the deck/rider from wheel impacts;
- geometry can preserve motor mass as sprung mass;
- very high rough-terrain stability is possible;
- suspension travel, spring preload and damping become explicit tuning variables.

### Costs

- far more pivots, bearings/bushings, fasteners and fatigue interfaces;
- substantially more mass;
- more difficult alignment and inspection;
- more opportunities for play/backlash to accumulate;
- more complicated guards, steering and enclosure interfaces;
- higher purchase/fabrication cost;
- harder to distinguish a bad setup from a bad component during early prototyping.

Current reference scale illustrates the cost: BajaBoard lists roughly 20 kg for G4 and 25 kg for G4X, while its DIY G4/G4X mechanical chassis is around $1,880 before user electronics. Propel's Endeavor independent-suspension variants are roughly 22-24 kg depending on drive.

### X1 decision

**REJECTED FOR V1 UNLESS PHYSICAL EVIDENCE REOPENS IT.**

Reopen only if the qualified Comp 95 donor demonstrates a repeatable terrain-control deficiency that is not acceptably improved by:

1. stock 8-inch pneumatic pressure optimization;
2. Matrix III shockblock position/hardness and kingpin tuning;
3. rider-interface control improvements;
4. measured wheel upgrade;
5. speed/mission-envelope adjustment.

If all five fail for the intended trail mission, then independent suspension becomes an evidence-driven redesign rather than technology tourism.

## Architecture C: custom precision conventional truck

Representative family:

- Lacroix Hypertruck-style architecture

The useful lesson is not the exact Hypertruck. It is that a conventional board can push stability and drivetrain precision through local engineering: precision CNC structure, multiple bearing support, dedicated motor mounts, pulley centering bearings, and carefully tunable bushings.

### Strengths

- adds precision where needed without creating full suspension;
- can improve drive alignment and retention;
- can improve steering consistency;
- lower joint count than independent suspension.

### Costs

- expensive custom hardware;
- creates a new structural truck authority instead of inheriting the donor's;
- can lock X1 to proprietary pulleys/mounts/bearings;
- does not by itself solve the friction-brake requirement.

### X1 decision

**REFERENCE FOR LOCAL DESIGN PRINCIPLES, NOT A V1 CHASSIS CHANGE.**

Borrow bearing support, positive retention and steering-tuning concepts where useful. Do not replace Matrix III until a specific measured deficiency justifies that scope.

## Architecture D: hub motors

### Strengths

- fewer external drivetrain parts;
- no exposed belts/gears;
- compact packaging.

### Weaknesses for X1

- increases unsprung wheel mass;
- wheel/motor takes direct trail impacts;
- tire/hub options become tightly coupled to motor architecture;
- heat rejection and serviceability become wheel problems;
- independent friction-brake packaging can become harder;
- low-speed off-road torque may require a motor architecture that increases wheel mass further.

BajaBoard explicitly cites unsprung motor mass and off-road torque as reasons it avoids hub motors in its G4 family.

### X1 decision

**REJECTED FOR CURRENT TRAIL-FIRST ARCHITECTURE.**

## Architecture E: four-wheel drive

### Strengths

- much higher available traction;
- redundancy in drive torque;
- stronger acceleration/climb potential.

### Costs

- twice the motors/drive interfaces for a 2WD comparison;
- additional unsprung/sprung mass depending on topology;
- front-drive torque interacts with steering;
- more ESC channels, wiring, guards and thermal paths;
- complicates independent friction braking and service.

### X1 decision

**NOT A DEFAULT.**

A future 4WD study requires measured evidence that rear 2WD cannot meet low-speed grade/traction requirements at acceptable tire loading. Peak acceleration alone is not justification.

## Architecture F: rear 2WD sealed gear drive

Representative families:

- MBS G1/Agent
- Ownboard Prometheus/LinnPower
- Lacroix Falcon
- modern BajaBoard Helix family

### Strengths

- debris protection;
- stable ratio;
- no exposed belt tension to set repeatedly;
- compact high-torque off-road packaging;
- guards/skids can be designed as sacrificial service items.

### Weaknesses

- axial packaging near wheel/hub is demanding;
- wheel couplers and gearbox mounts become safety-critical torque paths;
- backlash/alignment still require physical assembly evidence;
- heavier and costlier than simple belt architecture;
- X1's independent friction brake competes for some of the same rear-wheel volume.

### X1 decision

**PREFERRED DRIVE REFERENCE, NOT YET SELECTED.**

Issue #19 decides whether a sealed rear drive can coexist with the required friction brake without unsafe spacers/adapters.

## Architecture G: rear 2WD belt drive

Representative families:

- TRAMPA open belt
- Propel Endeavor belt variants
- many DIY Matrix builds

### Strengths

- light;
- inexpensive;
- easy ratio changes;
- easy inspection and replacement;
- mount geometry may offer more freedom than a sealed gearbox.

### Weaknesses

- tension/alignment state matters;
- debris can damage or derail belts;
- motor mounts can creep;
- belts are consumables;
- guards/idlers add their own interference paths.

### X1 decision

**LIVE FALLBACK TO SEALED GEAR DRIVE.**

If a belt topology is the only clean way to preserve the qualified friction brake and it passes debris/retention/guard tests, simpler can beat prettier.

## Architecture H: chain drive

### Strengths

- positive torque transfer;
- tolerant of some contamination;
- ratios easy to change with sprockets.

### Weaknesses

- lubrication/maintenance;
- noise;
- exposed pinch points;
- tension management;
- sprocket/chain guard volume;
- possible derailment/jam modes.

### X1 decision

**RESERVE FALLBACK ONLY.**

It does not currently solve a problem better than gear or belt references.

## Reopen criteria

A rejected architecture may be reopened only with a short issue that names:

- the physical X1 failure or unmet requirement;
- which current mitigation paths were tested;
- the quantitative improvement the alternate architecture is expected to deliver;
- its added mass, cost, joint count and maintenance burden;
- what existing authority would be invalidated by the redesign.

That rule keeps X1 from becoming an endless parade of impressive mechanisms. The goal is not to use the most mechanisms. The goal is to use the **fewest mechanisms that reliably satisfy the trail mission**.
