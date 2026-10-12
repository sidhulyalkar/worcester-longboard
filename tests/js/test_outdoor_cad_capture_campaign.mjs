import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {buildPickerStudy} from "../../builder/parts_picker_engine.mjs";
import {auditCompleteKitClaim} from "../../builder/complete_kit_closure.mjs";
import {compileCompleteKitCadDisplay} from "../../builder/complete_kit_cad_schema.mjs";
import {validateCadCaptureRequirements,blankCadFieldObservations,
 validateCadFieldObservations,planCadCaptureCampaign}
 from "../../builder/cad_capture_campaign.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const load=n=>JSON.parse(readFileSync(path.join(root,"catalog",n),"utf8"));
const cat=load("outdoor_parts_picker.v1.json"),kit=load("outdoor_complete_kit_claims.v1.json");
const retail=load("outdoor_retail_comparisons.v1.json"),recipe=load("outdoor_complete_kit_cad_recipes.v1.json");
const req=load("outdoor_cad_capture_requirements.v1.json");
const dims=load("outdoor_cad_dimensional_evidence.v1.json");
const registry=load("outdoor_cad_asset_registry.v1.json");
const build=name=>{
 const variant=cat.products.find(p=>p.id===name).variants[0].id;
 const study=buildPickerStudy(cat,{domain_id:"skateboard_longboard",
  selections:{long_complete:variant}});
 const audit=auditCompleteKitClaim(study,kit,cat,retail);
 return {cad:compileCompleteKitCadDisplay(study,audit,kit,recipe),audit};
};
const sample=(task_id,date="2026-10-12")=>({
 task_id,method:task_id==="truck-seller-revision"?
  "REVISION_RECONCILIATION":"METRIC_MEASUREMENT",part_revision:"RECORDED_ONLY_UNCONFIRMED",
 evidence_url:"https://example.com/research/photo-or-paper-not-independent",
 recorded_on:date,uncertainty_mm:task_id==="truck-seller-revision"?null:0.1,
 note:"Operator claims this measurement was taken but no independent review occurred.",
 source_sha256:null
});
test("all seven complete-kit part roles and seven interfaces have explicit measurement plans",()=>{
 const v=validateCadCaptureRequirements(req);
 assert.deepEqual(v,{role_count:7,required_task_count:20,interface_check_count:7,verified_tasks:0});
 const {cad,audit}=build("loaded-tangent-complete");
 const report=planCadCaptureCampaign(cad,req,dims,registry,{kitAudit:audit});
 assert.equal(report.task_count,20);
 assert.equal(report.missing_evidence,20);
 assert.equal(report.reported_unreviewed,0);
 assert.equal(report.interfaces.length,7);
 assert.equal(report.roles.length,7);
 assert.equal(report.geometry_candidate_count,0);
 assert.equal(report.physical_mates_verified,0);
 assert.equal(report.dynamic_clearances_verified,0);
 assert.equal(report.procurement_authorized,false);
 assert.equal(report.fabrication_authorized,false);
 assert.equal(report.additional_purchase_lines,0);
 assert.ok(report.interfaces.some(i=>i.id==="loaded-wheelbite"&&i.roles.includes("trucks")));
 assert.ok(report.roles.find(r=>r.role==="trucks").source_reference_urls.some(u=>u.includes("paristruckco")));
 assert.equal(report.seller_revision_conflict_unresolved,true);
 assert.deepEqual(planCadCaptureCampaign(null,req,dims,registry).roles,[]);
});
test("85mm and 105mm variation has distinct provenance and cannot cross-import observations",()=>{
 const a=build("loaded-tangent-complete").cad;
 const b=build("loaded-tangent-caguama").cad;
 const aReport=planCadCaptureCampaign(a,req,dims,registry);
 const bReport=planCadCaptureCampaign(b,req,dims,registry);
 const aLinks=aReport.roles.find(r=>r.role==="wheels").source_reference_urls.join(" ");
 const bLinks=bReport.roles.find(r=>r.role==="wheels").source_reference_urls.join(" ");
 assert.match(aLinks,/dad-bod-105mm/);
 assert.doesNotMatch(aLinks,/caguama-85mm/);
 assert.match(bLinks,/caguama-85mm/);
 assert.doesNotMatch(bLinks,/dad-bod-105mm/);
 assert.notEqual(a.selected_variant_id,b.selected_variant_id);
 const field=blankCadFieldObservations(a.selected_variant_id);
 assert.equal(validateCadFieldObservations(field,req,a.selected_variant_id).submitted_unreviewed,0);
 assert.throws(()=>planCadCaptureCampaign(b,req,dims,registry,{observations:field}),
  /wrong kit/);
});
test("field observations are traceable but never independently verified",()=>{
 const {cad}=build("loaded-tangent-complete");
 const field=blankCadFieldObservations(cad.selected_variant_id);
 field.records.push(sample("truck-seller-revision"),sample("wheel-core-bearing-seats"));
 const accepted=validateCadFieldObservations(field,req,cad.selected_variant_id);
 assert.equal(accepted.submitted_unreviewed,2);
 assert.equal(accepted.independently_verified,0);
 const report=planCadCaptureCampaign(cad,req,dims,registry,{observations:field});
 assert.equal(report.reported_unreviewed,2);
 assert.equal(report.missing_evidence,18);
 assert.equal(report.independently_verified,0);
 assert.equal(report.physical_mates_verified,0);
 assert.equal(report.roles.find(r=>r.role==="trucks").revision_confirmed,false);
 assert.match(report.tasks.find(t=>t.task_id==="truck-seller-revision")
  .field_observation.note,/unreviewed sample|Operator claims/);
 assert.equal(report.tasks.find(t=>t.task_id==="truck-seller-revision").status,
  "FIELD_REPORTED_NOT_INDEPENDENTLY_VERIFIED");
 assert.ok(report.interfaces.every(i=>i.physical_fit_qualified===false));
});
test("forged safety flags, wrong units, bad evidence and duplicates all fail closed",()=>{
 const {cad}=build("loaded-tangent-complete");
 const base=blankCadFieldObservations(cad.selected_variant_id);
 base.records.push(sample("wheel-core-bearing-seats"));
 const bad=[
  d=>d.scope="REVIEWED_AND_APPROVED",
  d=>d.authority.physical_fit_qualified=true,
  d=>d.units="inches",
  d=>d.kit_variant_id="other product",
  d=>d.records.push(sample("wheel-core-bearing-seats")),
  d=>d.records[0].task_id="fictional-metric-task",
  d=>d.records[0].uncertainty_mm=-1,
  d=>d.records[0].uncertainty_mm=NaN,
  d=>d.records[0].recorded_on="2026-02-30",
  d=>d.records[0].evidence_url="javascript:alert(1)",
  d=>d.records[0].source_sha256="bogus",
  d=>d.records[0].method="RECEIVING_AUDIT",
  d=>d.records[0].uncertainty_mm=null,
  d=>d.records[0].physical_fit_qualified=true,
  d=>d.records[0].note="short",
  d=>d.records[0].part_revision=" "
 ];
 for(const corrupt of bad){
  const copy=structuredClone(base);corrupt(copy);
  assert.throws(()=>validateCadFieldObservations(copy,req,cad.selected_variant_id),
   /CAD capture campaign:/);
 }
 const mutated=[
  d=>d.authority.procurement_authorized=true,
  d=>d.requirements[0].tasks[0].priority=0,
  d=>d.requirements[1].role="deck",
  d=>d.requirements[2].tasks[0].task_id=d.requirements[0].tasks[0].task_id,
  d=>d.interfaces[0].roles=["deck","deck"],
  d=>d.interfaces[0].physical_fit_qualified=true
 ];
 for(const corrupt of mutated){
  const copy=structuredClone(req);corrupt(copy);
  assert.throws(()=>validateCadCaptureRequirements(copy),/CAD capture campaign:/);
 }
});
