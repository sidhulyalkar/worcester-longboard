> **Review correction, October 11, 2026:** The earlier two named retailer wheel-setup correspondences are **not two qualified comparable packages**. The manufacturer lists Paris V3 trucks but the Skates USA retailer listing states Paris V2; both comparisons now remain on hold. The pilot distinguishes 14 maker-advertised unreceived child claims (7 per kit) and zero physically verified seller package contents. See [Loaded kit pilot](loaded_tangent_complete_kit_pilot_v1.md).

# Worcester critical review and 2026-10-11 development roadmap

**Scope:** Based on draft PRs #110–#114, maker/retail/source registries, active Builder issues #94–#97 and outdoor catalog #106, plus X1 fit/chassis issues #2, #25 and #37.

**Verdict:** An unusually rigorous research prototype with evidence-aware compatibility and source boundaries, but not yet a complete equipment configurator, seller checkout comparison engine, measured assembly or physical safety qualification. We have expanded demonstration breadth faster than we have closed one complete user workflow.

Run the reproducible audit with:

    python tools/audit_parts_picker_readiness.py --as-of 2026-10-11

Baseline: nine named sports; four active reference-study sports, five taxonomy-only; 24 maker families, 41 referenced variants, 12 curated studies, 18 suppliers in the directory, 16 maker sources, seven maker-unit observations, six dated retail rows, two matched Loaded setups. Exactly zero checkout-confirmed option SKUs, zero physically qualified assembly links, and zero approved orders. These are catalog counts, NOT market share or evidence of safety.

## Severity-ranked findings

| Severity | Finding | Action |
| --- | --- | --- |
| P0 | Five chained draft PRs remain unmerged; main does not yet ship the 4-sport Parts Picker | Human #97 review of exact #114 HEAD, then merge #110 → #111 → #112 → #113 → #114 with CI after each retarget |
| P0 | Manufacturer references are not exact-size seller SKU receipts | Separate ProductFamily / ProductVariant / SellablePackage / dated region-specific SupplierOffer |
| P0 | Assembly graph has no measured or verified mounting connections; 3D is illustrative | Source-authorized geometry, local datums, mate/fastener and clearance contracts, independent physical validation |
| P0 | Ski binding service, board brakes and X1 electrical hardware remain unqualified | Preserve professional ski fit/release, brake-first X1 and independent battery/electrical gates |
| P1 | Five sports have only taxonomy and the four live sports have sparse models | Deepen one complete non-powered build before further breadth |
| P1 | Source family, maker packs, retail listings and curated builds are parallel files | Normalize a typed source claim graph with revision and invalidation propagation; legacy adapter |
| P1 | Complete kits obscure separately included trucks/wheels/bearings/hardware | Closure algorithm that distinguishes seller package vs physical assembly parts without overbuy |
| P1 | Three example presets are curated, not optimized from user goals | Explainable hard/soft constraints, tri-state feasibility and allow fewer than 3 results |
| P1 | Fit requirements differ across ski/boot/binding/stance/axle/hub/brake | Typed compatibility edges with explicit UNKNOWN, CONFLICT, REFERENCE and VERIFIED states |
| P1 | Chromium automation verifies CDN failure fallback, not successful online 3D orbit | Successful WebGL/canvas, camera motion, mobile touch, screen-reader, print and performance review |
| P2 | Runtime Three.js is loaded from esm.sh and maker/page evidence is manually edited | Local pinned bundle, source fingerprints, legal asset/license inventory, audited feed strategy |
| P2 | UI asks novices to choose complex parts before seeing an explanation of goals | Guided rider brief, 3-way comparison, clear missing-item repairs and validated assembly learning |

### Concrete corrected defect: source relevance

The research UI previously showed Atomic Bent 90 ski-only/bundle retailer listings even when Salomon QST 94 was selected. We now attach unresolved seller bundles to a separately validated related product family, show those listings only beside their associated ski, and refuse to promote family evidence to an exact-size checkout SKU. Added pure-JavaScript and real-browser negative tests for leakage and forged family links.

## Product system of record

    Sport / AssemblyTemplate / ProfessionalService
      ProductFamily → ProductVariant
        SellablePackage → PackageContents → SupplierOfferSnapshot
        SourceClaim (original page, extracted raw text, observed date, reviewer)
        MechanicalInterface (unit, datum, revision, tolerance and qualification)
        GeometryAsset (licensed STEP/GLB, units, hash, coordinates, confidence)
      BuildRevision (frozen selection, user authorization, constraints)
        Fit & compatibility report
        Kit coverage, seller quantities and professional services
        Evidence-linked 2D/3D assembly
        Purchasing RESEARCH packet and receiving/learning checklist

Never derive one authority from another. An original manufacturer page may establish a published family spec but not confirm a physically fitted boot, exact purchased revision, live inventory or certified ski release. Mesh appearance cannot qualify CAD clearances.

A sport plugin should define its specific rider questions, equipment slots, interfaces, fit rules and service/skill expectations. Stable variant/package/offer/geometry/claims/revisions should be reusable across all sports. Changes to a model-year/size must invalidate dependent geometry, source, offer, assembly and compatibility receipts.

## Product experience to ship

