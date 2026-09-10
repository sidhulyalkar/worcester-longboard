# X1 fit calibration data pipeline

The goal is to fit the board to a repeatable neutral stance without assuming the rider is symmetric.

## Data authority

1. **Direct measurement / optical scan**: manufacturing geometry.
2. **Four-zone load rig**: observed heel/forefoot and left/right loading.
3. **Deck IMU**: neutral roll/pitch and response during lean drills.
4. **RuView or optical pose**: optional dynamic landmark trajectories.

No one stream is allowed to silently replace another. Shoe size is metadata, not a foot-length measurement, and Wi-Fi pose coordinates are not treated as millimetre-accurate CAD geometry.

## Session structure

For each candidate stance, record at least three remount trials. Each trial should contain:

- candidate ID
- left/right footplate center coordinates
- left/right yaw
- left/right cant wedge
- measured stance width
- raw four-zone ADC counts
- calibrated four-zone forces
- deck IMU stream
- optional dynamic pose stream
- subjective comfort notes stored privately

## Calibration sequence

1. Zero each load cell with the plate installed and unloaded.
2. Apply a known mass independently to each zone and record span counts.
3. Verify that a second known mass reconstructs within the chosen tolerance.
4. Record a 10-20 second unloaded zero-drift check.
5. Record a neutral stance trial.
6. Step off completely, remount, and repeat at least twice.
7. Only then perform slow heel/toe lean drills on the unpowered fixture.

## Candidate ranking

`fit/fit_score.py` rewards low remount-to-remount variation, low neutral deck-roll bias, low roll RMS noise, and repeatable stance width/yaw. It deliberately **does not** penalize a stable non-50/50 load split.

The score is a screening tool, not a medical or ergonomic truth function. Candidate geometry should be frozen only when it is comfortable, repeatable, mechanically feasible, and does not create an undesirable neutral board bias.

## RuView integration

Current RuView documentation exposes a 17-keypoint pose endpoint. `fit/ruview_adapter.py` normalizes that payload into X1's pose schema while explicitly marking the data as non-authoritative for metric geometry. Full CSI hardware is optional; the rest of the X1 fit workflow remains usable without it.

## Transition to Rev-B CAD

A candidate may become a Rev-B binding geometry input only when:

- both foot length and width are directly measured
- natural left/right yaw and stance width are repeatable
- load calibration passes
- neutral roll is acceptably small/repeatable
- the candidate has been remounted across multiple sessions

Truck geometry remains symmetric unless later vehicle testing produces independent evidence for a mechanical change.
