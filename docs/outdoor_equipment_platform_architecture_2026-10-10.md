# Outdoor Equipment Platform: shared catalog architecture v0

**Status: October 10, 2026.** This is a machine-validated domain vocabulary and architecture proposal, not a product catalog migration. The existing Board Builder remains the only active configurator.

## North star

The platform should answer: **Given my body, terrain, skill, budget, owned equipment, and goals, what outdoor setup should I choose, customize, upgrade, maintain, or have fitted?**

For any supported activity, users should receive a few genuinely distinct coherent concepts with transparent tradeoffs, visible geometry, real variant-aware sourcing where documented, and explicit unresolved evidence. Think PCPartPicker plus a mechanics-aware evidence graph, but **not** an AI-issued compatibility certificate.

This is broader than making boards. An alpine skier may need an expert mounting/fitting handoff rather than DIY instructions; a camping user needs replacement-pole geometry and weather constraints rather than steering/braking rules. Domain-specific behavior is indispensable.

## Existing software to preserve

The current system already separates dated source snapshots, catalog components, visual geometry, explicit pairwise compatibility rules, rider profiles, planning candidate synthesis, Build Passports, donor inclusion audits, source/receiving observations, and physical authority. That is a valuable foundation.

However, the existing questionnaire assumes board-riding, the Composer enumerates deck/truck/wheel/brake/drive slots, the renderer assumes board geometry, and the performance traits include carve and range. Those cannot be reused unmodified for skis, surfboards or tents.

Keep the current runtime operational. Wrap it through a mountainboard domain adapter rather than replacing it in one large migration.

## Shared entity model

The cross-domain catalog needs **separate first-class records**:

- **Product family:** manufacturer model, product generation, and the dimensions along which variants differ.
- **Product variant:** exact manufacturer identifier, size, width, material, flex, binding mount, model year, revision, and any sport-specific properties actually documented.
- **Sellable package:** orderable unit such as one ski, a pair, a whole donor board, four wheels, a boot pair, or a kit with accessories. Package content is source- and revision-specific.
- **Supplier offer snapshot:** merchant, dated listing, original currency, advertised price, condition, quantity units and availability evidence. Historical listings are not live stock or guaranteed prices.
- **Engineering interface:** typed mounting, bearing, boot-sole, fin-box, release, electrical, fit or load feature, with measurement units and tolerances.
- **Evidence claim:** one specific dimensional or compatibility assertion with a date, exact source, applicable variant identity, provenance confidence, and outstanding review.
- **Geometry view:** observed/measured geometry versus visual approximation. Never use art geometry to approve fabrication.
- **Assembly architecture:** domain-specific required/optional component slots, parent-child inclusions, adapters and mode-dependent constraints.
- **Mission/profile:** shared human and environmental data plus discipline-specific inputs.
- **Qualification receipt:** separate sign-off by qualified reviewers or an independent physical release process, never inferred from a catalog entry.

ProductGroup / Product variant structured-data conventions are useful for ingesting families and SKUs, but they do **not** replace mechanical interface rules.

## Architecture

1. Source adapters ingest manufacturer pages, manuals, part diagrams and retailer offers into dated raw claims.
2. A core catalog normalizes product families, exact variants, sellable units, source snapshots and claims. Unsupported values stay UNKNOWN.
3. Domain adapters define required slots, meaningful ergonomic and performance questions, interface rules, scoring criteria, visuals and domain safety policies.
4. A constraint engine considers typed interface connections and **multi-component compatibility**. A matching nominal label only creates a candidate relationship, never proof of fit.
5. Candidate generation ranks alternatives by domain-specific goals, cost evidence completeness and unresolved integration effort. It returns no automatic shopping cart when critical facts are absent.
6. An evidence passport tracks why a recommendation exists, possible donor overlaps, current quotes, received variants, unresolved tolerances and required professional inspections.

