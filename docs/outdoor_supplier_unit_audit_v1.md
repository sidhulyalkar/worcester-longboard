# Outdoor Parts Picker v1.2: maker-code, package-unit and source-freshness audit

**Historical manufacturer evidence only. No live offers, current stock, basket checkout, physical-fit permission, ski release or fabrication instructions.**

## Entry points

```sh
python tools/serve_board_platform.py
# http://127.0.0.1:8000/builder/parts.html
```

The existing part selector, source/size-specific 2D and opt-in 3D exploded studies and CSV/JSON research exports are preserved. Below the original order worklist, a new section, **Why this exact quantity?**, shows the exact maker-listed part code, reference package contents, **individual items required** versus items per **manufacturer seller package**, indicative pack count, and source hold. A new JSON evidence export preserves the dated maker-unit audit.

### Product identity and what is *not* a SKU

The original `catalog/outdoor_parts_picker.v1.json` stores research family/size variants. The `manufacturer_sku` field on each remains null. The new independent `catalog/outdoor_supplier_observations.v1.json` stores manually reviewed **manufacturer listing observations** with their public part code, selected variant reference, URL, price scope, package-count text and date.

A **model-level or family code is never assumed to identify an exact-size order option**:

- **MBS 11303**: Comp 95 Silver Hex 95 cm maker listing. Research target **1 deck**, maker page shows **1 deck**; historical example 1 seller package, physical hardware/interface still held.
- **MBS 12300**: Matrix III 12×400 mm black **each**. Research target 2 individual trucks; maker page lists 1 per seller unit, so historical example is **2 separate packages**.
- **MBS 14051**: F5 **pair**. Research target 2 individual bindings; maker page lists both in one seller package, so historical example **1 package**, not two.
- **MBS 12307**: Matrix III **CNC** 420 mm black each. Explicit manufacturer warning says **not compatible with MBS Brake Systems**, now a negative cross-part rule. 12307 must never silently substitute for 400 mm or standard non-CNC truck variants.
- **Loaded Tangent Standard Complete**: published 105 mm Dad Bod package contents and $424 family/setup reference. No independent maker SKU for the selected finish/setup; it stays on **exact option ID hold**, even though its complete-kit contents are advertised.
- **Burton Good Company 145**: board family/color code 27WIN-235951 is *not* a proven unique 145 cm sellable SKU. The size-specific order identity remains **on hold**.
- **Atomic Bent 90 157**: AA0030956+ is a family code, not a confirmed 157 cm sellable SKU; actual seller pair count and 157 cm purchase unit are still unknown.

**Selection and quantity are separate claims.** One selected manufacturer family does not establish a buyable line. Even historically supported reference counts are *not* allowed to become `qualified_supplier_order_lines`, and the final `actual_checkout_total` stays null. All sample prices are original manufacturer listing observations reviewed October 10, 2026, not live snapshots; historical partial totals exclude unknown items, shipping, taxes, professional mounting/inspection, and other required parts.

## Data contracts

`builder/offer_qualification.mjs` performs:

- **Registry identity validation:** all observations link back to a known catalog family and *selected variant* and a verified manufacturer-domain source URL, not an unrecognized retailer or invented domain.
- **Evidence scope validation:** item-specific examples require a listed maker code, typed seller-pack count and original-page price. Model-family-only examples are not counted as exact variants, no matter how persuasive their marketing photo.
- **Assembly-unit contract:** required individual items and maker seller-package items are typed `deck | truck | individual_binding | snowboard | complete_board | individual_ski`. Never reuse historical catalog `price.qty` as a cart quantity.
- **Expiry:** source observation within 30 days of the UTC audit date (inclusive) or else status `EXPIRED_OR_FUTURE_LISTING`; stale rows cannot produce package counts or historical partial amounts.
- **Conflicting interfaces:** known `MBS_CNC_420_BRAKE_CONFLICT` blocks **all** reference-pack calculations for that selected configuration. Missing documentation is never a compatible conclusion.
- **Source-bounded math:** only `PUBLISHED_MODEL_OPTION_CODE` examples can compute `ceil(assembly_items / seller_unit_items)`. These are **historical pack examples**, not live orders.
- **Cost boundaries:** historical reference subtotals can appear *per currency* when individual offer/pack evidence is present. Never compute a cross-currency sum, assume taxes/stock, promote a full bill-of-material total, or issue checkout/fabrication/power/release permission.

The validator checks that the maker page host matches the configured maker's host, but it cannot independently authenticate a page's contents. A real refresh or variant certification would require dated retained seller evidence and human review; arbitrary user-generated SKU strings never qualify the assembly.

## Assembly graph and 3D

The existing component identities and assembly graph are unchanged. A selected MBS variant's **published overall truck width** now adjusts the truck proxy's visible scale in the 3D Atlas; this is a source-reference silhouette only, not a derived mate coordinate, axle interface, brake clearance or replacement CAD part. The 3D exploded view still intentionally refuses to accept `exact_variant_verified=true` or physical-authority promotion without separate qualified CAD contracts.

## Test and QA

```sh
node --check builder/offer_qualification.mjs
node --test tests/js/test_outdoor_supplier_audit.mjs
node --test tests/js/test_outdoor_parts_picker.mjs
python -m pytest -q tests/test_outdoor_parts_picker.py
```

CI includes these with the existing physical-authority and model regression suite. Tests cover each-vs-pair math, historical exact-option holds, seller host/model/variant tampering, invalid units, stale/future observation dates, known CNC brake incompatibility, CSV research export authority, and graph safety. Manual browser/mobile/keyboard/print QA remains an **uncompleted requirement** under issue #97.

## Next gated stages

1. Reviewed exact seller **size/color revision IDs**, shipping-region-specific offers, price currency, stock expiry and order pack reconciliation. A live seller offer must be distinct from a maker research snapshot and have a refresh timestamp.
2. Source-bound normalized materials/geometry data, measured accessory CAD meshes, verified mount datums and geometry/tolerance integrity receipts. Add a model-specific boot/foot fit review with *two independent measurements* before offering recommendations.
3. Diverse **three-build** composition per sport with genuine constraints; each trade-off should show unresolved fit, dimensions, supplier units, exclusions and service requirements rather than quietly constructing a complete “approved” kit.
4. Human browser visual QA and independent mechanical safety approval before reconsidering any ordering workflow. Ski bindings must always retain professional release-service requirements.

The new observation catalog is intentionally small, evidence-dense and conservative instead of scraping thousands of ambiguous listings with bogus SKU matches.
