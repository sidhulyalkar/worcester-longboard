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

The reference map deliberately gives every HX711 its own clock line. This makes one channel easier to isolate and diagnose without coupling its readout pulses to the other three.

## HX711 sample-rate contract

The selected SparkFun HX711 breakout supports 10 or 80 samples/s. The hardware RATE jumper state and firmware build **must agree**.

- `fit_rig_esp32s3_10sps`: use with the breakout in its default 10 SPS hardware state. Prefer this mode for quiet static calibration and zero/drift characterization.
- `fit_rig_esp32s3_80sps`: use only after configuring the physical breakout RATE jumper for 80 SPS. Prefer this mode for remount, lean, and dynamic pose/IMU comparison where timing resolution matters more than lowest per-sample noise.

The logger prints `# hx711_sps=<10|80>` and a rate-contract warning at startup. Record those header lines with the raw session log.

Do not flash the 80 SPS build and assume it changes the breakout electrically; firmware cannot substitute for the physical RATE configuration.

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

## Raw logger contract

The ESP32 logger emits:

```text
t_us,left_heel_raw,left_forefoot_raw,right_heel_raw,right_forefoot_raw,load_valid_mask,roll_deg,imu_ok
```

`load_valid_mask` uses bits 0..3 for LH, LF, RH, RF respectively. A complete four-zone sample is `15` (`0b1111`). If a channel misses the bounded readiness window, its raw field is `nan` and its bit is cleared rather than freezing the entire logger.

The calibrated neutral-trial CSV consumed by `fit/trial_summary.py` remains:

```text
t_s,left_heel_N,left_forefoot_N,right_heel_N,right_forefoot_N,roll_deg
```

Only rows with all four valid force channels should enter a qualified neutral-trial reduction. Preserve the raw logger file even after calibrated conversion so drift and calibration can be replayed.

## Clocking

Prefer one ESP32 clock for all four force channels and the fixture IMU. The logger waits a bounded interval for all four HX711 channels, with the interval selected from the declared 10/80 SPS firmware mode.

If RuView is recorded separately, save both the RuView source timestamp/frame ID and host receipt time, then use bounded synchronization rather than pretending the two clocks are identical.

## Fault handling

A missing or saturated load-cell channel invalidates that individual sample and may invalidate a trial if complete coverage is insufficient. One failed HX711 must not freeze the other channels indefinitely.

A missing RuView frame does **not** invalidate a force/IMU trial because RuView is optional. No fit-rig sensor is a powered-board control input.
