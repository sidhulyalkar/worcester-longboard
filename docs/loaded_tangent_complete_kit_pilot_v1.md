> **Visual update, October 11:** The complete-kit pilot now projects seven manufacturer-advertised component categories into separately selectable/explodable SVG and 3D visual proxies. This replaces the earlier single composite longboard illustration while preserving **one seller package, zero child purchases, zero measured mates, zero physically verified contents**. See [seven-part visual design](loaded_complete_kit_seven_part_visual_v1.md). These shapes still are not measured or approved CAD.

# Loaded Tangent complete-kit research pilot: inclusion claims and revision conflict

**Research reviewed October 11, 2026.** Source pages are dated reference evidence, not a live seller checkout or received physical kit.

## Why this pilot matters

The existing Parts Picker had matched manufacturer and retailer listings on the name of the complete wheel setup. However, on October 11:

- [Loaded Tangent Standard Complete](https://www.loadedboards.com/products/tangent-longboard-skateboard) advertises Paris **V3** 150 mm 50° polished trucks for the 105 mm Dad Bod 77a complete, Loaded Zee Brackets, Jehu V2 bearings and Loaded 1.25 in deck / 1 in truck hardware sets.
- [Loaded Tangent Caguama Complete](https://www.loadedboards.com/products/tangent-caguama-complete) advertises Paris **V3** 150 mm 50° polished trucks for the 85 mm Caguama 80a complete, with the same named bracket/bearing/hardware families.
- [Skates USA Tangent Complete](https://www.skatesusa.com/collections/longboards/products/loaded-tangent-complete-longboard) describes Paris **V2** 150 mm 50° Raw trucks for named wheel options. Its listing therefore conflicts with the currently published Loaded maker kit contents. It may reflect an earlier listing, different stock, or stale text, and **we do not know which hardware would ship**.

Consequently **two similarly named historical listings are not equivalent sellable packages**. The retail engine now produces `INCLUSION_REVISION_CONFLICT_HOLD` with both seller sources displayed and **no historical "identical kit" price gap**. Both prices are historic page observations. A shared price or photograph does not resolve the underlying variant revision.

## Complete-kit assembly / seller package separation

An advertised complete is **one parent purchasing package** for research, not seven additional seller order lines. The following component categories are listed by Loaded as maker package inclusions. Numeric assembly counts are *structural expectations*, not original-page-confirmed seller unit counts.

| Child ID suffix | Maker-advertised component | Research assembly expectation | Actual received count |
| --- | --- | --- | --- |
| `deck` | Loaded Tangent deck | 1 deck | Unknown |
| `zee_brackets` | Loaded Zee Bracket system | 2 bracket pieces hypothesized | Unknown |
| `trucks` | Paris V3 150 mm 50° polished trucks | 2 trucks hypothesized | Unknown |
| `wheels` | Orangatang 105 mm Dad Bod **or** 85 mm Caguama, depending on selected setup | 4 wheels hypothesized | Unknown |
| `bearings` | Loaded Jehu V2 bearings | 8 bearings hypothesized | Unknown |
| `deck_hardware` | Countersunk 1.25 in deck hardware set | Exact bolt count unknown | Unknown |
| `truck_hardware` | Button-head 1 in truck hardware set | Exact bolt count unknown | Unknown |

The catalog source list does not independently establish axle washers, speed rings, nut revisions, bracket hardware quantity, service instructions, structural torque, or actual received items. No inferred sale units are permitted. Standalone hardware substitutions remain held until proven needed and compatible.

### Reproducible engine

- `catalog/outdoor_complete_kit_claims.v1.json` contains two maker-declared complete research packages, each with seven stable source-linked child IDs.
- `builder/complete_kit_closure.mjs` matches exactly one selected complete family to its kit and ensures maker-advertised contents never become separate purchase rows.
- It invalidates the old kit-child IDs when switching 85 mm ↔ 105 mm versions.
- It preserves every original seller's advertised Paris truck revision, blocks apparent equivalence, and exports `current_cart_total: null`, `actual_seller_unit_count: null`, `actual_received_units: null`, and `physical_connections_qualified: 0`.
- `/builder/parts.html` exposes the kit-closure table and a downloadable kit inclusion research JSON next to the historical source comparison. The existing 3D complete board remains a **single illustrative proxy**; individual child explosions require a later revision-specific geometry tranche.

### Verification before a purchase decision

1. Ask each seller to identify the actual installed truck model (V2 vs V3), finish, wheel option, color/durometer, bearings and manufacturer assembly/revision, with documentation for that exact sellable variant.
2. Confirm which fasteners and retainers are included, shipped unit count, and any adjustments needed for the named bracket/truck combination.
3. Review actual seller stock, returns, location, taxes, shipping, and delivered service options; none are currently established in this tool.
4. On physical receipt, inspect and photograph all components separately, compare against the maker page and original order invoice, and resolve manufacturer documentation discrepancies before claiming mechanical fit.
5. Only after supplier and physical evidence have been independently recorded may a distinct qualified receiving/assembly process proceed. The software **does not** authorize buying, fabrication, structural alterations or high-speed riding.

## Next milestones

The receiving ledger needs exact package contents, maker model revision and dimensions, evidence attachments, and independently qualified mounting geometry. The future measured assembly twin will show seven individually explodable child categories with a single parent kit purchasing identity, avoiding both phantom purchases and visually invented fasteners. This remains [issue #115](https://github.com/sidhulyalkar/worcester-longboard/issues/115), while [#116](https://github.com/sidhulyalkar/worcester-longboard/issues/116) will generalize the model.

No external retailer page was used as fabrication guidance; source URLs are for verifying equipment identity and published contents only.
