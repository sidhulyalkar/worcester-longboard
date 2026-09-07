# Worcester X1 Alpha commissioning gates

## Gate 0 — mechanical rolling chassis, no traction battery
- [ ] correct deck ply selected from manufacturer guidance
- [ ] front hydraulic brake truck clears deck through full steering range
- [ ] rear spur drive clears deck/wheels through full steering range
- [ ] wheel bearings/spacers installed per manufacturer
- [ ] wheel fasteners torqued per manufacturer and witness-marked
- [ ] bindings and heel straps adjusted so release can be practiced while stationary
- [ ] hydraulic brakes stop the unpowered board on a gentle slope
- [ ] battery mockup does not contact feet or steering hardware at full deck flex

## Gate 1 — battery/electronics bench, wheels disconnected or drive lifted
- [ ] battery builder provides pack test report and BMS configuration
- [ ] pack polarity independently verified before connection
- [ ] main fuse installed
- [ ] precharge / anti-spark operation verified
- [ ] VESC L/R firmware versions match
- [ ] CAN IDs unique
- [ ] motor temperature sensors valid
- [ ] motor direction verified at very low current
- [ ] remote-loss behavior verified
- [ ] mechanical brake remains entirely functional with system powered off

## Gate 2 — wheels airborne
- [ ] `X1_ALLOW_MOTOR_OUTPUT` enabled only after Gate 1
- [ ] Learn mode only
- [ ] conservative phase/battery limits retained
- [ ] front wheel sensor direction / pulse count verified by hand
- [ ] rear estimated wheel speed matches measured tire circumference
- [ ] TC artificially triggered in software test and reduces only intended side
- [ ] regen voltage taper verified with simulated sensor input before real battery test
- [ ] CAN dropout causes zero propulsion, not a hard brake

## Gate 3 — walking-speed test
- [ ] controlled private/legal test area without pedestrians or traffic
- [ ] 7 mph Learn cap
- [ ] hydraulic brake tested first
- [ ] remote failsafe tested
- [ ] logs record wheel speeds, command current, pack V, temperatures and faults
- [ ] no enclosure movement or cable chafe

## Gate 4 — low-speed dirt
- [ ] Trail mode remains locked until Learn logs are clean
- [ ] validate TC intervention progressively on loose dirt
- [ ] inspect drivetrain tub, gears, seals and fasteners after session
- [ ] check battery enclosure mounts after deck flex cycles

## Speed/current unlock rule
A higher mode is unlocked only after mechanical inspection, clean telemetry and repeatable braking/failsafe behavior.
