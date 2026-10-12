import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {validateCadFieldObservations,validateCadReportedMeasurements}
 from "../../builder/cad_capture_campaign.mjs";
import {makeCadFieldNotebookRecord,newCadFieldNotebook,
 upsertCadFieldNotebook,removeCadFieldNotebookRecord}
 from "../../builder/cad_field_notebook.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const load=name=>JSON.parse(readFileSync(path.join(root,"catalog",name),"utf8"));
const requirements=load("outdoor_cad_capture_requirements.v1.json");
const cat=load("outdoor_parts_picker.v1.json");
const variants=cat.products.filter(p=>["loaded-tangent-complete","loaded-tangent-caguama"].includes(p.id))
 .map(p=>p.variants[0].id);
const metric=(overrides={})=>({
 task_id:"deck-hole-centers",part_revision:"Operator marking, package rev not independently checked",
 recorded_on:"2026-10-12",evidence_url:"https://example.org/field-report/deck-scan-1",
 uncertainty_mm:"0.12",note:"Actual photographed caliper measurement with operator reference, not independently checked.",
 feature_id:"front-left-hole",reading_kind:"SCALAR",scalar_value:"53.975",
 ...overrides
});
test("native scalar readings are captured as numeric millimeters and remain unreviewed",()=>{
 const blank=newCadFieldNotebook(variants[0],requirements);
 const one=upsertCadFieldNotebook(blank,metric(),requirements,variants[0]);
 assert.deepEqual(blank.records,[]);
 assert.equal(one.records.length,1);
 assert.equal(one.records[0].method,"METRIC_MEASUREMENT");
 assert.deepEqual(one.records[0].measurements_mm,[{
  feature_id:"front-left-hole",kind:"SCALAR",value_mm:53.975,frame_label:null
 }]);
 assert.equal(one.records[0].uncertainty_mm,.12);
 assert.equal(one.authority.fabrication_authorized,false);
 assert.equal(validateCadFieldObservations(one,requirements,variants[0]).structured_readings_unreviewed,1);
 assert.equal(validateCadFieldObservations(one,requirements,variants[0]).independently_verified,0);
 const deleted=removeCadFieldNotebookRecord(one,"deck-hole-centers",requirements,variants[0]);
 assert.equal(deleted.records.length,0);
 assert.equal(one.records.length,1);
});
test("operator-frame XYZ features may append to same task only with identical provenance",()=>{
 const blank=newCadFieldNotebook(variants[0],requirements);
 const first=upsertCadFieldNotebook(blank,metric({
  reading_kind:"POINT_3D",point_x:"-5.25",point_y:"0",point_z:"12.40",
  frame_label:"Operator arbitrary left deck datum",scalar_value:""
 }),requirements,variants[0]);
 assert.deepEqual(first.records[0].measurements_mm[0].value_mm,[-5.25,0,12.4]);
 const second=upsertCadFieldNotebook(first,metric({
  append_reading:true,feature_id:"front-right-hole",
  reading_kind:"POINT_3D",point_x:"5.25",point_y:"0",point_z:"12.40",
  frame_label:"Operator arbitrary left deck datum",scalar_value:""
 }),requirements,variants[0]);
 assert.equal(second.records[0].measurements_mm.length,2);
 assert.equal(first.records[0].measurements_mm.length,1);
 assert.equal(validateCadReportedMeasurements(second.records[0]).reviewed,0);
 assert.throws(()=>upsertCadFieldNotebook(second,metric({
  append_reading:true,feature_id:"third-hole",evidence_url:"https://example.org/new-photo",
  reading_kind:"POINT_3D",point_x:"1",point_y:"2",point_z:"3",
  frame_label:"Different frame"
 }),requirements,variants[0]),/added points must share source, date, revision/);
 assert.throws(()=>upsertCadFieldNotebook(second,metric({
  append_reading:true,feature_id:"front-right-hole",
  reading_kind:"POINT_3D",point_x:"1",point_y:"2",point_z:"3",
  frame_label:"Operator arbitrary left deck datum"
 }),requirements,variants[0]),/unique within a task/);
 assert.throws(()=>validateCadFieldObservations(second,requirements,variants[1]),/wrong kit/);
});
test("structured field report preserves old JSON import format",()=>{
 const blank=newCadFieldNotebook(variants[0],requirements);
 blank.records.push({
  task_id:"deck-hole-centers",method:"METRIC_MEASUREMENT",
  part_revision:"Legacy operator annotation",recorded_on:"2026-10-11",
  evidence_url:"https://example.org/old-report",uncertainty_mm:.15,
  note:"Legacy record did not contain structured numeric readings.",
  source_sha256:null
 });
 assert.equal(validateCadFieldObservations(blank,requirements,variants[0]).submitted_unreviewed,1);
 assert.equal(validateCadFieldObservations(blank,requirements,variants[0]).structured_readings_unreviewed,0);
 assert.throws(()=>upsertCadFieldNotebook(blank,metric({
  append_reading:true
 }),requirements,variants[0]),/replace record before appending|added points must share source/);
 const upgraded=upsertCadFieldNotebook(blank,metric(),requirements,variants[0]);
 assert.equal(upgraded.records[0].measurements_mm.length,1);
});
test("source CAD tasks require real source SHA-256; other methods forbid synthetic measurements",()=>{
 const base=newCadFieldNotebook(variants[0],requirements);
 const cad=upsertCadFieldNotebook(base,{
  task_id:"deck-source-geometry",part_revision:"Operator thinks Tangent V1",
  recorded_on:"2026-10-12",evidence_url:"https://example.org/step",
  note:"Unconfirmed operator claim of a CAD file, no rights or model review.",
  source_sha256:"a".repeat(64)
 },requirements,variants[0]);
 assert.equal(cad.records[0].source_sha256,"a".repeat(64));
 assert.equal(cad.records[0].measurements_mm,undefined);
 assert.equal(validateCadFieldObservations(cad,requirements,variants[0]).independently_verified,0);
 assert.throws(()=>upsertCadFieldNotebook(base,{
  task_id:"deck-source-geometry",part_revision:"unknown",recorded_on:"2026-10-12",
  evidence_url:"https://example.org/step",note:"Claim with no file hash",
  source_sha256:"not-hex"
 },requirements,variants[0]),/field evidence needs/);
 assert.throws(()=>validateCadFieldObservations({
  ...cad,records:[{...cad.records[0],measurements_mm:[{
   feature_id:"fake-geo",kind:"SCALAR",value_mm:20,frame_label:null
  }]}]
 },requirements,variants[0]),/structured readings require metric method/);
});
test("bad units, malformed points, forged verification flags, and mixed records all fail closed",()=>{
 const variant=variants[0],blank=newCadFieldNotebook(variant,requirements);
 const inputs=[
  {feature_id:"No Spaces!",scalar_value:"5"},
  {feature_id:"good-name",scalar_value:"Infinity"},
  {feature_id:"good-name",scalar_value:"-1"},
  {reading_kind:"POINT_3D",point_x:"-10001",point_y:"0",point_z:"0",
   frame_label:"Operator left wheel center"},
  {reading_kind:"POINT_3D",point_x:"1",point_y:"2",point_z:"3",frame_label:""},
  {reading_kind:"NO_TYPE",point_x:"1",point_y:"2",point_z:"3"},
  {uncertainty_mm:"0"},
  {uncertainty_mm:"not-a-number"},
  {recorded_on:"not-a-date"},
  {evidence_url:"javascript:alert(1)"}
 ];
 for(const patch of inputs)
  assert.throws(()=>upsertCadFieldNotebook(blank,metric(patch),requirements,variant),
   /CAD (field notebook|capture campaign):/);
 const valid=upsertCadFieldNotebook(blank,metric(),requirements,variant);
 const poisoned=[
  r=>r.measurements_mm[0].physical_fit_qualified=true,
  r=>r.measurements_mm[0].value_mm=NaN,
  r=>r.measurements_mm[0].value_mm=[1,2,3],
  r=>r.measurements_mm[0].frame_label="FORGED_ASSEMBLY_DATUM",
  r=>r.measurements_mm.push({...r.measurements_mm[0]})
 ];
 for(const corrupt of poisoned){
  const cloned=structuredClone(valid);
  corrupt(cloned.records[0]);
  assert.throws(()=>validateCadFieldObservations(cloned,requirements,variant),
   /CAD capture campaign:/);
 }
 assert.throws(()=>removeCadFieldNotebookRecord(valid,"bogus-task",requirements,variant),
  /unknown task/);
 assert.equal(makeCadFieldNotebookRecord(metric(),requirements).measurements_mm.length,1);
});