1. **Goals first:** sport, terrain, ability, duration/range, budget, safety/maintenance preferences and rider fit. Personal body/foot measurements are optional and may be asymmetrical; never derive a release setting or safe retention from them alone.
2. **Explainable shortlist:** value, control/comfort and performance studies, only as many as available real compatible sources justify. Explain missing or rejected candidates rather than fabricating all three.
3. **Visual comparison:** selected variants in a shared 2D and orbitable 3D viewer; boot/binding, stance, wheels, axle/brake and accessory differences, with clear source and physical-measurement status.
4. **Part decisions:** reveal exact manufacturer evidence, size/revision, seller package unit/contents, required tools/service and review holds per assembly element.
5. **Repair mode:** propose a swap with the constraint diff and invalidated earlier assertions; require user acceptance, never silently change a brake, sole norm or safety-critical component.
6. **Ordering research packet:** classify every required line as included kit content, independently sourced exact package, missing/unknown, or professional service. No made-up tax, stock, delivery or all-in sum.
7. **Build learning and receiving:** source-linked maker instructions, safe non-structural printing recommendations, parts inspections and stage gates; no generic DIY ski release or battery construction authorizations.

## Gated development plan

### G0: Release integration, immediate

Finish #97 manually on the exact #114 commit: inspect artifacts, successful 3D orbit, real touch, keyboard/screen reader, print and source links. Merge #110 → #114 sequentially after updated-base CI, preserving a working main after every PR. Avoid a sixth deep feature branch before this is accomplished.

Exit: source-bound research picker is actually reachable from main, human-reviewed, keyboard/mobile usable and correctly marked non-orderable.

### G1: Exact package and parts closure for one manual longboard

Use the Loaded Tangent 85/105 mm published setups. Resolve exact seller option identity and date-bounded quote only from permitted reviewed sources; separate complete-kit advertised contents from verified received contents. Decompose truck/wheel/bearing/bracket/fastener as individually explodable child hypotheses and reconcile physically required counts to the package sold.

Exit: all required assembly lines classified, no double-order, maker citations for inclusion claims, exact unit count when supported, missing and service items explicit. No false current-stock or checkout claim.

### G2: Shared source/variant/offer/interface graph

Introduce durable typed IDs, source claims and revision invalidation rules. Read-only parity adapters protect existing Board Builder. Add explicit physical interface edges and negative tests for wrong boot retention, ski sole/binding reference, brake/axle/hub, package double-counting and stale/incomplete seller evidence.

Exit: deterministic explanation of required, incompatible and UNKNOWN components with no positive physical-approval shortcut.

### G3: Measured/revision-locked 3D and accessible assembly learning

Accept maker-authorized CAD or clearly marked measured bounding models with mm coordinates, mounting datums, hash/license and geometric completeness status. Animate package-child disassembly, component selection, hardware and tools, and professional-service stopping points. Test successful WebGL, camera presets, GPU/device variation and source-to-render identity.

Exit: one complete longboard explodes to every claimed part while refusing to assert fabricated physical interfaces; novice can identify actual assembly dependencies.

### G4: Personalized optimization, controlled edits

Formal hard vs soft constraints, a feasible Pareto shortlist (1–3 only when truly distinct), budget UNKNOWN vs known, rider-fit and skill constraints, user review/undo. Use two independent foot measurements and boot size charts when relevant. Do not infer ski release settings.

Exit: test profiles and conversational edits produce traceable decisions and no hidden profile mutation.

### G5: Broaden sports one by one

Add touring ski, splitboard, surfboard, bicycle and shelter only with a complete sourced example per domain, real package quantities, professional service taxonomies, domain-specific negative compatibility fixtures and usable assembly visualizations. No taxonomy-only domain marketed as operational.

Exit: every active domain has meaningful, tested end-to-end depth.

## Parallel program: actual X1 off-road electric board

The original X1 is **physical hardware development**, not simply another generative build card. Maintain issues #25 (chassis release), #2 (fit rig) and #37 (armor) as independent engineering gates.

- Begin with actual full-scale deck/stance cardboard and repeated stance/step-off comparison. Preserve rider-specific left/right footplate options without assuming body scans establish balance or load distribution.
- Source, inspect and validate one inert load-cell/ADC zone and test known masses/offset loads before assembling the four-zone fit rig.
- Choose a real independent braking path before propulsion. Measure axle/hub/rotor and steering sweep with inert parts. Never rely on a manufacturer-incompatible CNC brake assembly or unqualified 3D-printed safety mount.
- Protect critical components using sacrificial skid/armor with measured clearance, replaceable parts, positive retention and inert impact trials, accounting for dirt, roots, brush, water and deck flex.
- Keep long-range battery/BMS/charger, thermal, crash and charging designs as unqualified simulation until qualified electrical professionals and independent measurements support assembly/operation.
- No first powered trial until rider fit, structural path, independent braking, electronics, protective equipment and emergency stop behavior have been physically reviewed and demonstrated.

## Measurement dashboard

| Area | Leading indicator, not vanity metric |
| --- | --- |
| User success | A new user correctly identifies missing parts and unsafe unknowns without believing the model is certified |
| Source | Required lines with exact maker/seller revision, original claim, dated source and package evidence |
| Compatibility | UNKNOWN/conflict/reference/verified rates and attempted unsafe promotions blocked |
| Assembly | Required items closed through verified included packages / received contents / pro service / missing |
| CAD | Measured source/revision-locked part geometry, datum coverage and independently verified mates |
| Delivery | Full CI on updated main, human 3D/keyboard/touch/print findings, baseline TTI and memory |
| Hardware | Received/inspected, calibrated, repeated rider-fit, brake test and power commissioning receipts |

**Immediate next work order:** land the confirmed seller-family regression + readiness audit, complete full final-head CI, obtain actual human review for #114, then merge the existing dependency stack before implementing G1 on clean main. Software release is separate from physical purchasing, ski-binding service and any battery-powered build authority.
