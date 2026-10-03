# Worcester X1 Rev-C trail armor and sacrificial skid architecture

**Status:** inert geometry/service program.  
**Impact-energy authority:** none.  
**Powered-operation authority:** none.

Trail armor exists to make the cheap part lose the argument with the rock.

The goal is not an indestructible belly pan. An armor part that cannot deform, wear, or be replaced can simply move the impact into a gearbox housing, battery enclosure, deck insert, or truck mount.

## 1. Impact hierarchy

Rev-C uses this intended order:

```text
terrain
  -> tire where possible
  -> replaceable wear shoe / skid
  -> carrier or vendor guard structure
  -> qualified structural mount
  -> protected drivetrain / inert enclosure / electronics
```

The protected expensive component should not be the first exposed hard point in its armor zone.

## 2. Commercial reference lesson

The dated reference snapshot is:

`hardware/rev_c_trail_armor_snapshot_2026-10-01.json`

The current MBS G1 gear-drive reference is useful because its sealed aluminum gearbox uses replaceable aluminum skid plates on the vulnerable underside, and the skid plates are sold separately as service parts.

That validates a **service philosophy**, not the X1 geometry.

Propel likewise sells replaceable belt/hub guard parts in its off-road ecosystem.

X1 should steal the replaceability lesson rather than copying dimensions or attachment details blindly.

## 3. Three separate mechanical objects

### Wear shoe

The terrain-facing consumable.

It should be:

- replaceable independently;
- visually inspectable;
- retained without using exposed fastener heads as the intended wear surface;
- shaped so damage cannot enter wheel, brake, or steering sweep.

Material and thickness remain TBD.

### Carrier or vendor guard structure

The wear shoe must locate against something.

Depending on the final topology, this may be:

- a dedicated X1 carrier;
- a qualified vendor gearbox guard structure;
- another measured structural interface.

Its job is to route residual impact into a known load path without becoming a hook, mud scoop, or service obstruction.

### Structural mount

The final residual load reaches qualified chassis structure.

Requirements:

- retention can be inspected;
- witness or equivalent migration evidence exists;
- adhesive alone is not the structural load path;
- no unqualified safety-critical spacer or adapter is introduced.

The battery shell and electrical connector are not structural armor mounts.

## 4. Armor versus clearance

Protection below a component costs ground clearance.

Use:

```bash
python simulation/rev_c_skid_geometry.py \
  --wheelbase-mm 940 \
  --skid-x-mm 470 \
  --component-clearance-mm 100 \
  --skid-drop-mm 10
```

The output reports:

- skid ground clearance;
- rigid 2D component breakover angle;
- rigid 2D skid breakover angle;
- breakover-angle loss;
- fraction of component clearance consumed by the skid.

Those numbers are geometry only.

The calculation intentionally ignores:

- tire compression;
- truck roll;
- steering state;
- deck flex;
- rider motion;
- dynamic pitch;
- impact deformation.

Do not use it as physical trail-clearance authority.

## 5. Placement rule

A skid should be as low as necessary to receive the intended terrain contact, not as low as possible.

For every candidate record:

- measured loaded component clearance;
- skid drop below that component;
- longitudinal location between axles;
- full steer/lean/deck-flex state;
- wheel/brake/harness keep-outs.

If two candidate shapes protect the same component, the shape that consumes less useful clearance has a real advantage.

## 6. Snag avoidance

The worst armor shape is a downward tooth.

A first-pass armor candidate must not present a forward-facing hook in the intended direction of travel.

Low-energy root/curb surrogate trials must show that the intended wear surface:

- contacts first;
- slides or deflects over the surrogate rather than hooking;
- does not cause the protected component to contact;
- does not shift into the wheel/brake/steering envelope;
- does not loosen.

This does not prove high-speed impact survivability.

It proves that the shape is not obviously self-defeating at low energy.

## 7. Debris and mud

Armor should not create a debris reservoir beside rotating hardware.

The design needs:

- drainage / escape path;
- no narrow stone trap against a pulley, gearbox, brake, or wheel;
- visual inspection access;
- cleaning access without dismantling the traction enclosure.

