# X1 asymmetric fit-rig protocol

The fit rig exists to learn a comfortable, repeatable stance before personalized geometry is transferred to a rideable board.

## Safety boundary

The generated footplates and wedges are **unpowered calibration fixtures only**. Do not use the fit-rig parts as structural riding hardware. Keep the actual trucks mechanically symmetric during this phase.

This is an engineering fit process, not a medical assessment. Any clinician- or therapist-provided stance/joint-loading constraint should be treated as an external requirement that the optimizer is not allowed to override.

## Why left and right are independent

The software does not assume equal foot dimensions, equal foot angle, equal lateral offset, equal forefoot/heel loading, or a centered body line. It also does not infer physical foot dimensions from shoe-size labels.

## Capture sequence

1. Record standing height and body mass directly.
2. Measure each bare foot separately: heel-to-longest-toe length and maximum forefoot width in millimetres.
3. Capture a neutral 3D scan and a comfortable unpowered riding-stance scan if available.
4. On the adjustable fit rig, find a stance that feels natural without deliberately trying to be symmetric.
5. Record left/right plate center, yaw angle, and center-to-center stance width.
6. Calibrate each load-cell zone from raw counts to newtons using `fit/pressure_calibration.py`.
7. Record at least three 20-second four-zone neutral trials, fully stepping off and remounting between trials.
8. Record deck IMU simultaneously; optionally record optical or RuView pose.
9. Synchronize streams only within a bounded clock tolerance using `fit/session_sync.py`.
10. Rank candidates with `fit/fit_score.py`, then freeze only geometry that is comfortable, repeatable and mechanically feasible.

## Required dimensional inputs before Rev-B rideable CAD

- left foot length and maximum width, mm
- right foot length and maximum width, mm
- left/right natural foot yaw, degrees
- comfortable stance width, foot-center to foot-center, mm
- left/right plate lateral offset relative to deck centerline, mm
- any deliberately selected cant wedge angle

## Load inputs

The four zones are:

- left heel
- left forefoot
- right heel
- right forefoot

A repeatable non-50/50 left/right load split is not automatically an error. Do not convert a load difference directly into unequal truck spring preload. First evaluate whether binding position, yaw, stance width or removable footplate cant improves comfort and neutral board behavior.

## Dynamic pose

RuView or optical pose is optional and auxiliary. Current X1 tooling normalizes a 17-keypoint pose stream for repeated-motion comparison, but pose coordinates are not treated as authoritative manufacturing dimensions. Direct measurement and calibrated body geometry remain the CAD source of truth.

## Privacy

Raw meshes, medical information, exact personal measurements, CSI recordings and camera data belong under `rider/private/` or another local private store. The public repository contains only schemas, tooling, tests and non-identifying example data.
