# CAD Twin v4: synchronized candidate 3D evidence view

Status: **research-only on draft PR #114**. This is a software visualization and geometry-algorithm milestone, not a dimensional qualification or manufacturing / buying instruction.

## What this adds

The existing assembled and exploded Loaded Tangent presentation remains the primary visual, using **seven source-named procedural component categories** under one complete-board purchasing package. Zero components are replaced by unverified imported meshes.

When users open **CAD asset laboratory → Metric datum alignment and collision broad-phase**, they may either run the **synthetic steering example** or provide a JSON metrology fixture. The system renders:

- The existing candidate AABB pair table and optional motion-sweep SVG.
- An independently orbitable WebGL **candidate 3D envelope scene** in the fixture's own millimeter coordinates. The visible parts are semitransparent **boxes**, not high-fidelity CAD solids. Three-point-derived rigid frames place those boxes; for a supplied motion block, the assumed axis rotates only the requested moving box.
- A native keyboard/touch range slider to select **only precomputed sample angles**. Its selected-angle text and the SVG cursor follow the same discrete sample index. Highlighted boxes identify broad-phase `POSSIBLE_OVERLAP_REQUIRES_NARROW_PHASE`, never confirmed physical contact.
- The same zero-authority flags and exact parent-kit identity in each exported result. A wrong-variant, malformed or forged-authority fixture is held, and changing the selected complete kit hides and invalidates the previous scene.

The pure `builder/cad_candidate_scene.mjs` model compiler is testable without a renderer. `builder/cad_candidate_viewer.mjs` lazily constructs and reuses box and outline geometry rather than rebuilding on each sample, requests WebGL frames only around interaction, caps pixel density and releases owned GPU resources. The SVG and JSON outputs still work when WebGL or CDN modules are unavailable.

## Geometry and accuracy limitations

**These are assumed motion studies, not actual Paris V3 steering kinematics.** A rigid box rotation about a chosen axis is only a mathematical hypothesis; the truck hanger moves through geometry defined by its bushings, kingpin, pivot cup and rider load. Even a real source STEP for the part would not establish its assembly transform or steering movement.

The screen does **not** approve wheel bite, turning clearance, truck compatibility, loads, deck deflection, axle/pivot travel, wheel hub/bearing seats, fastener counts or charging/powered use. Nonoverlap in a discrete sampled AABB is not proof of clearance between samples or of true mesh geometry. Positive broad-phase overlap is not physical contact. The source format still requires independent verified datums and uncertainty envelopes before physical engineering analysis is appropriate.

## Review checklist

1. Run `node --test tests/js/test_outdoor_cad_candidate_scene.mjs tests/js/test_outdoor_cad_candidate_motion.mjs` and the full existing validation workflow.
2. In Chromium, confirm the synthetic example yields two boxes, the seven source-listed board categories remain in the main scene, and Arrow/Home/End moves the same chosen sample in both the SVG and 3D displays.
3. Submit a valid static JSON fixture and confirm its angle control is disabled. Submit a wrong-variant fixture and a forged motion-approval fixture and confirm that stale 3D evidence disappears.
4. Inspect the new candidate-snapshot artifacts on both desktop and mobile, including real-device touch, keyboard, screen-reader labeling and WebGL fallback.
5. Acquire permission-cleared, revision-specific actual STEP/GLB data before claiming any manufacturer shape. Then capture physical mounting datums and actual purchased/received kit revisions. **The registry is still 0/7 source-file-backed CAD assets**, 0 physically verified mates and 0 qualified clearance checks.

See [CAD Motion v3](browser_cad_motion_v3.md), [Metric CAD v2](browser_cad_metric_twin_v2.md), and the [original maker Tangent complete board spec](https://www.loadedboards.com/products/tangent-longboard-skateboard).
