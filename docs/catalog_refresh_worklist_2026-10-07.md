# Board catalog source-refresh worklist

Audit date: **2026-10-07**

This is a catalog-evidence maintenance queue. It is not stock confirmation, checkout authorization, fabrication authority, or powered-operation authority.

## Health summary

- source-linked components: **22**
- fresh: **15**
- refresh due: **7**
- stale: **0**
- missing provenance: **0**
- planning-only components: **15**
- visualization-only geometry proxies: **3**

## Refresh queue

### MBS

- **REFRESH_DUE** · mbs_comp95_2026_09_11 · 26 days old · DONOR-COMP95
  - source: https://www.mbs.com/shop/p/comp-95-mountainboard-silver-hex
  - reason: source is 26 days old; refresh before relying on current stock or price
- **REFRESH_DUE** · mbs_g1_2026_09_11 · 26 days old · DRIVE-G1-DUAL
  - source: https://www.mbs.com/shop/parts/electric-parts/gear-drives
  - reason: source is 26 days old; refresh before relying on current stock or price
- **REFRESH_DUE** · mbs_hubs_2026_09_11 · 26 days old · HUB-RSII
  - source: https://www.mbs.com/shop/parts/wheels/hubs
  - reason: source is 26 days old; refresh before relying on current stock or price
- **REFRESH_DUE** · mbs_matrixiii_2026_09_11 · 26 days old · AXLE-M3-70, TRUCK-M3-400
  - source: https://www.mbs.com/shop/parts/trucks/matrix-iii
  - reason: source is 26 days old; refresh before relying on current stock or price
- **REFRESH_DUE** · mbs_t2_9_2026_09_11 · 26 days old · TIRE-T2-9
  - source: https://www.mbs.com/shop/p/13120-9-mbs-t2-tires-1
  - reason: source is 26 days old; refresh before relying on current stock or price
- **REFRESH_DUE** · mbs_v5_2026_09_11 · 26 days old · BRAKE-V5
  - source: https://www.mbs.com/shop/p/15006-mbs-v5-brake-system
  - reason: source is 26 days old; refresh before relying on current stock or price

## Visualization-only geometry proxies

- trampa_vertigo_406 (VERTIGO 16 in / 12 mm hollow-axle truck): Wheel-center lateral value is a visualization proxy from the 14-inch center-wheel-width published for the related TRAMPA 12 mm brake-hanger family; do not use for fit.
- apex_air_434 (Apex Air PKP 434 mm truck): Source provides 434 mm axle-end width and 300 mm inner-bearing spacing, not wheel-center spacing. Wheel center is a visualization proxy only.
- lacroix_hyperlite_381 (Hypertruck Lite 15 in hanger reference): 381 mm is the published hanger width. Wheel-center lateral is a visualization proxy inferred from the complete Barrel's 16-inch overall width with a generic 2-inch visual tire width; do not use for fit or fabrication.

## Refresh procedure

For each queued source, re-open the official vendor or named retailer page, verify the exact interface facts used by the catalog, record availability or price only as a dated snapshot, and update the component source date plus snapshot verification date. A source refresh never creates purchase, fabrication, charging, or powered-operation authority.
