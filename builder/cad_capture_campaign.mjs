// Source-based CAD measurement campaign. Field observations are assertions,
// never independent review, manufacturer CAD, measured mates or safety approval.
const roles=["deck","zee_brackets","trucks","wheels","bearings",
 "deck_hardware","truck_hardware"];
const methods=["CAD_SOURCE","METRIC_MEASUREMENT","PHYSICAL_TEST",
 "REVISION_RECONCILIATION","RECEIVING_AUDIT"];
const check=(ok,message)=>{if(!ok)throw Error("CAD capture campaign: "+message);};
const isObj=x=>x&&typeof x==="object"&&!Array.isArray(x);
const url=x=>{try{const u=new URL(x);return u.protocol==="https:"&&!u.username&&!u.password;}catch{return false;}};
const noControl=x=>typeof x==="string"&&x.trim()===x&&x.length>0&&
 x.length<=512&&[...x].every(c=>c.charCodeAt(0)>=32);
const lowerId=x=>typeof x==="string"&&/^[a-z][a-z0-9-]{4,90}$/.test(x);
const date=x=>typeof x==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&
 !Number.isNaN(Date.parse(x))&&new Date(x+"T00:00:00Z").toISOString().slice(0,10)===x;
// Structured field readings are operator-reported coordinates, NOT assembly datums.
export function validateCadReportedMeasurements(rec){
 const readings=rec.measurements_mm;
 if(readings===undefined)return {structured_readings:0,reviewed:0};
 check(rec.method==="METRIC_MEASUREMENT"&&Array.isArray(readings)&&
  readings.length>=1&&readings.length<=16,
  "structured readings require metric method and 1-16 features");
 const seen=new Set();
 for(const m of readings){
  check(isObj(m)&&Object.keys(m).sort().join("|")===
   ["feature_id","kind","value_mm","frame_label"].sort().join("|")&&
   lowerId(m.feature_id)&&!seen.has(m.feature_id)&&
   ["SCALAR","POINT_3D"].includes(m.kind),
   "measurement requires a unique feature ID and supported kind");
  seen.add(m.feature_id);
  check(m.kind==="SCALAR"?
   (typeof m.value_mm==="number"&&Number.isFinite(m.value_mm)&&
    m.value_mm>=0&&m.value_mm<=10000&&m.frame_label===null):
   (Array.isArray(m.value_mm)&&m.value_mm.length===3&&
    m.value_mm.every(n=>typeof n==="number"&&Number.isFinite(n)&&
     Math.abs(n)<=10000)&&noControl(m.frame_label)&&
    m.frame_label.length<=120),
   "reported dimensions must be finite millimeters; 3D points need a named operator frame");
 }
 return {structured_readings:readings.length,reviewed:0};
}
export function validateCadCaptureRequirements(schema){
 check(schema?.schema_version===1&&schema.scope===
  "CAD_METROLOGY_REQUIREMENTS_NOT_ENGINEERING_APPROVAL"&&
  Object.keys(schema.authority??{}).length===3&&
  schema.authority.procurement_authorized===false&&
  schema.authority.fabrication_authorized===false&&
  schema.authority.physical_fit_qualified===false,
  "unqualified capture scope and locked authority required");
 check(Array.isArray(schema.requirements)&&schema.requirements.length===7&&
  schema.requirements.every((r,i)=>r.role===roles[i]&&
   Array.isArray(r.tasks)&&r.tasks.length>=2&&r.tasks.length<=8),
  "must enumerate exact seven maker assembly roles");
 const taskIds=new Set();
 for(const group of schema.requirements)for(const t of group.tasks){
  check(Object.keys(t).sort().join("|")==="instruction|priority|required_method|task_id"&&
   lowerId(t.task_id)&&!taskIds.has(t.task_id)&&
   methods.includes(t.required_method)&&
   Number.isInteger(t.priority)&&t.priority>=1&&t.priority<=3&&
   noControl(t.instruction)&&t.instruction.length>=25,
   "every measurement task needs a unique ID, method, priority and instruction");
  taskIds.add(t.task_id);
 }
 check(Array.isArray(schema.interfaces)&&schema.interfaces.length>=5&&
  schema.interfaces.length<=24,"interface review matrix missing");
 const interfaceIds=new Set();
 for(const x of schema.interfaces){
  check(Object.keys(x).sort().join("|")==="check|id|priority|roles"&&
   lowerId(x.id)&&!interfaceIds.has(x.id)&&
   Array.isArray(x.roles)&&x.roles.length>=2&&x.roles.length<=7&&
   x.roles.every(y=>roles.includes(y))&&
   new Set(x.roles).size===x.roles.length&&
   Number.isInteger(x.priority)&&x.priority>=1&&x.priority<=3&&
   noControl(x.check)&&x.check.length>=20,
   "interface check needs exact role dependencies and a review plan");
  interfaceIds.add(x.id);
 }
 return {role_count:7,required_task_count:taskIds.size,
  interface_check_count:interfaceIds.size,verified_tasks:0};
}
export function blankCadFieldObservations(kitVariantId){
 check(noControl(kitVariantId),"select exact kit revision before creating a field sheet");
 return {schema_version:1,scope:"UNREVIEWED_CAD_FIELD_OBSERVATIONS",
  kit_variant_id:kitVariantId,units:"mm",
  authority:{procurement_authorized:false,fabrication_authorized:false,
   physical_fit_qualified:false},records:[]};
}
export function validateCadFieldObservations(observations,requirements,variant){
 const {required_task_count}=validateCadCaptureRequirements(requirements);
 check(noControl(variant),"exact kit ID required");
 check(observations?.schema_version===1&&observations.scope===
  "UNREVIEWED_CAD_FIELD_OBSERVATIONS"&&observations.kit_variant_id===variant&&
  observations.units==="mm"&&isObj(observations.authority)&&
  Object.keys(observations.authority).length===3&&
  observations.authority.procurement_authorized===false&&
  observations.authority.fabrication_authorized===false&&
  observations.authority.physical_fit_qualified===false,
  "wrong kit, units or forged field authority");
 check(Array.isArray(observations.records)&&
  observations.records.length<=required_task_count,
  "observation collection too large");
 const taskMethods=new Map(requirements.requirements.flatMap(r=>
  r.tasks.map(t=>[t.task_id,t.required_method])));
 const taskIds=new Set(taskMethods.keys());
 const observed=new Set();
 for(const rec of observations.records){
  const required=["task_id","method","part_revision","evidence_url","recorded_on",
   "uncertainty_mm","note","source_sha256"].sort().join("|");
  const keys=Object.keys(rec).filter(k=>k!=="measurements_mm").sort().join("|");
  check(isObj(rec)&&keys===required,
   "observation fields must be explicit");
  check(taskIds.has(rec.task_id)&&!observed.has(rec.task_id),
   "unknown or duplicate task ID");
  observed.add(rec.task_id);
  validateCadReportedMeasurements(rec);
  check(methods.includes(rec.method)&&rec.method===taskMethods.get(rec.task_id)&&
   noControl(rec.part_revision)&&
   rec.part_revision.length<=120&&url(rec.evidence_url)&&
   date(rec.recorded_on)&&
   (rec.uncertainty_mm===null||
    (typeof rec.uncertainty_mm==="number"&&Number.isFinite(rec.uncertainty_mm)&&
     rec.uncertainty_mm>0&&rec.uncertainty_mm<=10))&&
   typeof rec.note==="string"&&rec.note.length>=12&&rec.note.length<=800&&
   (rec.source_sha256===null||
    (typeof rec.source_sha256==="string"&&/^[a-f0-9]{64}$/.test(rec.source_sha256)))&&
   (rec.method!=="METRIC_MEASUREMENT"||rec.uncertainty_mm!==null)&&
   (rec.method!=="CAD_SOURCE"||rec.source_sha256!==null),
   "field evidence needs explicit dated HTTPS pointer, revision, method and uncertainty");
 }
 return {submitted_unreviewed:observed.size,
  structured_readings_unreviewed:observations.records.reduce((n,r)=>
   n+(r.measurements_mm?.length??0),0),
  independently_verified:0,physical_approvals:0};
}
export function planCadCaptureCampaign(cad,requirements,makerDimensions,
 registry,{observations=null,kitAudit=null}={}){
 const catalog=validateCadCaptureRequirements(requirements);
 if(!cad)return {scope:"NO_SELECTED_COMPLETE_KIT_CAPTURE",kit_variant_id:null,
  roles:[],tasks:[],interfaces:[],status:"NO_KIT_SELECTED",
  task_count:catalog.required_task_count,reported_unreviewed:0,independently_verified:0};
 check(cad.scope==="BROWSER_PARAMETRIC_CAD_DISPLAY_UNQUALIFIED"&&
  cad.children?.length===7&&cad.additional_purchase_lines===0&&
  cad.physical_mates_verified===0,"only unqualified complete kit is accepted");
 check(cad.children.every((c,i)=>c.role===roles[i]),"capture roles must match assembly");
 check(registry?.assets&&Array.isArray(registry.assets)&&
  makerDimensions?.references&&Array.isArray(makerDimensions.references),
  "CAD source and geometry registries required");
 const variant=cad.selected_variant_id;
 const notes=observations??blankCadFieldObservations(variant);
 validateCadFieldObservations(notes,requirements,variant);
 const observed=new Map(notes.records.map(r=>[r.task_id,r]));
 const rolesOut=[],tasks=[];
 for(const req of requirements.requirements){
  const sourceRefs=makerDimensions.references.filter(r=>
   r.applies_to.includes(variant)&&r.roles.includes(req.role));
  const asset=registry.assets.find(a=>a.kit_variant_id===variant&&a.role===req.role);
  const roleTasks=req.tasks.map(t=>{
   const rec=observed.get(t.task_id);
   return {...t,role:req.role,status:rec?
    "FIELD_REPORTED_NOT_INDEPENDENTLY_VERIFIED":"EVIDENCE_REQUIRED",
    field_observation:rec?{method:rec.method,part_revision:rec.part_revision,
     evidence_url:rec.evidence_url,recorded_on:rec.recorded_on,
     uncertainty_mm:rec.uncertainty_mm,source_sha256:rec.source_sha256,
     note:rec.note,measurements_mm:rec.measurements_mm??null}:null,
    engineering_verified:false};
  });
  rolesOut.push({role:req.role,asset_candidate_id:asset?.asset_id??null,
   source_reference_urls:[...new Set(sourceRefs.map(s=>s.source_url))],
   tasks_missing:roleTasks.filter(t=>t.status==="EVIDENCE_REQUIRED").length,
   tasks_reported_unreviewed:roleTasks.filter(t=>t.field_observation).length,
   physical_geometry_verified:false,revision_confirmed:false});
  tasks.push(...roleTasks);
 }
 const interfaces=requirements.interfaces.map(i=>({
  ...i,dependent_task_ids:tasks.filter(t=>i.roles.includes(t.role)).map(t=>t.task_id),
  status:"REQUIRES_INDEPENDENT_INTERFACE_REVIEW",
  physical_fit_qualified:false,dynamic_clearance_qualified:false
 }));
 return {scope:"CAD_MEASUREMENT_WORKLIST_NOT_APPROVAL",
  kit_id:cad.kit_id,kit_variant_id:variant,roles:rolesOut,tasks,interfaces,
  task_count:tasks.length,missing_evidence:tasks.filter(t=>!t.field_observation).length,
  reported_unreviewed:tasks.filter(t=>t.field_observation).length,
  structured_readings_unreviewed:tasks.reduce((n,t)=>
   n+(t.field_observation?.measurements_mm?.length??0),0),
  source_reference_count:rolesOut.reduce((n,r)=>n+r.source_reference_urls.length,0),
  geometry_candidate_count:rolesOut.filter(r=>r.asset_candidate_id).length,
  received_kit_verified:false,
  seller_revision_conflict_unresolved:!!kitAudit?.inclusion_conflict,
  independently_verified:0,physical_mates_verified:0,
  dynamic_clearances_verified:0,procurement_authorized:false,
  fabrication_authorized:false,additional_purchase_lines:0,
  interpretation:"Reports track operator evidence submissions; only independent metrology, exact revisions and engineering review may qualify physical interfaces."};
}
