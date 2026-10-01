# Worcester X1 Rev-C public-use and test-venue envelope

**Status:** dated design constraint review, 2026-10-01.  
**Legal authority:** none.  
**Public-road operation authority:** none.  
**Town-park operation authority:** none.

This document separates three questions that are easy to blur together:

1. What terrain should X1 be capable of riding?
2. Where may X1 be physically tested?
3. What vehicle category, if any, would allow a finished configuration to operate on public roads or bikeways?

Those are different engineering problems.

## 1. Worcester Park remains a terrain benchmark, not a test track

Worcester Park is still a useful design reference because the Town describes it as an approximately 11-acre neighborhood park with natural woodlands, three trails, and a meadow.

That terrain inspired the product mission:

- loose dirt and gravel;
- narrow trail transitions;
- low-speed carving;
- root/brush/rough-surface compliance;
- compact maneuverability rather than top-speed riding.

However, the current Town of Los Gatos Parks Rules and Regulations list **hoverboards and skateboards as not allowed** in Town parks and trails.

Therefore the project now treats Worcester Park as:

> **terrain inspiration only, not an assumed physical X1 test venue.**

Do not schedule board testing there unless the applicable rules change or the Town provides specific written authorization.

## 2. California has a narrow electrically motorized board definition

The current California Vehicle Code definition used by this project is CVC 313.5.

The category includes a wheeled standing device that:

- is not greater than 60 inches deep and 18 inches wide;
- transports one person;
- uses an electric propulsion system averaging less than 1,000 W;
- has a propulsion-only maximum speed of no more than 20 mph on a paved level surface.

The important design implication is the power-system clause.

X1's trail architecture has been exploring motors, controllers, and battery references capable of substantially more than 1 kW of electrical/mechanical output.

The repository must therefore **not assume** that a high-power trail configuration is an "electrically motorized board" under CVC 313.5.

## 3. Shasta mode does not change vehicle classification by itself

Shasta mode currently has a provisional software speed cap of 2.7 m/s.

That is useful for control behavior.

It is not treated by this project as proof that a multi-kilowatt vehicle becomes a sub-1,000-W statutory electrically motorized board.

Likewise:

- a 15 mph software cap is not classification evidence;
- an 18 A mode-current cap is not classification evidence;
- a low-power ride mode does not erase the capabilities of the installed propulsion system;
- a user-selectable profile should not be used as a substitute for a vehicle-level classification review.

If public-road compatibility remains a product goal, it may require a distinct hardware architecture.

## 4. Public-operation constraints for a qualifying electrically motorized board

For a vehicle that actually satisfies the statutory category, current California rules relevant to the design include:

### Helmet

CVC 21292 requires a properly fitted and fastened bicycle helmet when operating an electrically motorized board on a highway, bikeway, public bicycle path, sidewalk, or trail.

### Darkness equipment

CVC 21293 requires, during darkness on a highway:

- forward white lighting visible from 300 feet, with qualifying operator-mounted alternatives;
- rear red reflector/reflective material visible from 500 feet;
- white/yellow side reflectors or reflective material visible from 200 feet.

This converts the existing Shasta-mode "lights requested" output from a convenience feature into a meaningful product-interface requirement if a public-road derivative is pursued.

### Road and speed envelope

CVC 21294 currently provides:

- operation on highways posted at 35 mph or less, unless entirely within a designated Class II or Class IV bikeway;
- maximum operation speed of 15 mph on highway, bikeway, public bicycle path, sidewalk, or trail;
- a general reasonable/prudent-speed requirement considering visibility, traffic, surface, width, and safety.

These are external legal constraints, not reasons to make 15 mph the engineering target for every X1 configuration.

## 5. Two architecture paths should remain open

### Path A: X1 Trail

Mission:

- snowboarding-like loose-surface handling;
- durability;
- useful trail torque;
- private or expressly authorized off-road operation;
- no assumption that the vehicle fits a public-road micromobility category.

Advantages:

- does not cripple the trail drivetrain to satisfy a potentially incompatible public-road power definition;
- keeps off-road traction, thermal, and range design honest;
- allows the board to remain an experimental trail machine.

Constraint:

- physical testing requires private or expressly authorized terrain.

### Path B: X1 Public / Companion derivative

Mission:

- neighborhood utility;
- Shasta-mode low-speed behavior;
- pavement/bikeway use where lawful;
- lighting/reflector integration;
- vehicle-level compliance with the applicable public-use category.

This path must not be created by a software checkbox.

It should answer, with authoritative evidence:

- whether the propulsion hardware itself fits the applicable statutory power definition;
- whether the final dimensions fit;
- whether maximum design speed fits;
- where the intended routes are permitted;
- whether a dedicated lower-power motor/controller/battery configuration is needed.

A separate lower-power derivative may be better than compromising X1 Trail.

## 6. Test-venue policy

Powered testing is not authorized today.

When future powered authority exists, the preferred venue order is:

1. controlled private property with owner permission;
2. a closed test facility or course where operation is expressly permitted;
3. another controlled venue with documented jurisdictional permission.

Do not default to:

- Worcester Park;
- another Los Gatos Town park or trail;
- a public sidewalk;
- a public road;
- a bike path;

merely because the board is speed-limited.

## 7. Powered test-venue record

Every future powered ground-test session should record:

- venue ID;
- land owner or managing jurisdiction;
- permission basis;
- date permission was checked;
- course boundaries;
- surface;
- nearby pedestrians/vehicles exclusion method;
- emergency stop location;
- mechanical brake status;
- maximum planned speed;
- applicable venue restrictions;
- whether public access is physically controlled;
- responsible test observer.

A venue record is not vehicle authority.

It is evidence that the location itself is appropriate for the planned test.

## 8. Companion use adds a second permissions question

Dog-accompanied riding needs both:

1. vehicle/venue permission;
2. animal-control compliance.

Current Los Gatos information states that dogs are not allowed off leash in Town parks.

That aligns with the current project rule:

- leash stays with the rider;
- leash is never attached to the board.

But a legal leash does not make a prohibited skateboard legal in a Town park.

Vehicle permission and dog-control rules must both pass.

## 9. Current design consequences

Rev-C should now preserve all of the following:

- low-speed Shasta mode remains useful even if only on private/authorized routes;
- lights and reflective visibility remain part of the public-oriented product branch;
- high-power Trail architecture is not represented as road-legal by default;
- no public-use claim is derived from a software mode;
- Worcester Park terrain drives tire/compliance requirements, not test permission;
- route/venue research becomes part of product planning rather than a post-build surprise.

## 10. What this changes in procurement

Nothing becomes newly orderable.

This review does **not** justify:

- buying a smaller motor;
- buying a larger motor;
- buying lights;
- buying a battery;
- buying a public-road drivetrain;
- buying test-venue equipment.

It creates a new architecture decision that should be resolved before final motor/controller/battery freeze if public-road utility remains important.

## 11. Current recommendation

Preserve two design branches until the propulsion architecture is physically closer to freeze:

```text
X1 Trail
  private / expressly authorized terrain
  off-road capability first
  public-road category not assumed

X1 Public / Companion study
  lower-power public-oriented hardware if needed
  Shasta control envelope
  lighting / reflectors
  only after classification and route permission are established
```

Do not force one board to satisfy both by accident.

The useful common platform remains:

- rider-fit geometry;
- pneumatic wheels;
- Matrix-style progressive steering;
- independent mechanical stopping;
- modular energy;
- instrumentation;
- fail-conservative controls.

The propulsion system may be the part that legitimately forks.
