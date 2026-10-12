# CAD Twin v6: official part geometry acquisition

**Scope:** Draft PR #114, source leads and requests only. Zero source-authenticated Tangent/Paris/Orangatang/Loaded structural GLBs or STEP models have been acquired for the seven complete-kit categories. No authorization for manufacturing or buying.

## Why this exists

A printable part, manufacturer photo, a DIY cutting drawing, or a parametric box is not the same as an exact-revision manufacturer CAD solid. The existing metric sandbox and capture campaign can only become a defensible physical digital twin after geometry provenance and measured mounting interfaces arrive.

The CAD laboratory now has an opt-in **Source acquisition** panel that pulls an exact-kit seven-part leadbook from `catalog/outdoor_cad_source_leads.v1.json`. Each entry names the manufacturer, links only to its official site, lists the missing revision-specific 3D geometry/datums and identifies any separately pinned but unqualified GLB candidate. The user can export a machine-readable lead report or download ready-to-review **manufacturer inquiry drafts** grouped into three companies (Loaded, Paris Truck Co, Orangatang). No automatic emails are sent, no license is inferred, and no child purchase lines are added.

### Exact model request and provenance boundary

| Role | Manufacturer reference | What is still required |
| --- | --- | --- |
| Tangent deck | [Loaded deck with brackets](https://www.loadedboards.com/products/tangent-deck-with-brackets) | Actual structural deck CAD, bracket attachment surfaces/holes and explicit preview reuse permission |
| Zee brackets | [Loaded Zee Bracket](https://www.loadedboards.com/products/zee-bracket) | Structural load-bearing bracket CAD and right/left instances; actual deck/baseplate mating datums |
| Trucks | [Paris V3 150 mm](https://www.paristruckco.com/products/v3-150mm-50-polished) | Confirm shipping **V2 vs V3** before importing geometry; complete baseplate/pivot/hanger/axle 3D data |
| Dad Bod 105 wheel | [Orangatang Dad Bod](https://www.orangatangwheels.com/products/dad-bod-105mm-longboard-wheel) | Full wheel profile, center offsets, core/bearing-seat measurements, durometer and revision |
| Caguama 85 wheel | [Orangatang Caguama](https://www.orangatangwheels.com/products/caguama-85mm-longboard-wheel) | Separate exact wheel variant, hub/seat geometry and orientation |
| Bearings | [Loaded replacement parts](https://www.loadedboards.com/collections/parts) | Actual JEHU V2 inner/outer race dimensions and hardware revision |
| Deck hardware | [Loaded countersunk hardware](https://www.loadedboards.com/products/countersunk-hardware) | Actual 1.25-inch fastener spec and received count |
| Truck hardware | [Loaded button head hardware](https://www.loadedboards.com/products/button-head-hardware) | Actual 1-inch fastener spec, washers and received count |

The leadbook has seven assembly roles for *each* selected 85/105 mm kit variant, not eight purchase lines. Only one of the two wheel reference pages is active at a time. Maker site pages are **research leads**, not proof that publicly licensed 3D geometry exists.

### Explicit source exclusion policy

- [Loaded Zee Bracket DIY cutting template](https://cdn.shopify.com/s/files/1/0092/1085/5524/files/Loaded-Zee-Bracket-template.pdf?v=1688582078): manufacturer-published PDF stencil, not a structural 3D model, calibrated Tangent deck hole coordinates or manufacturing signoff.
- [Optional 3D-printable tail nub STL on Loaded's Zee Bracket page](https://www.loadedboards.com/products/zee-bracket): offered as a free optional accessory. **It is not the structural Zee Bracket** and is not counted as one of the seven main categories. A public download statement is not a blanket license to redistribute the model from this platform.

Both excluded artifacts are represented as research links with explicit `exact_structural_part_cad: false`, `redistribution_authorized: false` and `qualifies_seven_component_models: false`. No mirrored copies of any manufacturer file are shipped.

### Acquisition procedure

1. In the Parts Picker choose the exact **105 mm Dad Bod** or **85 mm Caguama** complete Tangent research reference.
2. Open **CAD asset laboratory → Source acquisition**. Follow the seven first-party source pages and note that all roles still require licensed exact-revision CAD.
3. Choose **Download manufacturer request messages**; inspect and send your preferred inquiries through your own email or manufacturer support channel. Ask specifically for STEP (or GLB), revision, units, allowable preview/distribution rights, geometric mounting datums, and whether the source matches the current shipped part.
4. If a manufacturer approves reuse, preserve written permission and original source digest; convert STEP through `tools/convert_cad_step_to_glb.py` and stage with `tools/stage_cad_asset.mjs` plus the matching SHA-256 conversion receipt.
5. Inspect candidate GLBs in the **isolated** viewer, then collect independent mounting measurements using [CAD Twin v5 field campaign](browser_cad_capture_campaign_v5.md). Neither one promotes physical engineering authority on its own.
6. Perform a separate reviewed, revision-specific real assembly and tolerance/dynamic clearance analysis. Resolve seller truck V2/V3 discrepancy and actual received components before any physical fabrication or checkout gate can change.

### Pinned CAD receipt verification

A registered candidate is not shown in the isolated GLB inspector merely because its manifest names a source or declares millimeters. On **Inspect pinned GLB**, the browser now:

1. Fetches only the pinned content-addressed local `/assets/cad/<GLB_SHA>.glb` and its matching `.conversion.json` receipt (32 KB maximum).
2. Computes and checks **two independent SHA-256 values** against the registry, compares the STEP source digest to the receipt, and validates the explicit `mm → m` conversion and limited source/model extents.
3. Runs bounded GLB preflight, decodes the actual mesh in the isolated WebGL viewport, and cross-checks **its rendered scene bounding extents** against the conversion receipt's sorted glTF-meter envelope within declared tessellation tolerance.
4. Hides and releases the candidate viewer if the receipt is missing, either digest differs, the model is malformed or its rendered dimensions conflict with the receipt. The seven-component primary study stays rendered and no new order lines appear.

This is **reproducible file integrity**, not verification that the manufacturer authored the STEP, that every CAD surface is accurate, or that the physical assembly fits. We still need independent revision verification and actual measured mounting datums. Locally uploaded, unregistered GLBs remain isolated previews with unknown physical scale and never pass through source-backed intake.

The Chromium test exercises the real pinned-file flow with intercept-injected **synthetic** geometry and valid receipts, then deliberately tampers with the receipt to prove a fail-closed viewer. The regular registry remains empty and no synthetic test file is published to users.

### Regression coverage

```bash
node --test tests/js/test_outdoor_cad_source_acquisition.mjs
node tests/browser/parts_picker_smoke.mjs
```

The validator rejects forged checkout/reuse/geometry claims, fake official-looking domains, duplicate kit mappings, wrong wheel source variant, and efforts to relabel optional CAD or DIY drawings as approved structural geometry. Chromium verifies correct maker links, seven role counts, source exports, manufacturer inquiry text, and the 105-to-85 kit change. The main assembled procedural board and one-parent maker package remain unchanged.
