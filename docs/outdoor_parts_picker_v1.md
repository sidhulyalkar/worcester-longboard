# Outdoor Parts Picker v1: maker-backed option explorer and assembly ordering worklist

**Scope:** `EVIDENCE_AWARE_OUTDOOR_PARTS_RESEARCH_NO_CHECKOUT`. This page is a *catalog research workspace*, not a retailer checkout, verified bill of materials, mechanical release, 3D fabrication drawing, ski release-setting device, electrical commissioning tool or automated purchasing agent.

## Experience

```sh
python tools/serve_board_platform.py
# http://127.0.0.1:8000/builder/parts.html
```

Select alpine skis, snowboards, longboards or mountainboards. For each assembly slot, choose an official manufacturer reference family and a published size/option label. A source link and a detailed inclusion hypothesis appear in the part card. The graph redraws the chosen parts and unresolved placeholders; orbit in opt-in **3D**, choose a camera preset or retain the source-linked **SVG**. Ski boots are shown as two distinct **procedural shell/cuff silhouettes**, one over each ski. These represent an assembly relationship only, not scanned boot geometry, bindings or a mechanically fitting footprint. Specific documented ski/board length and waist ratios can alter visual proportions without converting proxy shapes into dimensionally accurate CAD.

The worklist tracks required categories, selected manufacturer family, missing references, included-contents hypotheses, foot-size/mounting-family conflicts, professional service holds and exact seller quantity `null`. CSV and JSON are **research exports**, not executable orders or approved assembly instructions.

The **demo** button loads a non-authoritative manufacturer reference bundle. It does **not** check stock, prices or live part compatibility.

## Inventory and evidence

Canonical family seed: `catalog/outdoor_parts_picker.v1.json`.

- 9 taxonomy domains consistent with `catalog/outdoor_equipment_domains.v0.json`.
- 4 active maker-referenced research workflows: alpine ski, snowboard, longboard, mountainboard.
- 23 manufacturer product families and 37 source-publication size/option labels in the initial seed, plus 18 brand and specialist retailer directory links. Different seller pack quantities, exact SKU/barcode/revision IDs and actual received kit contents remain **unverified**.
- The other 5 domains, **touring ski, splitboard, surfboard, bicycle and camping shelter**, remain schema/directory exploration only. **They are not operational Parts Picker build recipes yet.** Do not imply full coverage of all sports.
- Manufacturer links are primary *specification/evidence* references; retailer links are supplier discovery. Supplier reputation, authorized-dealer status, stock, price, local taxes, return eligibility, shipping constraints and installation services must be verified for the exact chosen revision and region.

### Initial maker catalog evidence

| Brand | Family / role | Source basis | Independent decision still needed |
| --- | --- | --- | --- |
| Atomic | Bent 90 lengths 157/166/175/184 cm | Official size/dimensions table | Exact length/SKU, pair count, compatible binding/brake and professional mount |
| Salomon | QST 94 Black 156/164/172/180/188 cm | Official 94 mm waist and **skis-only** listing | Bindings, brake, fitted boots, length and professional service |
| Tyrolia | GW adult and MN binding **family** references | Maker compatibility page | Actual binding model/revision, AFD, brake choice and binding service |
| Salomon | S/Pro Alpha C BOA 130 / 100 boot families | Maker product text; C BOA 130 published alpine-sole factory configuration | Independently fit each foot; inspect actual sole, BSL and size |
| Burton | Good Company Camber 2027 | Channel and size-dependent length/waist table | Board width/stance/boot overhang, exact graphics/revision and mounting hardware |
| Burton | Step On Re:Flex 2027; Mission Re:Flex study | Maker mounting family and Step On gender/size guide | Exact compatible Step On boot model/size, discs and fasteners |
| Loaded | Tangent 105 mm Dad Bod and 85 mm Caguama completes; Tangent deck-with-brackets | Separate manufacturer **complete** and **deck + brackets** offerings | Avoid duplicated parts; verify shipped package and choice |
| MBS | Comp 95, Matrix III, Rockstar, F5, brake system, electric family | Manufacturer parts directory and Agent description | Per-item vs paired quantities, axle/hub/brake compatibility, electrical certification |

### Source versus order entity design

A selected product family + size label is not an exact stocked offer. Worklist fields deliberately preserve:

- `variant_id`: internal *reference option* key. Not an official manufacturer's sku.
- `manufacturer_sku`: `null` until maker-exact revision evidence.
- `exact_seller_order_units`: `null` until a dated seller offer identifies exact pack contents and quantity.
- `expected_assembly_amount`: descriptive worklist requirement. Never treated as an order quantity.
- `physical_fit_verified`, `checkout_eligible`, `supplier_order_unit_verified`: all **false**.
- `source_url`: reviewed original maker page, not a live order or inventory guarantee.

