# Worcester X1 Rev-C energy, range, and charging architecture

**Status:** planning and mechanical-UX architecture.  
**Battery purchase authority:** none.  
**Charger purchase authority:** none.  
**Powered operation:** not authorized.

## Product goal

The board should not feel like a battery carrier that happens to turn.

Rev-C separates:

1. **installed energy**: the mass physically attached to the board on this ride;
2. **trip energy**: the total energy needed to complete the mission with reserve;
3. **charge power**: how quickly an approved battery/charger system can replenish energy;
4. **charging UX**: how little handling and connector fuss is required to park and charge safely.

Those are related, but they are not the same design variable.

## Current commercial reference facts

The dated source snapshot is `hardware/rev_c_energy_charge_snapshot_2026-10-01.json`.

Current MBS reference packs provide a useful architecture comparison:

| Reference | Nominal energy | Published battery mass | Derived Wh/lb | Quick swap |
|---|---:|---:|---:|---|
| AGENT 540 | 540 Wh | 15 lb | 36.0 | yes |
| AGENT 1080 | 1089 Wh | 20 lb | 54.45 | yes |

The striking result is not merely that the larger pack has more range. It is also much more energy-dense at the **pack-system level** in these published references.

Two 540 references would provide 1080 Wh of **battery inventory** and 30 lb of total pack mass, but a true cold-swap strategy would still install only one 15 lb pack on the board at a time. One 1089 Wh reference installs 20 lb continuously.

That makes the real trade more interesting than a simple 30-versus-20 lb comparison:

- one 540 installed: lower board mass and potentially better handling, but only trail-class range before a logistics stop;
- two 540s in inventory: near-1080 trip energy, but the spare needs a safe off-board location and a route that can reach it;
- one 1089 installed: much more continuous range with no mid-trip swap, but +5 lb of installed battery mass versus one 540 reference.

That does **not** select an MBS pack for X1. It means modularity should be used intelligently:

- daily/light mission: install the lighter trail-class pack when its range is enough;
- long mission: install the denser range-class pack when its mass is justified;
- cold swap: useful when a spare can remain at a safe logistics point, not as an excuse to carry an unprotected traction pack on the rider;
- permanent duplicate packs: avoid unless a later architecture proves a compelling reason.

## Conservative range planning

`simulation/range_envelope.py` and `simulation/rev_c_energy_planner.py` use the current planning cases:

- mixed surface: 22-30 Wh/mi;
- trail: 32-45 Wh/mi;
- default reserve: 20%.

These are planning numbers, not product claims.

At 20% reserve:

| Pack reference | Trail planning envelope | Mixed-surface planning envelope |
|---|---:|---:|
| 540 Wh | 9.6-13.5 mi | 14.4-19.6 mi |
| 1089 Wh | 19.4-27.2 mi | 29.0-39.6 mi |

This is why the existing 20-mile trail and 30-mile mixed-surface goals need telemetry rather than optimism. The 1089 Wh reference barely misses the conservative end of each target under the current planning assumptions.

## Mission planning

Example:

```bash
python simulation/rev_c_energy_planner.py \
  --distance-miles 20 \
  --terrain trail \
  --pack-wh 1089 \
  --reserve 0.20
```

The tool reports required nominal energy, the pack's planning range envelope, and how many cold-swap pack equivalents would be required under optimistic and conservative consumption cases.

It does not select or authorize a battery.

## Charge-time arithmetic is not a charge-time claim

Energy divided by charger power gives only a mathematical lower bound.

For example:

```bash
python simulation/rev_c_energy_planner.py \
  --pack-wh 1089 \
  --charger-w 1050 \
  --start-soc 0.10 \
  --target-soc 0.90
```

The result is an ideal lower bound of about 49.8 minutes for adding 80% of 1089 Wh at a hypothetical constant 1050 W.

Real charging takes longer because a real battery/charger system has conversion losses, current limits, temperature limits, balancing, and charge taper. The tool therefore always emits `actual_charge_time_claimed=false` and `compatibility_claimed=false`.

## Current charger references

MBS currently lists:

- part 16571: AGENT charger, 75.6 V x 7 A, 530 W;
- part 16572: Exway Smart Super Charger, 1050 W.

MBS explicitly markets the 1050 W charger as an upgrade for the AGENT 1080. Do not infer that it is approved for another pack.

UL micromobility guidance treats the battery, charger, and electrical system as a system-level compatibility problem. X1 follows the same conservative design rule: **only the charger explicitly approved for the selected battery system may be used.**

