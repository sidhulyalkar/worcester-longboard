import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {validateCadDimensionalEvidence,planCadPublishedDimensions}
 from "../../builder/cad_dimension_evidence.mjs";
import {solveThreePointDatumFrame,transformedBounds,
 compareCandidateAabbs,evaluateMetricFixture}
 from "../../builder/cad_metric_workbench.mjs";
import {compileCompleteKitCadDisplay} from "../../builder/complete_kit_cad_schema.mjs";
import {buildPickerStudy} from "../../builder/parts_picker_engine.mjs";
import {auditCompleteKitClaim} from "../../builder/complete_kit_closure.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const load=n=>JSON.parse(readFileSync(path.join(root,"catalog",n),"utf8"));
const registry=load("outdoor_cad_dimensional_evidence.v1.json");
const catalog=load("outdoor_parts_picker.v1.json");
const kit=load("outdoor_complete_kit_claims.v1.json");
const retail=load("outdoor_retail_comparisons.v1.json");
const recipe=load("outdoor_complete_kit_cad_recipes.v1.json");
function cad(product){
 const variant=catalog.products.find(p=>p.id===product).variants[0].id;
 const study=buildPickerStudy(catalog,{domain_id:"skateboard_longboard",
  selections:{long_complete:variant}});
 const audit=auditCompleteKitClaim(study,kit,catalog,retail);
 return compileCompleteKitCadDisplay(study,audit,kit,recipe);
}
function part(id,translation=[0,0,0],distortion=0){
 const pts=[[0,0,0],[5,0,0],[0,6,0],[0,0,7]];
 return {id,source_url:"https://example.com/survey/evidence",revision:"synthetic-fixture",
  geometry_evidence:"UNVERIFIED_CANDIDATE_BOUNDS",
  mating_datums_physically_verified:false,exact_revision_received:false,
  survey_tolerance_mm:0.25,
  local_bounds_mm:{min_mm:[-1,-1,-1],max_mm:[1,1,1]},
  correspondences:pts.map((p,i)=>({
   local_mm:p,
   assembly_mm:p.map((x,j)=>x+translation[j]+(i===3&&j===0?distortion:0))
  }))};
}
function fixture(variant,space=12){
 return {schema_version:1,scope:"METRIC_CAD_SURVEY_FIXTURE_RESEARCH_ONLY",
  kit_variant_id:variant,units:"mm",
  authority:{procurement_authorized:false,
   fabrication_authorized:false,physical_fit_qualified:false},
  parts:[part("synthetic_deck"),part("synthetic_bracket",[space,0,0])]};
}
test("maker envelope, DIY stencil and wheel-size claims are traceable, NOT mating datums",()=>{
 assert.equal(validateCadDimensionalEvidence(registry).published_records,5);
 const large=planCadPublishedDimensions(cad("loaded-tangent-complete"),registry);
 const small=planCadPublishedDimensions(cad("loaded-tangent-caguama"),registry);
 assert.equal(large.scope,"PUBLISHED_DIMENSIONS_READ_ONLY_NOT_CAD");
 assert.equal(large.claims.length,12);
 assert.equal(large.claims.find(c=>c.label==="nominal_wheel_diameter").value_mm,105);
 assert.equal(small.claims.find(c=>c.label==="nominal_wheel_diameter").value_mm,85);
 assert.equal(large.claims.find(c=>c.label==="template_across_holes").value_mm,41.275);
 assert.equal(large.claims.find(c=>c.label==="template_along_holes").value_mm,53.975);
 assert.equal(large.qualified_mates,0);
 assert.ok(large.claims.every(c=>!c.usable_as_mounting_datum&&!c.revision_verified));
 assert.equal(large.additional_purchase_lines,0);
 assert.ok(large.claims.find(c=>c.meaning.startsWith("DIY_TEMPLATE"))
  .source_url.endsWith("Loaded-Zee-Bracket-template.pdf?v=1688582078"));
});
test("published dimensions reject forged clearances, pretend mounts and template relabeling",()=>{
 const mutate=fn=>{const r=structuredClone(registry);fn(r);return r;};
 const corrupt=[
  x=>x.authority.physical_clearances_verified=true,
  x=>x.references[0].claims[0].meaning="PHYSICALLY_MEASURED_MOUNT",
  x=>x.references[2].claims[0].meaning="PUBLISHED_OVERALL_ENVELOPE",
  x=>x.references[0].claims[0].usable_as_mounting_datum=true,
  x=>x.references[0].source_url="javascript:alert(1)",
  x=>x.references[0].applies_to.push(x.references[0].applies_to[0]),
  x=>x.references[1].roles.push("trucks","trucks"),
  x=>x.references[0].claims[0].value_mm=NaN
 ];
 for(const fn of corrupt)assert.throws(()=>validateCadDimensionalEvidence(
  mutate(fn)),/CAD dimensional evidence:/);
 assert.deepEqual(planCadPublishedDimensions(null,registry).claims,[]);
});
test("three-point alignment solves rotated rigid frames with millimeter residuals",()=>{
 const source=[[0,0,0],[10,0,0],[0,20,0],[0,0,15]];
 const rotated=p=>[-p[1]+30,p[0]-40,p[2]+12];
 const solution=solveThreePointDatumFrame(source.map(p=>({
  local_mm:p,assembly_mm:rotated(p)
 })),{max_residual_mm:.01});
 assert.ok(solution.max_residual_mm<1e-8);
 assert.deepEqual(solution.translation_mm,[30,-40,12]);
 assert.equal(solution.mounting_verified,false);
 const bounds=transformedBounds({min_mm:[0,0,0],max_mm:[2,3,5]},solution);
 assert.deepEqual(bounds,{min_mm:[27,-40,12],max_mm:[30,-38,17]});
 const mismatched=source.map(p=>({local_mm:p,assembly_mm:rotated(p)}));
 mismatched[3].assembly_mm=[32,-39,13];
 assert.throws(()=>solveThreePointDatumFrame(mismatched),/mismatched fiducials/);
 assert.throws(()=>solveThreePointDatumFrame([
  {local_mm:[0,0,0],assembly_mm:[0,0,0]},
  {local_mm:[1,0,0],assembly_mm:[1,0,0]},
  {local_mm:[2,0,0],assembly_mm:[2,0,0]}]),/degenerate/);
});
test("bounding-box broad-phase refuses to claim contact even for overlap",()=>{
 const a={min_mm:[0,0,0],max_mm:[2,2,2]};
 const far={min_mm:[5,0,0],max_mm:[7,2,2]};
 const near={min_mm:[1,0,0],max_mm:[3,2,2]};
 const separated=compareCandidateAabbs(a,far,{uncertainty_mm:0.25});
 assert.equal(separated.classification,"CANDIDATE_AABBS_SEPARATED");
 assert.equal(separated.conservative_axis_gap_mm,2.5);
 assert.equal(separated.physical_clearance_qualified,false);
 assert.equal(compareCandidateAabbs(a,near).classification,
  "POSSIBLE_OVERLAP_REQUIRES_NARROW_PHASE");
 assert.equal(compareCandidateAabbs(a,near).contact_confirmed,false);
 assert.throws(()=>compareCandidateAabbs(a,far,{uncertainty_mm:-1}),/uncertainty/);
});
test("metric fixture scopes by exact kit and never inherits safety/checkout authority",()=>{
 const variant=cad("loaded-tangent-complete").selected_variant_id;
 const report=evaluateMetricFixture(fixture(variant),{expected_variant_id:variant});
 assert.equal(report.candidate_pairs_checked,1);
 assert.equal(report.possible_overlap_pairs,0);
 assert.equal(report.pairs[0].classification,"CANDIDATE_AABBS_SEPARATED");
 assert.equal(report.physical_clearances_verified,0);
 assert.equal(report.procurement_authorized,false);
 assert.equal(report.fabrication_authorized,false);
 const overlapping=evaluateMetricFixture(fixture(variant,1));
 assert.equal(overlapping.possible_overlap_pairs,1);
 assert.equal(overlapping.pairs[0].contact_confirmed,false);
 const changed=fixture(variant);
 changed.authority.physical_fit_qualified=true;
 assert.throws(()=>evaluateMetricFixture(changed),/research scope/);
 assert.throws(()=>evaluateMetricFixture(fixture(variant),
  {expected_variant_id:"some other maker variant"}),/match selected exact/);
 const broken=fixture(variant);broken.parts[1].correspondences[2].assembly_mm[1]+=3;
 assert.throws(()=>evaluateMetricFixture(broken),/mismatched fiducials/);
 const duplicate=fixture(variant);duplicate.parts[1].id="synthetic_deck";
 assert.throws(()=>evaluateMetricFixture(duplicate),/unique lowercase/);
});
