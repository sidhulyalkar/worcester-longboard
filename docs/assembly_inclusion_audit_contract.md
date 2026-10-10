# Board Builder v1.5: auditable package inclusions and order-unit unknowns

**Scope:** `NON_AUTHORITATIVE_ASSEMBLY_INCLUSION_AUDIT`. Nothing here is an orderable cart, a bill of verified exact quantities, a safe substitute, an assembly permit or a manufacturer manual.

## Why this exists

The catalog contains a real donor-first question: `DONOR-COMP95` names an included deck, Matrix III trucks, Rockstar II hubs, T1 pneumatic tires/tubes and F5 bindings, while the Board Builder catalog independently lists truck, hub, wheel and deck *reference entries*. These names cannot be assumed to refer to identical exact revisions or quantities, and simply summing every line of an edited BOM may count a donor's contents twice.

A separate registry, `catalog/board_package_inclusions.v1.json`, maps only **reference inclusion tokens** to **possible** catalog counterpart IDs. It is pinned to the donor's exact catalog snapshot and SKU text. `tools/validate_board_package_inclusions.py` checks that every token is covered, mapped IDs exist and the reference source snapshot has not changed unnoticed.

This is a deliberately non-authoritative inference layer, not an inventory of what anyone actually received. Registry changes require review.

## Contract

The package audit is included in every Build Passport produced using the full v1.5 catalog bundle, under `assembly_inventory_audit`. The standard Python and JavaScript generators both load the same registry, and the existing exact passport comparator covers every audit field.

- `package_claims` identifies selected donor packages and whether their reference source mapping is still bound to the dated catalog record.
- `overlap_worklist` reports selected standalone components that **might** duplicate an included donor item. Example: a standalone Rockstar II hub with a Comp 95 donor. No item is deleted and no price is reduced.
- `retrofit_worklist` reports source-aware conflicts such as a Comp 95 50 mm axle reference with the G1 drive/70 mm axle planning study. This is a question to measure, not an assertion of compatibility.
- `unmapped_inclusion_worklist` surfaces included claims without catalog counterparts, e.g. F5 bindings. A new donor or changed source is treated as unknown and held.
- `order_lines` deliberately sets **actual supplier order quantity**, **actual assembly quantity**, and package unit to `null`. The catalog `price.qty` field is retained only as a historical reference pricing multiplier.
- `source_worklist` explicitly asks for exact physical revision, genuine manufacturer instructions, current stock, verified assembly counts, vendor order unit and fresh quote.
- `costs.overlap_adjusted_total_usd`, `confirmed_quote_total_usd` and `all_in_assembly_total_usd` are all `null`. Do not present a speculative savings number from an inclusion match.
- All quantities/compatibility/electrical eligibility gates and all authority booleans remain false.

A proposed part revision invalidates the attached package audit in the what-if passport. A new registry and new reference snapshot must be reviewed before an inclusion claim can appear in a new coherent study.

## Data needed to make this a real construction BOM

For every selected supplier product, obtain the **exact sellable variant, revision and manufacturer part number**, plus authoritative written contents and included fastener counts, package/case/unit quantities, and dated vendor price/stock evidence. For a donor board, inspect and photograph the actual wheels, hubs, trucks, axles, bearings and bindings against its revision-matched list.

For mechanical assembly, measure the deck mount pattern, truck hanger and axle stack, hub/wheel retention, brake mounts and drive clearance at full steering travel. Independently qualified electrical system, charger, braking and mechanical safety evidence are still mandatory outside the generic Builder.

This information is **not yet available as qualified evidence**. The feature creates a clear research/receiving queue rather than fabricating missing dimensions.

## Validation

```bash
python tools/validate_board_package_inclusions.py
node --test tests/js/test_board_assembly_inventory.mjs
python -m pytest -q tests/test_board_assembly_inventory.py
python tools/generate_build_passport.py configurator/examples/trail_rider_profile.json brake_first_trail_core > /tmp/packet-py.json
node tools/generate_build_passport.mjs configurator/examples/trail_rider_profile.json brake_first_trail_core > /tmp/packet-js.json
python tools/compare_build_passports.py /tmp/packet-py.json /tmp/packet-js.json
```

The full GitHub Actions suite runs Python/JavaScript tests, an updated exact cross-runtime passport parity check, catalog integrity audit and existing electrical/physical authority regressions. A manual desktop/tablet/mobile, screen-reader and printed-page review is still tracked in issue #97.

## Next tranche

An explicitly versioned received-content contract with independent source review and a real measurement/fit-pilot workflow, followed by browser/print QA. Until then: **planning only, not an order list**.
