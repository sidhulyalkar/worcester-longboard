# Maker board-sports reference pilot v1

**October 10, 2026**. This adds five actual manufacturer-publication references to the exploded Assembly Atlas, not approved hardware configurations, current in-stock offers or buying recommendations.

## Source-backed longboard studies

Maker: Loaded Boards.

- Tangent Standard Complete with 105 mm Dad Bod 77a option: manufacturer advertises Loaded Tangent deck, Zee brackets, Paris V3 150 mm 50-degree trucks, Orangatang 105 mm Dad Bod 77a wheels, Loaded Jehu V2 bearings, and hardware. See https://www.loadedboards.com/products/tangent-longboard-skateboard .
- Omakase Standard Complete: manufacturer lists Omakase deck, Paris V3 165 mm trucks, Orangatang 75 mm In Heat wheels, bushing and bearing references, Paris risers and hardware. See https://www.loadedboards.com/products/omakase-longboard-skateboard .

These complete-board published contents explain genuine assemblies and alternative longboard mechanical concepts. They do NOT establish a received kit's exact fasteners, bearing counts, revision, geometry, individual replacement fit or supplier quantity.

## Snowboard source reference studies

Maker: Burton.

Three studies:
- Custom Camber (2027) family + Mission Re:Flex binding (2027) + Re:Flex Combo Disc reference + unknown boot pair.
- Good Company Camber (2027) + Cartel Re:Flex (2027) + Combo Disc + unknown boots.
- Process Camber (2027) + Step On Re:Flex (2027) + Combo Disc + unknown matching Step On boots.

Official pages:
- https://www.burton.com/en-us/products/mens-burton-custom-camber-snowboard-106881
- https://www.burton.com/en-us/products/burton-good-company-camber-snowboard-235951
- https://www.burton.com/en-us/products/mens-burton-process-camber-snowboard-106921
- https://www.burton.com/en-us/products/mens-burton-mission-re-flex-snowboard-bindings-105461
- https://www.burton.com/en-us/products/mens-burton-cartel-re-flex-snowboard-bindings-105391
- https://www.burton.com/en-us/products/mens-burton-step-on-re-flex-snowboard-bindings-172831
- https://www.burton.com/en-us/products/burton-re-flex-combo-disc-229011
- https://www.burton.com/en-us/blogs/the-burton-blog/burton-reflex-bindings-overview

Burton explicitly documents Re:Flex disc/adapter families, and describes EST as The Channel-only. Older 3D requires a special 3D Hinge Disc, not assumed included. Step On bindings require matching Step On boots. An accepted mounting family only creates a reference *candidate*, never certified mounting, boot fit or safe release.

**No binding or boot size selected in these studies.** The exploded boot pair is an intentionally null-source placeholder. The board and binding models are product-family references, not purchased size/color/manufacturing revisions. A separate real fitting/inspection is required. All physical authorizations remain false.

## Deterministic integration

Data source: catalog/board_sport_reference_studies.v1.json with 10 original-manufacturer public references and five manufacturer-anchored studies. All source URLs are HTTPS maker domains and source IDs must bind exactly.

Assembly graph engines (JavaScript and Python) accept a referenced study only if its entire input exactly equals a stored, versioned registry study. No arbitrary assembled combination gets promoted by supplying a fake source URL or receipt count.

The existing unsourced concept examples still work separately and are labeled as unsourced; live mountainboard design candidates still import only the original board catalog. The user now chooses one of five maker-backed studies inside the same exploded UI and sees component source links, advertised content claims and outstanding fit/mounting questions.

A separate maker-family mounting rule checks Channel M6 references and Re:Flex Combo Disc as a documented candidate match requiring review, tests known conflicting EST versus non-Channel combinations and missing 3D adapters, and always requires independent boot size and exact hardware verification.

Neither source product pricing, current stock, actual shipped quantities, boot/binding fit, fastener torque nor installation clearance is inferred from the public pages.

## Tests

    python tools/validate_board_sport_reference_studies.py
    node --test tests/js/test_board_sport_source_studies.mjs
    python -m pytest -q tests/test_board_sport_source_studies.py
    python tools/compare_exploded_assemblies.py
    python tools/compare_snowboard_mount_checks.py

Full CI additionally runs the legacy candidate/BOM/Build Passport parity, source integrity, CAD, firmware and physical authorization regression gates.

## Next

Real exact-sized product variants, body/boot fit constraints, per-variant hardware selection, independent mount geometry, live seller quotes and true sport-specific candidate generation are the next expansion tranches under issue #106. These reference studies are not yet three qualified complete cross-sport builds.
