# Adjustable rider-fit subsystem

Worcester X1 does not assume a perfectly symmetric rider or stance.

The public repository contains the fit schema and algorithms only. Raw scans, exact measurements and calibration recordings belong under `rider/private/`, which is excluded from version control.

The fit system separates:

1. geometric measurements from a calibrated mesh and direct measurement,
2. static foot loading from a calibration platform,
3. dynamic pose during lean/carve/braking drills, and
4. board response from the deck IMU and wheel sensors.

Geometry is not automatically converted into steering bias. Rev-B CAD should support independent binding position, yaw, lateral offset and removable cant shims while leaving truck geometry symmetric by default.