## Charging should be mundane

The desired daily interaction is:

1. roll or carry the board into its parking location;
2. place it into a stable cradle;
3. the cradle self-centers the board;
4. connect the battery/system-approved charger with minimal connector handling;
5. verify charge state using the selected system's normal indicators;
6. unplug before removing the board.

The first dock is deliberately passive.

## Passive charge-cradle architecture

The dock is a mechanical alignment and cable-management device.

It may include:

- a stable parking cradle;
- wheel/deck guides that self-center the board;
- a floating charger-plug carriage or one-handed mechanical mating aid;
- connector strain relief;
- protected cable routing;
- clear parked-state indication;
- access that does not require lifting the board for normal charging.

It must **not** include, unless a future qualified electrical architecture explicitly supports it:

- exposed traction-voltage contacts;
- improvised pogo-pin or magnetic high-voltage contacts;
- charger or BMS bypass;
- pack paralleling;
- automatic hot swap;
- a custom charging power stage;
- assumptions that a mechanically fitting connector is electrically compatible.

## Why the dock should not be the charger

Keeping the charger electrically unchanged has several advantages:

- the selected battery builder/system retains responsibility for charge limits and BMS interaction;
- the dock can be prototyped with inert connector geometry;
- a failed dock cannot silently become an overcharge-control failure;
- charger replacement remains straightforward;
- the cradle can evolve without invalidating the battery's charging electronics.

This is a deliberate product architecture decision: **mechanical cleverness, electrical boredom.**

## Inert dock qualification

Initialize a fresh private inert session:

```bash
python tools/init_rev_c_charge_dock_session.py \
  rider/private/energy/dock-01
```

The initializer refuses to overwrite a non-empty session and creates a non-authoritative workspace with `dock_manifest.json`.

The public template is `hardware/rev_c_charge_dock_mechanical_template.json`.

Qualify with:

```bash
python tools/qualify_rev_c_charge_dock.py \
  rider/private/energy/dock-01/dock_manifest.json \
  --out rider/private/energy/dock-01/dock_authority.json
```

The test uses an inert pack/connector fixture and requires at least five repeatable alignment trials.

It checks that:

- the board is supported without loading brake or drive hardware;
- the connector is never a structural retention element;
- guides center the board repeatably;
- the inert connector seats without forced lateral loading;
- cable strain relief remains effective;
- the cable clears sharp edges and wheel/steering sweep;
- the connector is protected when the board is absent;
- service access remains available;
- nothing shifts, loosens, or is damaged after the trial block.

A passing result still says:

```text
live_battery_test_authorized = false
electrical_charge_authorized = false
procurement_authority = false
powered_operation_authorized = false
```

## Dock timing in the build

Do not freeze the physical charger cradle before these interfaces are real:

- final selected chassis and rider interface;
- qualified brake/drive topology;
- defined power-packaging candidate;
- Issue #21 inert dummy-pack mount;
- selected professional battery architecture;
- selected approved charger and connector orientation.

Before that point, only the UX and inert mechanical principles are frozen.

## Daily charge target

Rev-C does not invent a universal 80% or 90% lithium-battery rule.

If the selected BMS/charger explicitly supports a reduced daily SOC target, that can be used for ordinary short missions. If it does not, follow the battery manufacturer's instructions.

Likewise, storage SOC, charging temperature, charge-rate limits, and balancing behavior come from the selected battery system, not a generic skateboard rule.

## Long-range operating strategy

The preferred decision sequence is:

1. estimate the mission distance and terrain;
2. apply the planning reserve;
3. choose the smallest qualified installed pack that covers the mission with margin;
4. use the range-class pack for genuinely long outings rather than permanently carrying it;
5. use a cold-swap logistics plan only when a safe spare location exists;
6. revise Wh/mi from real telemetry once powered commissioning eventually produces trustworthy data.

That preserves the original product thesis: range should expand **when needed** without making every ride heavy.

## Future data loop

Once powered operation is independently authorized, every real ride should record at minimum:

- pack energy used;
- distance;
- elevation change;
- surface/terrain class;
- average and distribution of speed;
- tire pressure;
- pack temperature;
- ambient temperature where available;
- rider + carried mass configuration.

That lets the planning model graduate from generic 22-45 Wh/mi envelopes to route- and setup-conditioned X1 telemetry.

Until then, the range model remains deliberately conservative.