Complete kits and individual component bundles are mutually exclusive in the longboard selection state. Kit inclusion is an **advertised contents** review hypothesis. No deduction from part counts or budget is allowed until seller pack contents/received items have been reconciled.

### Compatibility logic

- Snowboard board mount family and binding family reuse `evaluateSnowboardMountReference`. A matching Channel/Re:Flex reference remains **REVIEW_REQUIRED**, not safe installation. Step On binding/boot family conflicts explicitly fail closed. Burton men's Step On chart Mondo *boot* bands may flag rider foot measurements for review, but measured foot length does not automatically become a correctly sized boot.
- Ski boots and bindings are compared **only at published sole norm family level** (ISO 5355, ISO 23223, ISO 9523), and a recognized overlap remains **REVIEW_REQUIRED**. Individual boot soles, BSL, binding revision, boot category A/C, brake dimensions/clearance, mounting/adjustment and mechanical release testing remain unqualified. Tyrolia's official guidance explicitly requires technician adjustments in relevant cases.
- **No automatic DIN/Z-value computation or ski-binding mounting instructions.** Use a qualified shop for mounting, interface inspection, release adjustment and testing.
- Mountainboard wheel/axle, brake, steer and electric systems retain the original X1 authority restrictions. No printed safety-critical substitute is released.

## Respectful source monitoring, not indiscriminate scraping

The initial reference seed was manually curated from pages publicly displayed on original manufacturer sites as of 2026-10-10. The scanner is an *opt-in, bounded source-monitoring tool*, not a production scraper that self-publishes vendor assertions:

```sh
# Offline manifest of selected existing source URLs; does not touch the web
python tools/scan_outdoor_parts_sources.py --limit 5 --out /tmp/outdoor-source-plan.json

# Only if internet access is available and the use respects the site's terms:
python tools/scan_outdoor_parts_sources.py --fetch --limit 3 --out /tmp/outdoor-source-check.json
```

It uses HTTPS URLs from the reviewed manufacturer seed, respects `robots.txt` with a conservative unavailable/disallow hold, limits page size and fetch delays to at least 2 s per maker host, sets explicit timeouts, and rejects off-origin redirects and non-HTML pages. It extracts only page title/description, source fingerprint, ETag/Last-Modified and fetch outcome for independent review. It **does not** infer a product's model revision, boot compatibility, price, stock or cart readiness from arbitrary HTML; it does not copy complete catalog webpages, evade anti-bot restrictions, or store credentials.

**Future ingestion gateway**, *only after provider permission/feeds and validation*: approved APIs/feeds -> raw dated source hash/quote -> versioned family/variant normalization -> unit/price/currency/ship-region parsing -> primary manufacturer interface rule validation -> overlap/kit quantity audit -> human approval -> candidate source state. The old X1 physical release and receiving ledger remain independent and unchanged.

## Visualization and printable parts

All procedurally generated ski, boot, binding, wheel and deck meshes remain unscaled proxies. Published dimensions may inform visible length/width ratios, **not mate coordinates**. Exact-size CAD work requires a per-part revision hash, manufacturer licensed CAD/STEP/GLB or independently measured point clouds, installation datum frames, uncertainty, model units in mm and collisions/tolerances verified by an engineer. No manufacturer renders or CAD files were scraped or republished.

3D printing: non-structural storage stands, visual models and accessories can be investigated with material, UV, temperature, load and attachment constraints reviewed. Generic consumer FDM prints are **not** a replacement for ski bindings/release systems, boot retention, brake-critical parts, truck axles or battery and charging protection. Drill jigs and mounting templates for alpine release bindings remain **display-only**.

## Validation

```sh
node --test tests/js/test_outdoor_parts_picker.mjs
python -m pytest -q tests/test_outdoor_parts_picker.py
node --check builder/parts_picker_engine.mjs
node --check builder/parts_picker_app.mjs
python tools/scan_outdoor_parts_sources.py --limit 3
```

CI adds these to the existing Board Builder engine/physical safety regression set. Initial static/engine tests do **not** substitute for manual browser review. Verify 1440/1280/768/390/375 widths, touch/orbit, keyboard tree, 2D↔3D fallback, no network/CDN, print, CSV injection safety and source links. Issue #97 remains open.

## Next release criteria

1. Exact size and manufacturer revision tables, binding/brake product-specific accepted norms, separate left/right boot shell/sole evidence, known shipped quantities.
2. Dated **offer snapshots** with SKU, seller pack count, currency, shipping region, taxes/return caveats, package overcount review, inventory refresh and expiry. Only then compute supplier order counts, sums and compare *actual price totals*.
3. A constrained, user-reviewable solver producing at least three genuinely distinct complete systems per domain without guessing fit or elevating professional approval.
4. Manufacturer-authorized dimensional CAD with separately qualified mate transforms, geometry integrity receipts, boot fit and accessible 3D inspection.
5. More sport-specific slots and true product variants for splitboard, touring ski, surfboard, bicycle and camping shelter.
