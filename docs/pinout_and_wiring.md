# X1 Alpha wiring and pinout plan

## Power tree

`14S4P pack -> DC-rated main fuse -> service disconnect / precharge -> split -> VESC L + VESC R`

The pack builder must size the fuse, conductor gauge, connector and precharge system for the final current limits, cable lengths and thermal environment.

### Initial VESC electrical limits for commissioning
- pack nominal: 50.4 V
- pack full: 58.8 V
- initial battery-current max: 20 A per VESC
- initial regenerative battery current: 5 A per VESC
- initial motor phase-current max: 26–30 A per VESC in Learn commissioning
- initial motor brake current: 20 A per VESC
- configure an independent ERPM/speed limit in VESC Tool

## CAN
Use a proper twisted pair and terminate the physical bus only at its two ends.

Suggested topology: `VESC L (ID 10) — VESC R (ID 11) — BMS — X1 ECU`

Do not allow two independent applications to fight for current control during integration.

### ESP32-S3 development pin assignment
- CAN TX: GPIO 5
- CAN RX: GPIO 6
- front Hall L: GPIO 9
- front Hall R: GPIO 10
- SPI SD and I2C IMU: assign after board/module selection

Use a 3.3 V-compatible CAN transceiver. The ESP32 TWAI peripheral is not the physical CAN transceiver.

## Front wheel sensing
Initial target is 6–12 magnetic pulses per undriven front wheel revolution. Prefer digital/Schmitt Hall outputs, robust strain relief and sensor wiring separated from motor phase leads.

## Temperature
Minimum channels are left/right motor, left/right VESC and multiple battery/BMS temperature sources. Where VESC already reports motor/FET temperature over CAN, consume that instead of duplicating the sensor.

## Harness rules
- no unsupported solder joint carries pack or phase cable weight
- service loops at steering trucks
- abrasion sleeve at deck/enclosure edges
- strain relief before every bulkhead connector
- label both ends of CAN, phase, sensor and charge harnesses
- witness-mark structural fasteners after torque verification
