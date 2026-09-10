# Adjustable rider-fit subsystem

Worcester X1 does not assume a perfectly symmetric rider or stance.

The public repository contains the fit schema and algorithms only. Raw scans, exact measurements and calibration recordings belong under `rider/private/`, which is excluded from version control.

The fit system separates:

1. geometric measurements from a calibrated mesh and direct measurement,
2. static foot loading from a calibration platform,
3. dynamic pose during lean/carve/braking drills,
4. board response from the deck IMU and wheel sensors, and
5. session repeatability across full step-off/remount trials.

Geometry is not automatically converted into steering bias. Rev-B CAD should support independent binding position, yaw, lateral offset and removable cant shims while leaving truck geometry symmetric by default.

## Calibration modules

- `pressure_calibration.py`: raw load-cell counts to calibrated force
- `static_load.py`: four-zone left/right and heel/forefoot summaries
- `session_sync.py`: bounded nearest-timestamp stream alignment
- `ruview_adapter.py`: normalizes RuView 17-keypoint pose payloads for dynamic comparison
- `fit_score.py`: ranks repeatable unpowered stance candidates without penalizing stable left/right asymmetry
- `landmarks.py`: private landmark-derived left/right geometry descriptors
- `session.example.json`: non-identifying session schema

See `docs/calibration_pipeline.md` and `hardware/fit_rig_bom.md` for the physical workflow.
