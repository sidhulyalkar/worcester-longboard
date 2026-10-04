# Worcester X1 authority-aware digital twin

Status: visualization and engineering-review layer only. It creates no physical authority.

## Purpose

The X1 digital twin should answer four questions before hardware is committed:

1. What geometry are we actually proposing?
2. What portions are measured, manufacturer-grounded, assumed, or blocked?
3. What moves, collides, flexes, or remains uncertain across the intended motion envelope?
4. Which physical experiment would convert the largest useful uncertainty into evidence?

The viewer must never make speculative geometry look equally trustworthy to qualified geometry.

## Evidence states

Every visual component has exactly one public evidence state:

- `QUALIFIED`: backed by a supplied fingerprint-valid repository authority whose full gate, dependency, and evidence-link checks pass.
- `REFERENCE`: manufacturer or other documented reference, not received-unit measurement.
- `ASSUMED`: parameterized engineering placeholder used only for analysis.
- `BLOCKED`: intentionally unresolved or prohibited from promotion by the current build-authority graph.
- `NOT_PRESENT`: omitted from the current physical configuration.

Private rider measurements never enter the checked-in showcase manifest. Rider-specific views consume a local private overlay generated outside public repository data.

## Required views

### Hero
Clean complete-board presentation. Blocked subsystems remain visually distinguishable and must not imply build readiness.

### Anatomy
Exploded deck, trucks, wheels, brake reference, rider interface, guards, inert energy-storage envelope, and future drive envelopes.

### Rider fit
Footplate zones, yaw/cant adjustment reserve, heel/toe leverage regions, stance keep-outs, and reversible adjustment limits. No private foot dimensions are checked in.

### Steering and carve
Neutral plus positive/negative steering sweep, tire envelope, rider keep-out, and brake/drive keep-outs. Published dimensions remain REFERENCE until physical measurements replace them.

### Topology
Side-by-side display of brake-first 400 mm, drive-clearance 420 mm, and 300 mm hanger plus 70 mm axle topology-study branches. Unknown simultaneous brake/drive compatibility remains visibly BLOCKED.

### Clearance
Ground plane, vulnerable underside volumes, steering sweep, service-removal direction, and later inert-pack keep-outs.

### Risk
Map mechanical-risk register entries to components without turning risk scores into fabricated physics.

### Authority
Show the build-authority dependency graph and the distinction between gate definition and supplied physical evidence.

## Visual grammar

Suggested default presentation:

| Evidence state | Surface treatment |
| --- | --- |
| QUALIFIED | opaque, normal material |
| REFERENCE | cool translucent material |
| ASSUMED | amber translucent material |
| BLOCKED | red wireframe / ghost volume |
| NOT_PRESENT | hidden |

Exact colors are viewer presentation details. State labels remain textual so meaning never depends on color perception.

## Asset pipeline

1. Run the existing CadQuery generators.
2. Export STEP/STL as already supported by the repository.
3. Generate `showcase/x1_runtime_manifest.json` with `tools/build_showcase_manifest.py`.
4. Serve the repository locally and open `showcase/`.
5. The current web scaffold renders a procedural donor-grounded reference and the authority state even when detailed mesh assets have not yet been exported.
6. Later mesh conversion may add GLB assets, but the GLB pipeline must not alter evidence classification.

## Runtime authority contract

The manifest builder reuses `tools/evaluate_build_authority.py`, rather than inventing a second notion of qualification.

That provides:

- the exact evidence predicates from `hardware/build_authority.json`;
- SHA-256 authority fingerprint verification;
- upstream dependency resolution;
- evidence-link matching between dependent authorities;
- fail-closed handling of missing evidence.

The showcase then maps those evaluated gate states onto visual components. A component has at most one physical promotion gate and may also list contextual gates that affect design maturity without promoting the component itself to QUALIFIED.

The pre-hardware viewer adds one stricter boundary: evidence asserting `powered_operation_authorized=true` is rejected rather than rendered as an active authority.

## Public runtime manifest

The runtime manifest contains only public design metadata:

- schema version
- project/configuration identifiers
- component evidence states
- source paths
- evaluated gate status and blockers
- source-file fingerprints
- safety boundary flags
- rendering hints

It must not contain private anthropometry, private raw fit-rig logs, addresses, personal identifiers, or unsupported measured values.

## Fail-closed rules

- Missing evidence means a gate is closed.
- Merely defining a gate in `hardware/build_authority.json` never makes it pass.
- A document merely claiming `qualified=true` is insufficient.
- Unknown evidence-state strings are invalid.
- No showcase input may set `powered_operation_authorized=true`.
- No visual component may be promoted to QUALIFIED unless the existing authority evaluator satisfies its exact physical promotion gate. Selection/plausibility gates may be shown as context but never silently promoted into physical qualification.
- Blocked propulsion, live battery, charger, and powered-operation concepts remain blocked until their independent repository gates pass.

