# Outdoor Parts Picker v1.3: retail setup comparison and three research configurations

## Status

**Research only, not a shopping cart or qualified assembly.** `/builder/parts.html` now has three per-sport configurable research alternatives and manufacturer-evidence-led retail comparison for matched published product setups. This is stacked on v1.2 unit auditing. All source units, exact checkout size identities, hardware/boot fit, mounting and electrical authorities remain independent review gates. No new physical or buying approvals are granted.

## What actually changed

- `catalog/outdoor_retail_comparisons.v1.json`: six dated original seller webpage observations (October 10, 2026), with two **matched** Loaded Tangent Standard 105 mm Dad Bod 77a complete references at **USD 424** (Loaded Boards and Skates USA), two matched Caguama 85 mm 80a complete references at **USD 364**, and two **intentionally unmatchable** SkiEssentials 2026 Atomic Bent 90 (skis only `AA0030696`) versus skis-with-Marker-Squire bindings (`AA0030696K`). That SkiEssentials seller family is not the same as Atomic's referenced `AA0030956+` maker family. No ski offer is assigned to an exact selected 157 cm reference.
- `catalog/outdoor_build_studies.v1.json`: exactly three intentionally distinct candidate reference configurations for **alpine ski**, **snowboard**, **longboard**, and **mountainboard** (12 total). Each one has explicit source-bound selected variant IDs, intent, missing components and review notes. Every configuration is **unqualified**; no safe auto-pairing or size recommendations are asserted.
- `builder/retail_build_comparison.mjs`: fail-closed pure JavaScript engine, validates different sellers' HTTPS hosts, scope, matching maker setup signatures, the same selected option and package kind. Refuses mismatched sizes/kits, bogus SKUs, stock claims, invalid prices, duplicate listing identities and weakened 30-day freshness gates. A historical price range is only displayed if **two independent merchants match the same named published setup**, not merely the family name. Zero claims of actual checkout SKU, inventory, shipping, tax, returns or current delivery.
- Three-card comparison UI: pick a preset and it loads the same selected source-bound assembly graph, 2D/SVG or opt-in Three.js viewer. Its report exposes incomplete requirements, findings, and historical *partial* maker-unit costs; any rider mass comparison only flags official snowboard weight-range mismatches, not boot or board sizing approvals. The intent labels are educational.
- Selected loaded complete 105 mm versus 85 mm variants now show different four-wheel radius proxies in the same interactive 3D platform. Published radius is used as an illustrative ratio, not validated wheel clearance, truck axle geometry, suspension or fabricatable CAD. Display remains source-linked and clearly unqualified.
- New JS + Python quality gates; existing mountainboard CNC-420/brake exclusion, ski binding professional release requirements and 3D source-authority restrictions remain intact.

### UI quickstart

```sh
git fetch origin
git switch feat/equipment-study-comparison-and-retail-evidence-v13
python tools/serve_board_platform.py
# http://127.0.0.1:8000/builder/parts.html
```

Select a sport, compare three cards, click **Inspect this configuration**, toggle orbitable **3D**, then read **Compare published seller setups** and **Why this exact quantity?** The full research worklist may be exported as JSON/CSV; no consumer checkout is possible.

### Testing

```sh
node --check builder/retail_build_comparison.mjs
node --test tests/js/test_outdoor_retail_build_comparisons.mjs
node --test tests/js/test_outdoor_supplier_audit.mjs
python -m pytest -q tests/test_outdoor_parts_picker.py
```

Run full CI and manually review 375, 390, 768, 1280, 1440 widths; touch, keyboard, 2D/3D offline fallback, printed offer evidence, design switching, source links, and on-device 3D camera geometry. A successful JS test does not establish browser/WebGL usability.

## Evidentiary and next-stage architecture

1. **Seller offer identity:** Currently this is matching **named maker-configured setups** from page text, not a confirmed immutable, checked-out UPC/EAN/manufacturer SKU. Before a real seller quote: document selected size/color, manufacturer model-year revision, retailer seller SKU, shipped pack contents, currency, regional taxes, returns, shipping and expiry. Do not promote claims through page-title similarity.
2. **Assemblies:** `buildPickerStudy` produces only proxy geometry. Exact assemblies require licensed source CAD or measured shell/boot/truck meshes, units, stable local datum axes, mate transforms, safe load interface checks, independently verified clearance and release service by trained providers.
3. **Rider customization:** Use independently measured left/right foot mondo and actual boot-specific shell/sole/BSL information, boot try-on and exact binding capacity. Body mass and length alone do not prescribe release values or establish physical fit.
4. **3D printing:** Noncritical accessories can move through explicit design/material/load/print orientation/reliability validation. Generic consumer printed ski-binding components, trucks, brake levers and battery protection stay blocked.
5. **Broader equipment verticals:** More manufacturer-verified catalogs, actual component quantities, and 3D interface formats for touring ski, splitboard, surf, bicycles and camping equipment remain future work; their taxonomy does not imply orderability.

The seller-comparison engine is deliberately small and strict. Large indiscriminate scrape catalogs are prone to conflating listings, misleading availability and unsafe mechanically unqualified assemblies.
