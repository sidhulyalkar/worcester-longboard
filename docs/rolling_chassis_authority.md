# Worcester X1 unpowered rolling-chassis authority

Issue #12 advances vehicle-core geometry without waiting for final rider-interface CAD and without introducing traction-battery or motor torque.

## Two reference lanes

The current envelope intentionally keeps two vendor-reference candidates alive:

| Lane | Reference truck | Width | Brake reference | Drive-clearance reference | Purpose |
|---|---|---:|---|---|---|
| Brake-first | MBS Matrix III CNC 400 mm | 400 mm | yes | no | Preserve a straightforward mechanical-brake path |
| Drive-clearance | MBS Matrix III CNC 420 mm | 420 mm | no | yes | Reserve space for larger e-mountainboard drivetrain packaging |

The vendor currently describes the 400 mm CNC truck as brake compatible and the 420 mm e-mountainboard truck as not compatible with MBS brake systems. X1 therefore treats this as a packaging decision that must be resolved rather than a cosmetic width choice.

## Current wheel reference

The first packaging model uses a 250 x 50 mm / nominal 9-inch pneumatic tire envelope on a 12 mm axle. This is a collision-analysis reference, not a final tire commitment.

## Rider-interface boundary

The center 650 x 245 mm top-deck region is protected from chassis-specific permanent interfaces. Rev-B fit work owns final left/right foot-interface geometry. Chassis packaging may route around this region but may not consume it merely for convenience.

## Clearance gates

The reference model starts with:

- 65 mm static underbody clearance
- 20 mm vertical motion allowance
- 45 mm minimum compressed clearance
- 12 mm wheel-to-deck packaging allowance
- 25 mm radial allowance outside the wheel for future drivetrain guards

These are design screening numbers. Physical suspension geometry and real component drawings must replace envelope assumptions before fabrication authority opens.

## Brake boundary

X1 requires an independent mechanical braking path before powered hill testing. The 160 mm rotor in the current model is a packaging reference only. Rotor diameter, carrier, caliper, actuation, hose/cable routing and static brake torque all remain separate verification gates.

Regenerative braking is supplemental. It is not the sole stopping authority.

## Generated references

Run:

```bash
PYTHONPATH=. python cad/generate_rolling_chassis.py
```

The generator emits neutral and maximum-steering sweep STEP/STL files for both the 400 mm brake-first and 420 mm drive-clearance references, plus machine-readable authority JSON.

The sweep output is deliberately bulky. It is a keep-out/interference model, not a finished aesthetic surface.

## Fabrication gate

A rolling-chassis authority may only become fabrication-ready after all of the following are true:

1. selected wheel/hub/tire envelope is physically or drawing verified;
2. selected truck envelope is physically or drawing verified;
3. the chosen mechanical-brake interface is defined and verified;
4. a full steering + suspension motion sweep has been completed and recorded;
5. all geometry validation checks pass;
6. the rider-interface keep-out remains intact until Rev-B fit authority.

Even then, this milestone authorizes only an **unpowered rolling chassis**. It does not authorize motors, traction battery, high-current ESC operation, or powered hill testing.
