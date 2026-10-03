# X1 SnowDeck v0.1 rider-interface study

Status: reversible bench experiment only.

## Design intent

Explore whether a personalized rider interface can increase snowboard-like edge leverage and reduce trail chatter without replacing the known mountainboard deck/truck architecture.

The first experiment is deliberately local and reversible. It does not redesign the structural deck, truck, brake, drivetrain, or wheel system.

## Architecture

Each foot uses an independently adjustable removable interface:

- universal fit plate
- longitudinal adjustment
- yaw adjustment
- bounded cant wedge
- optional heel/toe ramp
- optional compliant insert
- positive fastener retention
- no permanent structural deck drilling before the existing rider-fit/template gates

The existing Fit Rig remains the measurement platform.

## Variables

Treat each variable independently before combining them:

### Geometry
- stance width
- left/right yaw
- fore/aft placement
- cant angle
- heel ramp height
- toe ramp height
- usable edge-leverage arm

### Compliance
- vertical deflection under static load
- torsional deflection under controlled heel/toe moment
- return hysteresis
- visible rocking
- insert compression set after repeated loading

### Rider-force behavior
After four-zone qualification:
- left/right total load
- heel/forefoot distribution
- front/rear distribution
- repeatability across natural remounts
- distribution during controlled knee bend and static carve poses

## Experiment matrix

Start with rigid controls:

- S0: rigid plate, zero cant, zero ramp
- S1: rigid plate, mild cant
- S2: rigid plate, heel/toe ramp only

Only after rigid geometry is understood:

- C1: low-compliance insert
- C2: alternate insert
- C3: asymmetric insert only if repeatable evidence supports a rider-specific need

Do not combine multiple new variables in the first comparison.

## Acceptance observations

A candidate is interesting only if it preserves all of:

- stable foot support
- no unexpected rocking
- predictable return after unload
- positive fastener retention
- adequate step-off freedom
- no interference with binding hardware
- no intrusion into truck/wheel/brake sweep
- no use of the interface as a safety-critical brake or chassis member

Any perceived comfort or carve improvement remains subjective until repeated observations and force data agree.

## TorsionDeck sub-study

A later bench-only sub-study may place a thin constrained compliant layer beneath each fit plate.

Measure:

- torsional stiffness proxy from applied heel/toe moment vs angular displacement
- vertical stiffness proxy
- hysteresis
- damping/settling time
- cross-axis coupling
- fastener/preload sensitivity
- permanent set

The goal is not maximum flex. The goal is a small, repeatable mechanical transfer function between foot input and the known structural deck.

If the layer creates ambiguous control, slow return, fastener migration, overload-stop contact, or inconsistent force readings, reject it.

## Adjustable-interface safety boundary

Snowboard-style fixed boot retention is not assumed appropriate for X1.

Any retention concept must preserve deliberate emergency disengagement and must be evaluated separately from the fit-plate geometry. Until that work exists, the study treats the foot interface as open/removable and does not authorize ride use.

## Public/private boundary

Public CAD may contain generic adjustment envelopes and plate geometry.

Private evidence may contain actual foot dimensions, preferred stance, or rider-specific calibration data. Those values do not belong in checked-in public showcase files.

## Relationship to current gates

SnowDeck v0.1 does not alter:

- Issue #4 one-zone qualification
- Issue #63 off-axis repeatability qualification
- Issue #25 chassis purchase release
- Issue #12 rolling chassis
- Issue #14 brake interface
- Issue #19 brake/drive topology

Rider-specific final geometry remains downstream of qualified fit evidence.

## Decision record

The first useful decision is not "build SnowDeck."

It is:

> Does a removable, bounded rider-interface change produce repeatable improvements in leverage/comfort/control proxies without adding instability or obscuring the existing mechanical safety case?

Only physical bench evidence can answer that question.