A beautiful closed scoop that fills with trail grit is not armor.

## 8. Battery/enclosure rule

The live battery is never the first trail-armor test mass.

Initial enclosure-zone testing uses the Issue #21 inert mass / enclosure surrogate.

The armor may protect a future enclosure, but it must not rely on the battery shell as the primary impact structure.

Battery retention and armor are separate jobs.

## 9. Serviceability

A trail wear part is useful only if it is actually treated as a wear part.

The early qualification requires that replacement:

- does not open the traction enclosure;
- does not disturb an unrelated brake-critical joint;
- preserves wheel/tube service;
- preserves drivetrain service;
- has a documented method and measured replacement time.

A skid that turns every scrape into a half-day teardown is not a good consumable.

## 9A. Wear witnesses and service intelligence

A replaceable wear shoe should make its own consumption inspectable.

For a future physical candidate, consider **geometric wear witnesses** on the sacrificial part only, such as side-face steps, shallow reference grooves, or another directly measurable feature that reveals remaining material without removing the part.

Rules:

- the witness belongs to the replaceable wear shoe, not the structural carrier;
- it must not create a forward-facing hook, debris trap, sharp edge, or crack starter in a critical load path;
- it must not expose the retention fastener as the next terrain-contact feature;
- no replacement threshold in millimetres is invented before the actual material, thickness, contact geometry and load path are selected;
- a visual witness never replaces direct inspection after a hard contact.

The useful outcome is a service record that can say:

> this exact wear shoe has consumed more material since the last inspection

without pretending that visual wear alone proves remaining impact strength.

When the physical geometry exists, record the initial witness geometry and a repeatable remaining-thickness or witness-state measurement method. A later lifecycle bridge may attach these observations to the Issue #41 vehicle-health history.

This is intentionally more useful than decorative armor. The sacrificial layer should be cheap to replace and easy to judge.

## 10. Inert qualification

Create a private session:

```bash
python tools/init_rev_c_trail_armor_session.py \
  rider/private/armor/zone-a
```

Fill:

`trail_armor_manifest.json`

Qualify:

```bash
python tools/qualify_rev_c_trail_armor.py \
  rider/private/armor/zone-a/trail_armor_manifest.json \
  --out rider/private/armor/zone-a/trail_armor_authority.json
```

The early qualifier requires:

- no live battery;
- no electrical energy;
- no powered vehicle;
- geometry/sweep checks;
- a defined load path;
- inspectable retention;
- serviceability;
- at least three low-energy surrogate contacts;
- clean post-trial inspection.

A passing report still states:

```text
impact_energy_qualified = false
live_battery_test_authorized = false
procurement_authority = false
powered_operation_authorized = false
```

## 11. Material selection is intentionally delayed

Candidate families include:

- replaceable aluminum wear plate;
- replaceable engineering-polymer wear shoe;
- vendor-supplied drivetrain skid.

Do not choose a material solely from a generic strength or friction table.

The final choice depends on:

- actual contact geometry;
- wear rate;
- expected temperature;
- carrier stiffness;
- fastener geometry;
- mass;
- noise;
- gouging versus sliding behavior;
- service availability.

Material optimization starts only after the geometry/load path exists.

## 12. Later impact-energy qualification

The current qualifier cannot answer:

> Will this survive a specific rock strike at a specific powered speed?

That later question needs:

- final vehicle mass;
- final protected subsystem;
- actual armor mass/material/thickness;
- measured loaded clearance;
- final structural mount;
- representative impact geometry;
- a defined test energy / load case;
- post-impact structural inspection criteria.

Do not invent that threshold today.

## 13. Exit condition for the current tranche

A Rev-C armor architecture is ready to advance when:

1. the protected zone and component are real;
2. the wear shoe is the intended first hard contact;
3. clearance loss is quantified;
4. full motion/sweep clearance passes;
5. the load path is explicit;
6. replacement does not disturb unrelated safety-critical hardware;
7. low-energy root/curb surrogates do not hook or loosen the assembly;
8. the protected inert component and structural mount remain undamaged.

That is enough to decide whether an armor geometry is mechanically sensible.

It is not enough to authorize powered trail impacts.
