# Browser CAD Twin v2: source receipts → metric geometry → diagnostic previews

Status: **draft PR #114 only**, parent PRs #110–#113 not merged to `main`. All geometry and dimensional receipts in this tranche remain research-only. No kit received, manufacturer STEP authenticated, mounting datum verified, interference cleared, electric system commissioned or purchase quantity approved.

## What exists now

The existing default assembled Tangent board is still a seven-category, source-named **procedural reference** with a single complete-board purchasing package. It has an exploded SVG/Three.js view, camera presets, selection, source-linked kit table and guarded JSON exports. No imported candidate replaces these unmeasured shapes.

The collapsed **CAD Asset Laboratory** adds:

- **Registered geometry coverage:** exact kit-variant and role identity, SHA-256-addressed local GLBs and conversion receipts, source revision, permission evidence, distinct candidate versus approved status. Today 0/7 registered CAD bodies. A source model never creates an extra order line.
- **Manufacturer dimensional evidence:** provenance-linked published dimensions for Tangent deck-with-brackets (overall 914 mm × 248 mm, published wheelbases), approximate general Zee Bracket envelope (210 × 82.6 × 57.2 mm), advertised wheel diameters and the maker's DIY trim stencil. Values remain evidence *claims* and do not drive the visual geometry or mating transforms.
- **Original maker DIY drawing:** [Loaded Zee Bracket printable stencil](https://cdn.shopify.com/s/files/1/0092/1085/5524/files/Loaded-Zee-Bracket-template.pdf?v=1688582078). It illustrates 1.625 in / 41.275 mm lateral and 2.125 in / 53.975 mm longitudinal nominal truck-hole spacing, plus 16°/23° DIY trimming guidance. It is **not** the received Tangent's certified mounting plan. The template is linked, not republished.
- **Local GLB viewer:** optional isolated orbitable inspection, bounded parser, no outside resources, never automatically assembled from a candidate mesh. Pinned assets are SHA-256 checked before rendering.
- **Candidate metric survey JSON:** an independent three-point rigid-body frame solver with residual checks, an AABB broad-phase across candidate boxes and explicit unverified contact/clearance results. This sandbox does not modify the integrated board, cannot produce physical fit clearance or authorize manufacturing and resets on exact kit change.

## Source-first CAD conversion, end to end

**glTF 2.0 specifies meters and +Y up.** STEP input is converted by CadQuery/OCCT to millimeter coordinates; the conversion script tessellates and multiplies coordinates by **0.001** for GLB meters. It checks sorted bounding extents after export, output file size, geometry budgets and creates an immutable digest receipt. Sorted envelopes alone do not verify local axes, hole locations or source authenticity.

With a genuine licensed source STEP:

```bash
python tools/convert_cad_step_to_glb.py \
  --source /path/to/permission-cleared-maker.step \
  --out /tmp/candidate.glb \
  --tolerance-mm 0.2
# Produces /tmp/candidate.glb and /tmp/candidate.glb.conversion.json
node tools/stage_cad_asset.mjs \
  --file /tmp/candidate.glb \
  --conversion-receipt /tmp/candidate.glb.conversion.json \
  --kit-variant-id "loaded-tangent-complete-105 mm Dad Bod 77a" \
  --role zee_brackets \
  --part-number SOURCE_EXACT_PART_NUMBER \
  --revision SOURCE_EXACT_REVISION \
  --source-url https://www.loadedboards.com/products/zee-bracket \
  --license EXPLICIT_REUSE_PERMISSION \
  --origin MANUFACTURER_PUBLISHED \
  --evidence-date 2026-10-11
```

The staging tool rejects a receipt from different bytes, mismatched glTF unit scale, an unbounded/error-ridden mesh, or an attempt to grant physical fit/ordering approval. It writes `assets/cad/<glb-sha256>.glb` and `assets/cad/<glb-sha256>.conversion.json`, and registers both immutable paths and digests. Operators must still review manufacturer attribution and licensing and confirm the exact received revision. The tool's output is a **candidate**; the original source rights must permit any publication.

### Independent metrology fixture format

Create a bounded JSON fixture scoped to the *exact* selected `kit_variant_id` and with `scope: "METRIC_CAD_SURVEY_FIXTURE_RESEARCH_ONLY"`, `schema_version: 1`, `units: "mm"`, and `authority` flags all false. Provide 2+ parts, each with a unique stable lower-case ID, an HTTPS source link, revision, `geometry_evidence: "UNVERIFIED_CANDIDATE_BOUNDS"`, `mating_datums_physically_verified: false`, `exact_revision_received: false`, a nonzero `survey_tolerance_mm` up to 2 mm, strict min/max local bounds in mm, and three or more ordered pairs of `local_mm` and `assembly_mm` landmarks. A fourth independent landmark is strongly recommended to detect a wrong correspondence. The workbench enforces a rigid 3D transform and fails closed for collinearity, excessive residual or unit/kit mismatch.

The resulting pairwise broad-phase classifies `CANDIDATE_AABBS_SEPARATED` or `POSSIBLE_OVERLAP_REQUIRES_NARROW_PHASE`. AABB overlap **never proves contact** and candidate separation **never proves actual ride, truck-steer, wheelbite or tolerance clearance**. This is an algorithm test on surveyed inputs, not a certified mechanical simulation.

## Physical twins: remaining qualification steps

1. **Acquire rights-cleared, revision-specific STEP**, ideally direct from Loaded (Tangent, Zee pair, board hardware) and Paris/Orangatang for the correct truck revision/wheels. Do not substitute an unrelated CAD-library proxy and silently call it OEM CAD.
2. **Inspect the actual package** and reconcile seller Paris V2/V3 ambiguity, bearing races, kingpin/axle/hanger geometry and all delivered items. Do not add duplicate purchasing lines.
3. **Record measured correspondences** for screw-hole centers, bracket mating planes, wheel bores and axle centers, with coordinate frames, units, revision, temperature and instrument uncertainty. A published overall envelope is not an appropriate registration datum.
4. **Build a metric scene** only after traceable transforms and inspect orientation/chirality, correspondence residuals, file hashes and repeated part instances. Require a positive reviewer action to promote any metric scene from candidate to assessment.
5. **Evaluate dynamic clearance** across steering and deck deflection, wheel bite, loaded ground height, stackup/tolerances and fasteners. Use mesh narrow-phase/contact geometry, not just AABB. Validate results against physical test. Treat electric X1 mechanical/battery systems separately.
6. **Review on actual devices** (screen readers, mobile touch, screenshots, online/offline WebGL), then process the stacked PR merges in order. No manufacturing, charging or checkout authority arises from browser CI.

## Automated checks

- `node --test tests/js/test_outdoor_cad_assets.mjs tests/js/test_outdoor_cad_metric_workbench.mjs`
- `python -m pytest -q tests/test_cad_step_glb_conversion.py`
- `node tests/browser/parts_picker_smoke.mjs` (when Playwright + Chromium installed)
- Full `.github/workflows/validate.yml` and Chromium workflow artifacts for exact final SHA.

External specs: [Khronos glTF coordinate/units](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html), [CadQuery importing STEP](https://cadquery.readthedocs.io/en/latest/importexport.html), [Loaded Zee Bracket](https://www.loadedboards.com/products/zee-bracket), [Loaded Tangent deck with brackets](https://www.loadedboards.com/products/tangent-deck-with-brackets).
