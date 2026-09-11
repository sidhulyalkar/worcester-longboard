# X1 one-zone pilot: minimal order and bench BOM

This BOM is intentionally smaller than the four-zone Fit Rig BOM. Buy enough to qualify one physical sensor path plus one untouched spare. Do **not** duplicate all four installed zones until Issue #4 passes.

## Order now

| Qty | Item | Selected class / part | Role | Gate |
|---:|---|---|---|---|
| 2 | Single-point load cell | Phidgets 3135_0, 50 kg | 1 pilot + 1 untouched spare | Required |
| 2 | Load-cell ADC | SparkFun SEN-13879 HX711 | 1 pilot + 1 spare | Required |
| 1 | MCU | ESP32-S3 DevKitC-1 compatible board | Existing fit-rig logger | Required unless already owned |
| 1 | USB data cable | Matches selected ESP32-S3 board | Power + serial capture | Required |
| 1 | M5 metric fastener assortment | short socket-head lengths + washers | Sensor fixed/loaded-end trials | Length measurement-gated |
| 4 | M4 through bolts + washers + nyloc nuts | sized to pilot pod + 8 mm carrier | Pod-to-carrier fastening | Required |
| 4 | Bench fasteners or clamps | through the 6.5 mm carrier holes | Carrier-to-rigid-base fastening | Bench dependent |
| 1 | Flexible 4-conductor sensor wiring kit | solder/strain-relief consumables | Load cell -> HX711 | Required |
| 1 | Digital caliper | 0.01 mm display class is sufficient for screening | Vendor pattern/body checks | Required |
| 1 | Feeler-gauge set | includes leaves around 0.10–1.00 mm | Stop-gap measurement | Required |
| 1 | Rigid pilot base | thick plywood/aluminum/bench fixture | Holds carrier flat | Required |

## Known masses

The default manifest uses nominal 2 kg, 5 kg, and 10 kg ascending plateaus, paired 5 kg and 2 kg descending plateaus, and a 7.5 kg independent validation plateau. Those labels are only a convenient starting sequence.

**Record the actual measured mass used for every plateau.** Do not assume a gym plate, dumbbell, water container, or shipping weight exactly matches its label. The manifest values are evidence, not decoration.

The qualification code imposes a hard 20 kg pilot ceiling. There is no reason to approach the 50 kg cell rating during this experiment.

## Do not order yet

- the other three installed load cells / HX711 channels
- full four-zone fixture fabrication
- rider footplates specifically for standing/remount tests
- traction battery, motors, VESCs, or powered-board hardware for this milestone

The purpose of the pilot is to spend tens of dollars discovering mechanical/sensor problems before spending hundreds or thousands scaling them.

## Identification

Before assembly, label the physical parts with stable local IDs, for example:

- `LC-PILOT-A`
- `ADC-PILOT-A`
- `POD-PILOT-A`
- `PAD-PILOT-A`

Write those exact IDs into the private pilot manifest. If any one of these components changes, create a new authority report for the new stack.
