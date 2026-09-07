# Worcester X1 Alpha v0.1 — design specification

## Mission
A trail-first electric mountainboard optimized for control, low-speed authority and repeatable experimentation rather than headline top speed. Alpha is rear 2WD with hydraulic front braking and is mechanically/electrically provisioned for a later AWD front module.

## Frozen Alpha hardware architecture

| Item | Frozen target |
|---|---|
| Deck | TRAMPA 35° HS11 9-69, factory-drilled |
| Front axle | TRAMPA Vertigo/HS11 hydraulic brake truck |
| Rear axle | TRAMPA channel/Vertigo-compatible truck integrated with 2WD spur kit |
| Wheels | 4 × 8 in / ~200 × 50 mm SUPERSTAR 5-spoke pneumatic |
| Rear drivetrain | sealed TRAMPA spur drive, 9:63 helical steel, 7.0:1 |
| Motors | 2 × TRAMPA 6376 160 KV |
| Motor controllers | 2 × VESC 6/75, separate units |
| Battery | professionally built 14S4P Molicel P50B, 20 Ah / 1008 Wh nominal |
| Remote | VESC WAND Magneto + NRF receiver |
| Supervisor | ESP32-S3 Alpha ECU, 100 Hz vehicle control |
| Braking | rear regenerative + front rider-controlled hydraulic |
| Speed ceiling | 25 mph maximum software mode; Learn starts at 7 mph |

## Published packaging references used in CAD
The selected HS11 deck is published as 912 mm tip-to-tip, 228 mm maximum width, 690 mm crease-to-crease, 128 mm crease-to-tip, 35° truck mounting angle and 945 mm factory wheelbase. The assembly model is a packaging reference only, not a replacement for the manufacturer's deck geometry.

## Battery sizing
Molicel P50B reference cell: 3.6 V nominal, 5.0 Ah typical, 18 Wh, 21.55 mm max diameter, 70.15 mm max height.

14S4P:
- 56 cells
- 50.4 V nominal
- 58.8 V at 4.20 V/cell
- 20 Ah nominal
- 1008 Wh nominal

Pack construction is delegated to a qualified high-current battery builder. The CAD provides an envelope; it does not prescribe welding, busbar construction or cell-level assembly.

## Enclosure
Custom Alpha enclosure external body: **330 × 188 × 58 mm**. Battery-enclosure deck drilling and internal pack geometry remain measurement-gated until the finished pack and purchased deck are measured.

## Drivetrain calculations
With 160 KV, 7.0:1 gearing and nominal 8 in / 203.2 mm wheel:

- motor no-load RPM at 50.4 V: 8064 rpm
- motor no-load RPM at 58.8 V: 9408 rpm
- theoretical wheel speed at nominal voltage: ~27.4 mph
- theoretical wheel speed at full voltage: ~31.9 mph
- using an 0.84 first-order load factor: ~23.0 mph nominal, ~26.8 mph full

Motor torque constant: `Kt = 60/(2*pi*160) = 0.0597 N·m/A`.

At 55 A phase current per motor and 90% mechanical efficiency, combined longitudinal wheel force is approximately 407 N on 8 in tires. At a generic light-rider Alpha design mass of 70 kg rider+board, gravity along a 30% grade is ~197 N. Alpha is therefore expected to become traction-limited before motor-torque-limited on loose surfaces.

## Ride modes — initial commissioning values

| Mode | speed cap | max accel | max decel request | phase current cap / motor |
|---|---:|---:|---:|---:|
| Learn | 7 mph | 0.8 m/s² | 1.2 m/s² | 26 A |
| Trail | 14 mph | 1.4 m/s² | 1.9 m/s² | 48 A |
| Flow | 20 mph | 2.0 m/s² | 2.4 m/s² | 65 A |
| Sport | 25 mph | 2.7 m/s² | 2.8 m/s² | 75 A |

These are starting software limits, not evidence that the machine is qualified at those values. VESC battery-current, phase-current, voltage and temperature limits remain a separate hard layer and are set lower during early commissioning.

## Traction control
Vehicle velocity is estimated from the two undriven front wheels. Rear longitudinal slip estimate for each side:

`s = (v_rear - v_vehicle) / max(abs(v_vehicle), 1 m/s)`

Initial threshold:
- <= 10% slip: no intervention
- 10–20%: progressive current reduction
- >= 20%: strong reduction while retaining small crawl torque

Below ~1 m/s, slip ratio is poorly conditioned; TC fades in with speed.

## Regen slip control
During braking the same estimator detects a driven rear wheel decelerating below front-wheel vehicle speed. Regen is progressively reduced for roughly -12% to -25% slip. This is a supervisory traction feature, not a substitute for a certified automotive ABS system.

## Regen voltage envelope
- normal daily charge target: 4.10 V/cell = 57.4 V pack
- full pack: 58.8 V
- supervisor starts tapering requested regen above 57.4 V
- supervisor reaches zero regen request at 58.2 V
- independent hydraulic braking remains available

## Failure philosophy
- remote lost: smoothly ramp propulsion to zero; do not command an automatic hard brake
- stale vehicle-speed data: propulsion to zero
- high pack voltage: regen tapered; hydraulic brake remains available
- CAN/BMS anomalies: fail passive, log fault, reduce operating envelope

## Measurement-gated interfaces
1. battery-enclosure deck drilling coordinates
2. front Hall sensor bracket-to-hanger interface
3. exact bulkhead connector cutouts
4. final battery builder's internal pack/BMS geometry
