# Browser CAD Twin v3: evidence-backed candidate steering screening

**Release boundary:** Research-only, stacked draft PR #114. Nothing in this implementation establishes an OEM geometry license, a received kit, a verified mount, physical steering clearance, safe wheel bite, order quantity or fabrication approval.

## What changed

The assembled Loaded Tangent remains one maker purchasing package with seven **source-named, procedural** component categories. A new opt-in motion diagnostic lives inside the CAD laboratory's metric sandbox and does not replace or metrically scale that assembled board.

- The **one-click synthetic motion example** creates two tiny abstract boxes and an assumed rotation axis. They are deliberately not a Tangent deck, Paris truck or Orangatang wheel; all 3D poses and clearances are synthetic.
- A survey JSON may optionally include a `motion` block. The workbench computes the already guarded 3-point frames, transforms eight corners of the candidate moving box, samples a user-supplied rigid rotation through an explicit world-space axis and compares resulting broad-phase boxes against selected stationary candidate parts.
- Screening is bounded at 121 angles, 13 stationary parts, steering values between -45° and 45°, and explicit 0–10 mm candidate uncertainty. An overlap means **possible**, not proven contact. A separated AABB means **only this sampled box pair** is separated, not that the real assembly is safe. Angles between samples, wheel deformation, deck flex, true truck kingpin motion, machining deviations and loading are not evaluated.
- The motion report exports its exact assumed angles, candidate classifications and explicit no-authority flags. SVG marks samples but never labels them “safe”, “approved” or “wheel-bite free”. Kit-variant changes clear both the metric report and the motion export.
- The source ledger now includes eight original manufacturer records: Loaded Tangent published complete envelope, Zee Bracket family envelope, Zee DIY template, nominal 105/85 mm wheel diameters, Paris V3 150 mm hanger/215 mm axle/65 mm axle-height claims, and original Orangatang Dad Bod/Caguama wheel widths and contact patches. These are **public specifications, not measured CAD datums**.

## Example optional motion block

Supply this block inside a valid `METRIC_CAD_SURVEY_FIXTURE_RESEARCH_ONLY` JSON document with two or more source-traceable candidate shapes and three or more ordered local-to-assembly landmarks per shape. Part IDs must match that fixture; the user-provided axis is in the same candidate assembly frame, **not** automatically inferred from a truck hanger.

```json
{
  "scope": "CANDIDATE_MOTION_RESEARCH_ONLY",
  "moving_part_id": "hypothesis_wheel",
  "stationary_part_ids": ["hypothesis_deck"],
  "axis_point_assembly_mm": [0, 0, 0],
  "axis_direction_assembly": [0, 0, 1],
  "angle_range_deg": [-30, 30],
  "sample_step_deg": 5,
  "uncertainty_mm": 0.25,
  "kinematics_physically_verified": false,
  "dynamic_clearance_qualified": false,
  "contact_verified": false
}
```

**No sample is a real Paris V3 steering pose until the exact truck revision, rotation center and articulation have been measured independently.** A wheel-bite conclusion requires true wheel geometry, rolling-axis offsets, truck pivot/kingpin and steering dynamics, bushings, loading, worst-case manufacturing variation and physical validation, not merely a bounding-box example.

## Official manufacturer evidence and remaining models

| Source component | Published useful facts | Still needed for an engineering twin |
| --- | --- | --- |
| [Loaded Tangent](https://www.loadedboards.com/products/tangent-longboard-skateboard) | Complete reference kit and envelope | Licensed exact revision STEP or independent 3D measurements; actual received kit |
| [Loaded Zee Bracket](https://www.loadedboards.com/products/zee-bracket) | General envelope and linked DIY cutting stencil | Bracket STEP, actual mounting plane, hole center locations, tolerance and revision |
| [Paris V3 150 mm 50°](https://www.paristruckco.com/products/v3-150mm-50-polished) | Hanger 150 mm, axle 215 mm, axle height 65 mm | Source-specific 3D geometry, kingpin/pivot frame and seller V2/V3 ambiguity resolution |
| [Orangatang Dad Bod 105](https://www.orangatangwheels.com/products/dad-bod-105mm-longboard-wheel) | Nominal 105 mm diameter, 62 mm width, 57 mm contact patch | Exact core, bearing seat, axle offset, independent measured wheel |
| [Orangatang Caguama 85](https://www.orangatangwheels.com/products/caguama-85mm-longboard-wheel) | Nominal 85 mm diameter, 58.5 mm width, 56 mm contact patch | Same core/bearing geometry and actual received revision |
| Loaded Jehu V2 bearings and maker hardware | Manufacturer's claimed inclusion categories | Specific seat, spacer, fastener pattern/quantity, pack contents and tolerances |

On the Zee Bracket page, Loaded also publishes an STL for an **optional tail nub**. It is not the Zee Bracket structural model or one of the complete Tangent's seven accounted categories. The catalog does not silently import or redistribute that file.

### Next measurement milestones

1. Request geometry with explicit publication/redistribution permissions from Loaded, Paris and Orangatang, or carry out a separately documented measurement session on the actual received revision.
2. Record **at least four independent**, non-collinear calibrated fiducials per part, source-file digest, instrument uncertainty, true mate contact surfaces, coordinate conventions and a screenshot/measurement receipt.
3. Promote only reviewer-confirmed metric transforms to a separate qualified-schema tier, never by altering the unqualified legacy recipe. Use conservative mesh/solid narrow-phase against real revisions and quantify worst-case stackups.
4. For actual steering, derive a constrained truck/axle articulation from real kingpin/baseplate/pivot geometry. The current **generic pivot model is intentionally not that kinematic chain**.
5. Keep the seller Paris V2/V3 discrepancy and all purchasing/fabrication approvals blocked independently of browser/CI success.

## Test paths

```bash
node --test tests/js/test_outdoor_cad_candidate_motion.mjs tests/js/test_outdoor_cad_metric_workbench.mjs
node tests/browser/parts_picker_smoke.mjs
```

The browser release gate checks a genuine synthetic example, a tampered physical-clearance assertion, JSON export parity, model switching, and preservation of the integrated board. All tests demonstrate **software behavior only**. See `docs/browser_cad_metric_twin_v2.md` for STEP→GLB conversion and registration receipts.
