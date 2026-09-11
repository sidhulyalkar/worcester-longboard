# X1 fit calibration data pipeline

The goal is to fit the board to a repeatable neutral stance without assuming the rider is symmetric.

## Data authority

1. **Direct measurement / calibrated optical scan**: manufacturing geometry.
2. **Four-zone load rig**: observed heel/forefoot and left/right loading.
3. **Fixture IMU**: neutral roll/pitch and response during lean drills.
4. **RuView or optical pose**: optional dynamic landmark trajectories.

No one stream is allowed to silently replace another. Shoe size is metadata, not a foot-length measurement, and Wi-Fi pose coordinates are not treated as millimetre-accurate CAD geometry.

## Sensor acquisition authority

Each neutral trial begins with the ESP32-S3 raw logger:

```text
t_us,left_heel_raw,left_forefoot_raw,right_heel_raw,right_forefoot_raw,load_valid_mask,roll_deg,imu_ok
```

Use the 10 SPS firmware/hardware RATE configuration for quiet static zero/known-mass work and the 80 SPS configuration for remount/lean capture. The logger startup header records the configured rate. Firmware and the physical HX711 RATE state must agree.

`load_valid_mask=15` means all four force channels were present for that sample. Missing channels remain visible as `nan`; one failed ADC does not freeze the rest of the logger.

## One-zone mechanical pilot before calibration

Before building all four force zones:

1. generate the vendor-pattern pilot from `cad/generate_fit_rig.py`,
2. fit one physical Phidgets 3135 into the pod/pad stack,
3. verify the current 55 x 12.65 x 12.65 mm body and 40 mm two-hole M5 pattern,
4. verify fixed/wire-end and loaded/free-end orientation,
5. check screw length and flexure clearance,
6. verify the hard stop remains clear throughout normal known-mass loading,
7. record the physical verification privately and run `tools/validate_fit_rig_measurements.py`,
8. only then duplicate the force zone four times.

## Calibration sequence

Create a private calibration file:

```bash
cp fit/calibration.example.json rider/private/fit_rig_calibration.json
```

For each installed zone:

1. zero with the complete mechanical stack installed and unloaded,
2. apply a known mass independently to that zone and record loaded counts,
3. enter `zero_raw`, `loaded_raw`, and measured `known_mass_kg`,
4. verify a second independent mass reconstructs plausibly,
5. repeat zero after removing the verification mass,
6. investigate mechanical rubbing, screw contact, stop contact, or drift before accepting a bad channel.

Do not reuse one cell's calibration for another cell.

## Raw-log quality gate

Before converting a neutral trial:

```bash
python tools/summarize_fit_rig_raw.py \
  rider/private/sessions/stance-A/remount-1.raw.csv
```

The current qualification gate requires, per remount trial:

- strictly monotonic timestamps,
- at least 20 s raw duration for Rev-B qualification,
- >=98% complete four-channel force coverage,
- >=98% validity for every individual force channel,
- >=95% valid fixture-IMU coverage.

The quality report does not repair bad data. A failed channel remains a reason to inspect the hardware or wiring.

## Deterministic raw-to-force conversion

Once the raw log and calibration are healthy:

```bash
python tools/calibrate_fit_rig_raw.py \
  rider/private/sessions/stance-A/remount-1.raw.csv \
  rider/private/fit_rig_calibration.json \
  rider/private/sessions/stance-A/remount-1.calibrated.csv
```

This emits only complete four-force-channel samples with valid fixture roll into the qualified calibrated schema:

```text
t_s,left_heel_N,left_forefoot_N,right_heel_N,right_forefoot_N,roll_deg
```

A `--diagnostic-override` exists for debugging an imperfect raw log, but that does **not** make the resulting session Rev-B-qualified. Raw logs are retained permanently alongside calibrated derivatives.

## Session structure

For each candidate stance, record at least three full step-off/remount trials. The private manifest follows `fit/session_set.example.json` and records both `raw_log` and calibrated `csv` for every trial plus:

- candidate/trial IDs,
- left/right yaw,
- measured stance width,
- optional left/right cant/offset metadata,
- private comfort notes outside public Git history.

## Candidate scoring and Rev-B gate

Run:

```bash
python tools/score_fit_session.py \
  rider/private/sessions/stance-A/session.json \
  --out rider/private/sessions/stance-A/report.json
```

`fit/fit_score.py` rewards low remount-to-remount variation, low neutral fixture-roll bias, low roll RMS noise, and repeatable stance width/yaw. It deliberately **does not** penalize a stable non-50/50 left/right load split.

`fit/rev_b_gate.py` then combines:

- direct dimensional completeness,
- >=3 remount trials,
- raw sensor-quality provenance,
- load-distribution repeatability,
- neutral roll bias/RMS,
- stance-width repeatability,
- independent left/right yaw repeatability,
- the invariant that truck geometry remains symmetric during this fit phase.

A low numerical score is not an ergonomic or medical truth function. Subjective comfort remains an explicit private acceptance input before geometry is frozen.

## RuView integration

`fit/ruview_adapter.py` normalizes RuView-style 17-keypoint payloads while marking the data as non-authoritative for metric geometry and vehicle control. Full CSI hardware is optional; the force/IMU fit workflow remains usable without it.

If pose is recorded on a separate clock, preserve source frame/timestamp plus host receipt time and use `fit/session_sync.py` only within a bounded synchronization tolerance.

## Transition to Rev-B CAD

Issue #3 remains blocked until Issue #2 closes. A candidate may become Rev-B rider-interface geometry only when:

- both foot length and maximum width are directly measured,
- natural left/right yaw and stance width are repeatable,
- one-zone mechanical pilot and four-zone calibration are qualified,
- raw session quality passes,
- neutral roll is acceptably small/repeatable,
- >=3 complete remount trials support the candidate,
- the stance is explicitly comfortable,
- the final geometry is physically templated before permanent deck drilling.

Truck geometry remains symmetric unless later vehicle testing produces independent evidence for a mechanical change.
