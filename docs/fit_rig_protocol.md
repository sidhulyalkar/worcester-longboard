# X1 asymmetric fit-rig protocol

The fit rig exists to learn the rider's comfortable, repeatable stance before any personalized geometry is transferred to a rideable board.

## Safety boundary

The generated footplates and wedges are **unpowered calibration fixtures only**. Do not use the fit-rig parts as structural riding hardware. Keep the actual trucks mechanically symmetric during this phase.

This is an engineering fit process, not a medical assessment. If a clinician or therapist has a stance/joint-loading constraint, treat that as an external requirement rather than something the optimizer should override.

## Why left and right are independent

The software does not assume equal foot dimensions, equal foot angle, equal lateral offset, equal forefoot/heel loading, or a centered body line. It also does not infer physical foot dimensions from shoe-size labels.

## Capture sequence

1. Record standing height and body mass directly.
2. Measure each bare foot separately: heel-to-longest-toe length and maximum forefoot width in millimetres.
3. Capture a neutral 3D scan and a comfortable unpowered riding-stance scan.
4. On the adjustable fit rig, find a stance that feels natural without deliberately trying to be symmetric.
5. Record left/right plate center, yaw angle, and center-to-center stance width.
6. Record at least three 20–30 second four-zone load trials.
7. Repeat after stepping off and remounting. A setup is more useful when the load pattern is reproducible, not merely visually symmetric.
8. Use optional optical or Wi-Fi CSI pose tracking to compare pelvis/shoulder/knee trajectories across gentle heel/toe lean drills.
9. Freeze only the geometry that remains comfortable and repeatable across sessions.

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

Do not convert a left/right load difference directly into unequal truck spring preload. First see whether binding position, yaw, stance width, or removable footplate cant improves comfort and repeatability.

## Dynamic validation

If a Wi-Fi CSI pose system is available, use it as a repeated-motion sensor rather than a dimensional ruler. Compare neutral stance, gentle toe/heel lean and carve posture across repeated trials. Manufacturing dimensions should still come from direct measurements or calibrated 3D geometry.

## Privacy

Raw meshes, medical information, exact personal measurements, CSI recordings and camera data belong under `rider/private/` or another local private store. The public repository should contain only schemas, tooling, tests and non-identifying example data.
