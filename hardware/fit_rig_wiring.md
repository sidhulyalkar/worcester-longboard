# X1 Fit Rig v0.3 wiring architecture

This document covers the **low-voltage, unpowered calibration fixture only**.

## Signal topology

```text
LEFT HEEL cell ------ HX711-LH ----\
LEFT FOREFOOT cell -- HX711-LF -----\
RIGHT HEEL cell ----- HX711-RH ------> ESP32-S3 ---> USB serial / private log
RIGHT FOREFOOT cell - HX711-RF -----/       |
                                            +---- I2C IMU
                                            |
                                            +---- microSD (optional)
```

Each force zone remains electrically independent all the way to software.

## Suggested development GPIO map

This is a reference pin map for an ESP32-S3 DevKit. Confirm the exact development board pinout before wiring.

| Signal | GPIO |
| --- | ---: |
| LH HX711 DOUT | 4 |
| LH HX711 SCK | 5 |
| LF HX711 DOUT | 6 |
| LF HX711 SCK | 7 |
| RH HX711 DOUT | 8 |
| RH HX711 SCK | 9 |
| RF HX711 DOUT | 10 |
| RF HX711 SCK | 11 |
| I2C SDA | 17 |
| I2C SCL | 18 |
| microSD CS | 21 |

The reference map deliberately gives every HX711 its own clock line. This makes one channel easier to isolate, power-cycle and diagnose without coupling acquisition timing to the other three.

## Power

- power the ESP32-S3 from USB during initial calibration
- power HX711 logic according to the specific breakout requirements
- use a common low-voltage ground between ESP32, ADC modules and IMU
- keep sensor wiring physically away from mains adapters and future motor/phase wiring
- do not connect the X1 traction battery to this fixture

## Load-cell wiring

For a full-bridge four-wire sensor, identify excitation+/-, signal+/- from the sensor datasheet. Connect those to the corresponding HX711 bridge terminals. **Do not assume colors are universal.**

Before standing on the fixture:

1. verify each channel responds to hand pressure
2. verify increasing load gives a monotonic reading
3. verify the other three unloaded zones remain approximately stable
4. install mechanical overload stops
5. calibrate each zone independently with a known mass

## Data contract

The calibrated neutral-trial CSV consumed by `fit/trial_summary.py` uses:

```text
t_s,left_heel_N,left_forefoot_N,right_heel_N,right_forefoot_N,roll_deg
```

Preserve raw ADC counts in a separate file or additional columns. Never discard the raw readings after calibration because they are needed to diagnose drift or redo calibration later.

## Clocking

Prefer one ESP32 clock for all four force channels and the fixture IMU. If RuView is recorded separately, save both the RuView source timestamp/frame ID and host receipt time, then use bounded synchronization rather than pretending the two clocks are identical.

## Fault handling

A missing or saturated load-cell channel invalidates that trial. A missing RuView frame does **not** invalidate a force/IMU trial because RuView is optional. No fit-rig sensor is a powered-board control input.
