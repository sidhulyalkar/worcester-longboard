# Exploded Assembly Atlas v1: conceptual assembly graph and SVG viewer

**Planning visualization only.** The diagrams are not installation or fabrication instructions. Actual dimensions, source-matched fasteners, seller order quantities, ski binding release, fit, electrical safety and physical qualification remain unresolved.

## Experience

The selected mountainboard's Source-aware BOM now has an **Inside the build** section:

- Semantic exploded SVG: platform, mounting/steering, wheels/terrain contact, rider interface, brake/drive, electronics and accessories
- Assembly separation slider, from conceptual overview to separated components
- Grouped accessible assembly tree, linked diagram selection and component source panel
- Source and SKU text, inclusion hypotheses, uncertain quantities and revision/physical fit holds
- SVG and JSON export, plus a sport selector
- Mountainboard: actual current candidate/component references
- Longboard, snowboard, alpine ski, splitboard, surfboard: explicit UNSOURCED concept references, not buyable products, mechanically verified builds or selected fit recommendations

All sport examples are illustrative. They do not grant mount, binding-release, assembly or vendor checkout authority.

## Run

    python tools/serve_board_platform.py

Open http://127.0.0.1:8000/builder/ . Select a generated board and scroll below the BOM to Inside the build. Select a system, change explosion separation, click a grouped component and inspect its evidence.

## Architecture and deterministic semantics

- Source contract: catalog/outdoor_assembly_recipes.v1.json
- JavaScript graph: builder/assembly_graph.mjs
- Python graph: configurator/assembly_graph.py
- SVG renderer: builder/exploded_renderer.mjs
- Parity: tools/compare_exploded_assemblies.py

The source-bound assembly graph preserves all component IDs and original BOM ordering. Unknown catalog component IDs or ambiguous assembly roles throw errors rather than being assigned to a safe-looking default group.

For other sport examples, any deviation from the versioned canonical UNSOURCED recipe throws. A diagram cannot convert an inferred or user-supplied component into a validated manufacturer model.

Group item counts mean numbers of **catalog reference lines**, not amounts needed for assembly or supplier packs. All real assembly and seller quantities remain null. The historical catalog price multiplier is never substituted for a component quantity.

Donor packages and their possible included components remain conservative research hypotheses. A source ID or SKU mismatch removes the component-equivalence mapping and flags stale donor contents. The platform never subtracts guessed bundled items from known BOM subtotal.

**Geometry:** separation vectors and SVG silhouettes are unitless illustrative proxies. No exact mounting placement, tolerance, axle spacing, screw length, ski brake clearance or wiring dimensions can be inferred from the image.

**Safety:** physical, mounting and ski binding release statuses stay NOT_QUALIFIED. All procurement, fabrication, charging and powered-operation authority fields remain false. Ski binding fit and release require a qualified professional.

## Tests

    node --test tests/js/test_board_exploded_assembly.mjs
    python -m pytest -q tests/test_board_exploded_assembly.py
    python tools/validate_outdoor_assembly_recipes.py
    python tools/compare_exploded_assemblies.py

CI tests all current generated mountainboard candidates and all five cross-sport concepts, checks against BOM duplication and source tampering, tests SVG escaping, and requires exact Python/JS assembly graph parity. All existing Board Builder, physical authority, firmware and CAD regressions remain in place.

## Next milestones

1. Manual browser/mobile/keyboard/print/SVG interaction QA under issue #97.
2. True physical subassembly edges only after exact manufacturer revisions and independent measurements.
3. Real source-reviewed longboard/snowboard product and binding/adapter pilots with typed negative compatibility rules.
4. Optional 3D exploded scene for geometries whose provenance is clear.

The rendering layer generalizes to more sports now. Multi-sport purchasing and fit qualification are not currently supported.