## Immediate visualization targets

Before chassis purchase, the most useful views are:

1. three full-scale deck candidates with neutral rider keep-outs;
2. brake-first donor geometry with steering sweep;
3. inert range-pack plausibility envelope;
4. brake/drive topology branch comparison;
5. one-zone and future four-zone Fit Rig geometry;
6. SnowDeck v0.1 reversible rider-interface stack;
7. passive charge-cradle alignment concept.

## Exit criterion for Issue #65

Issue #65 may close when the repository has:

- a deterministic public runtime manifest;
- a local viewer that clearly distinguishes evidence states;
- tests proving fail-closed behavior;
- a SnowDeck experiment definition with no fabrication/power authority;
- no change to the Issue #25 -> #4/#63 -> chassis/brake physical sequence.

This work improves review quality. It does not move a physical gate by itself.


## Coordinate and motion contract

The viewer uses the same convention as the rolling-chassis CadQuery references:

- +X: board longitudinal axis;
- +Y: board lateral axis;
- +Z: upward from the ground plane;
- ground: Z = 0.

The browser camera is explicitly configured Z-up. This is required before clearance or steering overlays may be interpreted geometrically.

The procedural motion view currently exposes the documented reference ±22 degree steering envelope. Front and rear axle groups are shown with opposite plan-view yaw for the packaging sweep used by the existing CAD generator. This is an interference visualization, not a validated dynamic steering model.

The clearance view shows the current provisional 65 mm static deck clearance and 45 mm compressed keep-out. Both remain ASSUMED/REFERENCE packaging values until the received donor is measured.

## Generated CAD overlay

`tools/export_showcase_assets.py` converts generated STL files to GLB without changing geometry authority.

Each asset record carries:

- stable `asset_id`;
- source group;
- source path + SHA-256;
- GLB path + SHA-256;
- `physical_authority=false`;
- `powered_operation_authorized=false`.

The browser may overlay the neutral chassis and unioned steering-sweep meshes on the procedural evidence-colored model. The overlay is a geometry audit aid, not a second authority system.

## SnowDeck laboratory view

The viewer exposes independent front/rear:

- plate yaw;
- cant;
- plate separation;
- compliant-layer thickness proxy.

These are broad visualization bounds, not recommended ride settings.

`cad/generate_snowdeck_study.py` produces the universal Fit Rig plate reference, 2 and 4 degree cant-study wedges, and the maximum compliant-insert envelope. Its generated authority explicitly keeps fabrication and ride authority false.

Final rider-specific geometry remains downstream of qualified four-zone evidence and the existing Rev-B/template gates.


## Configuration laboratory

The viewer is also a non-authoritative trade-study laboratory. It may compose known reference and assumed layers into named visualization presets, but a preset is never an engineering release.

The configuration lab must:

- keep physical appearance visually distinct from evidence state, using normal-looking materials for the board and authority-colored outlines/ghost volumes for uncertainty;
- expose deck candidate, truck/topology branch, SnowDeck setup, and system-layer visibility as explicit variables;
- permit brake, drive, inert-pack, SnowDeck, armor, and passive-dock layers to be shown or hidden independently;
- provide named presets only as reproducible starting points for questions such as brake-first packaging, SnowDeck fit, drive packaging, brake/drive coexistence, and service-envelope inspection;
- allow two states to be captured as A and B and compared using descriptive geometry/compatibility fields;
- surface incompatibility or unknown-reference warnings without reducing the design to a synthetic winner score;
- automatically frame the currently visible assembly so a camera setting cannot hide clipping or make a packaging envelope appear larger than the board;
- retain `winner_selected=false` and all existing procurement/fabrication/ride/power boundaries.

The A/B comparison may report deck envelope, truck width, estimated outer wheel width, provisional clearance references, stance, reference brake compatibility, reference drive compatibility, and visible systems. It must not infer strength, ride quality, range, stopping distance, durability, or safety from those geometric fields.

### Physical-looking geometry vs evidence

The default scene should read as a recognizable mountainboard rather than a collection of authority-colored blocks:

- deck, tires, hubs, and trucks use neutral physical materials;
- reference/assumed/blocked status remains visible through colored edges, translucent volumes, textual state labels, and the component panel;
- brake and drive studies may use representative packaging geometry only when clearly marked as reference/blocked;
- the inert pack stays an under-deck envelope, not a battery product claim;
- the passive dock remains mechanically inert in the visualization;
- armor remains a replaceable first-contact study rather than a structural member.

Detailed imported CAD remains available as an overlay for geometry audit. A prettier procedural model never supersedes generated CAD or physical measurement.
