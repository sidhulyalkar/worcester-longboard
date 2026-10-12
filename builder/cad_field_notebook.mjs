// Exact-variant, memory-only operator field log. No review, approval or local storage.
import {blankCadFieldObservations,validateCadCaptureRequirements,
 validateCadFieldObservations} from "./cad_capture_campaign.mjs";
const fail=s=>{throw Error("CAD field notebook: "+s);};
const raw=x=>typeof x==="string"?x:"";
const nonempty=x=>raw(x).trim();
const precision=x=>{
 if(!nonempty(x))fail("measurement and uncertainty must be entered explicitly");
 const n=Number(x);
 if(!Number.isFinite(n))fail("measurements must be finite");
 return n;
};
const taskMap=req=>new Map(req.requirements.flatMap(g=>
 g.tasks.map(t=>[t.task_id,{...t,role:g.role}])));
export function makeCadFieldNotebookRecord(fields,requirements){
 validateCadCaptureRequirements(requirements);
 const task=taskMap(requirements).get(raw(fields?.task_id));
 if(!task)fail("select one of the 20 required evidence tasks");
 const method=task.required_method;
 const reading=method==="METRIC_MEASUREMENT";
 const kind=raw(fields.reading_kind)||"SCALAR";
 const record={
  task_id:task.task_id,method,
  part_revision:nonempty(fields.part_revision),
  evidence_url:nonempty(fields.evidence_url),
  recorded_on:raw(fields.recorded_on),
  uncertainty_mm:reading?precision(fields.uncertainty_mm):null,
  note:nonempty(fields.note),
  source_sha256:method==="CAD_SOURCE"?nonempty(fields.source_sha256):null
 };
 if(reading){
  const label=nonempty(fields.feature_id);
  const value=kind==="SCALAR"?precision(fields.scalar_value):
   kind==="POINT_3D"?[precision(fields.point_x),precision(fields.point_y),
    precision(fields.point_z)]:null;
  if(value===null)fail("choose scalar or XYZ point measurement");
  record.measurements_mm=[{
   feature_id:label,kind,value_mm:value,
   frame_label:kind==="POINT_3D"?nonempty(fields.frame_label):null
  }];
 }
 return record;
}
export function upsertCadFieldNotebook(packet,fields,requirements,variant){
 validateCadFieldObservations(packet,requirements,variant);
 const record=makeCadFieldNotebookRecord(fields,requirements);
 const next=structuredClone(packet);
 const index=next.records.findIndex(r=>r.task_id===record.task_id);
 if(index<0)next.records.push(record);
 else if(fields?.append_reading===true&&record.method==="METRIC_MEASUREMENT"){
  const prev=next.records[index];
  for(const k of ["part_revision","evidence_url","recorded_on","uncertainty_mm","note"])
   if(prev[k]!==record[k])fail("added points must share source, date, revision, note and uncertainty with existing task");
  if(!Array.isArray(prev.measurements_mm))
   fail("legacy task has no structured points; replace record before appending");
  if(prev.measurements_mm.some(m=>m.feature_id===record.measurements_mm[0].feature_id))
   fail("feature IDs must be unique within a task");
  record.measurements_mm=[...prev.measurements_mm,...record.measurements_mm];
  next.records[index]=record;
 }else next.records[index]=record;
 validateCadFieldObservations(next,requirements,variant);
 return next;
}
export function removeCadFieldNotebookRecord(packet,taskId,requirements,variant){
 validateCadFieldObservations(packet,requirements,variant);
 if(!taskMap(requirements).has(taskId))fail("unknown task removal rejected");
 const next=structuredClone(packet);
 next.records=next.records.filter(r=>r.task_id!==taskId);
 validateCadFieldObservations(next,requirements,variant);
 return next;
}
export function newCadFieldNotebook(variant,requirements){
 const next=blankCadFieldObservations(variant);
 validateCadFieldObservations(next,requirements,variant);
 return next;
}