The phases are parallel: universal source/variant infrastructure underneath, specialized gear/terrain expertise on top.

## Domain-specific examples

| Domain | Critical catalog slots | Interfaces and non-automatic checks |
|---|---|---|
| Mountainboards and electric boards | Deck/donor, truck, hub/wheel, brake, drive, battery | Mounting pattern, axle stack, combined brake/drive sweep, electrical protection and real braking |
| Snowboards | Board, left/right boot fit, bindings, mounting disc/kit | Burton 2x4, 4x4, legacy 3D and Channel mount families; discs/screws/adapters; binding size and boot fit |
| Alpine skis | Ski pair, boots, bindings, brakes | Boot-sole norm, binding acceptance, sole length, mounting zone and brake width; professional release and mounting tests |
| Touring skis | Ski, boots, touring bindings, skins, crampons | Tech insert system, touring/downhill modes, boot norm, climbing attachment and separate release qualification |
| Splitboards | Board, bindings, pucks, skins, tour pivot | Mode-switching interface and adapter chain, not just a ride-mode binding pattern |
| Surfboards | Board/hull, fin boxes, fins, leash | FCS II versus other fin systems and adapters, fin configuration, board volume/skill and leash attachment |
| Bicycles | Frame, fork, wheels, brakes, drivetrain | Hub spacing, axle and rotor standard, wheel/tire clearance, bottom bracket/drivetrain system |
| Camping shelters | Shelter, replacement poles, footprint, stakes | Pole section diameter/geometry, shelter attachment and weather/load constraints |

Current official documentation illustrates why this separation is necessary:

- Burton mount patterns and binding adapter considerations: https://www.burton.com/en-us/blogs/the-burton-blog/snowboard-binding-size-chart
- Salomon boot/binding compatibility letters and the role of professional verification: https://www.salomon.com/en-us/lp/g/ski-boot-and-binding-compatibility
- GripWalk ski boot sole limitations: https://www.grip-walk.com/faq/
- FCS II fin systems and old dual-tab adaptation: https://www.surffcs.com/pages/fin-systems
- Bicycle bottom-bracket standards: https://www.parktool.com/en-us/blog/repair-help/bottom-bracket-standards-and-terminology

These links support the **ontology**, not any claimed approval of specific products or unsafe DIY ski binding instructions.

## Typed compatibility, not a boolean

Instead of only joining two products by ID, compare compatible **interface types**. Examples include deck mounting geometry, axle-bore-spacer stack, snowboard insert pattern plus disc/fastener kit, ski boot-sole norm plus binding acceptance and boot sole length, or a surf fin base and fin-box standard.

Compatibility verdicts should distinguish:

- **INCOMPATIBLE:** a documented hard contradiction.
- **UNKNOWN:** a field, adapter path, exact revision or measurement is absent.
- **REFERENCE_MATCH_REVIEW_REQUIRED:** a manufacturer or normative family claim exists but the received variants or actual fit remain unconfirmed.
- **QUALIFICATION_REQUIRED:** enough design evidence exists for a specialist review, not for automatic assembly or release.

Some checks are hyperedges: a truck + wheel + brake + drive envelope can conflict even if every pair has a plausible published match. Ski boot + binding + brake + ski mounting is similarly coupled.

No “generic compatible=true” setting should ever bypass per-domain evidence or safety gates.

## Rider experience and personalization

A universal intake asks about activity, experience, conditions/terrain, human dimensions, budget, ownership goals, ease of maintenance, and existing gear. Then each domain asks a *small adaptive set* of high-information questions.

Examples: snowboard preferences for park/carve/powder and boot fit; alpine skiing terrain, ability, existing boot sole norms and professional fitting; surfing wave type, experience and board volume; bicycle intended terrain and geometry/fit; mountainboard terrain, carve, braking, range and electric intent.

Left and right foot/boot sizes should remain individually representable. Sensitive personal measurements should default to local-only or explicitly consented storage, with clear separation between human fit and manufacturer part measurements.

The results page should show three different concepts rather than random variation: visual design, expected use, cost evidence, unresolved interfaces, editable component choice, source/variant history, professional review, and purchasing only when justified.

Avoid one global “best” score. Carve or powered range are not comparable to avalanche risk, surf volume, or shelter weather exposure. Scoring dimensions belong to domains; the shared layer ranks evidence quality, uncertainty and user preferences.

## Machine-readable v0 contract

The file at catalog/outdoor_equipment_domains.v0.json is the first implementation slice, with:

- 8 bounded equipment domains and their required and optional roles.
- 15 typed, intentionally conservative interfaces.
- Per-domain inputs, proposed viewer adapters, and qualification policies.
- A read-only role mapping for every existing v1 component category.
- No new sellable products, manufacturer SKUs, live prices, fit determinations or released authority.

tools/validate_outdoor_equipment_domains.py verifies the domain vocabulary, migration coverage, unknown-safe state model, declared interfaces, safety policies and authority invariants. tests/test_outdoor_equipment_domains.py exercises omission, duplicate/unknown interface and false-approval regressions.

**This file is not yet a live schema consumed by the Builder UI.** It is a testable migration and design contract.

## Roadmap and acceptance gates

### Phase 0: Domain registry (this change)

Publish the read-only domain taxonomy and validation tests. Preserve all board runtime outputs and independent X1 release authority.

### Phase 1: Shared catalog graph and v1 adapter

Introduce versioned family, variant, package, offer, evidence-claim, interface and qualification data models. Import the current mountainboard catalog through a read-only adapter and show parity for old source links, BOM, geometry, readiness and authority. No automatic source-to-approval promotion.

### Phase 2: Snowboard pilot

Ingest a few real board, boot and binding variants from original manufacturer documentation. Compare several genuinely distinct all-mountain, freeride and freestyle concepts. Document the exact mounting disc/adapter and size uncertainties. Use a new snowboard viewer, not board-twin geometry.

### Phase 3: Alpine ski pilot with a professional installation route

Add skis, boots, bindings and mounting/brake relationships with normative boot compatibility and dedicated professional review of binding setting and release testing. Never generate a DIY release setting as a system-issued safety assurance. Add touring only after clear separation.

### Phase 4: Multi-mode and other surface boards

Splitboard tour/ride validation, surf fins/boards, and repair/upgrade/owner inventory flows. A generic subassembly model should handle the difference between "one board", "pair of skis", "four wheels", and "one package containing components."

### Phase 5: Outdoor equipment platform

Bicycle and shelter recipes, specialized safety/rating workflows, vendor/catalog contribution pipeline, owner inventory/maintenance history, and builder/repair communities. Consider additional outdoor categories only when a domain expert can articulate required interfaces and safety checks.

### Release gate before any new domain is public

- At least three mechanically or functionally distinct sourced example setups, not cosmetic variations.
- Exact product family versus variant and supplier pack units kept separate.
- No unreviewed pairing of a boot binding, fin box, axle, hub or proprietary mount.
- Missing/contradictory source information gives UNKNOWN or an explicit hold, never green.
- Automatic ordering/release does not follow from a generated candidate.
- Per-domain geometry renderers do not fabricate fit dimensions.
- Safety-critical interactions have manufacturer documentation and, where required, independent professional verification.
- Regression tests verify that legacy Board Builder and physical/electrical authority are unaffected.
- Real browser usability/accessibility walkthrough before launch.

## What not to do first

Do not begin with an unrestricted scraping agent, hundreds of low-evidence SKUs, one universal recommendation score, automatic mounting prescriptions, or a generic 3D mesh renderer that pretends all equipment shares the same physics.

The high-value first execution tranche after this contract is **a read-only v1-to-core product graph adapter and a carefully sourced snowboard mounting-interface pilot**, with no changes to the current electric mountainboard solver.
