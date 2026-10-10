// Auditable, revision-aware planning packet. This is not an assembly, purchase,
// charging or powered-operation release. Do not infer a revision from a SKU.
const AUTHORITY=Object.freeze({
  procurement_authorized:false,fabrication_authorized:false,
  charging_authorized:false,powered_operation_authorized:false,
  generic_builder_may_promote_x1_authority:false
});
const POWER=new Set(["battery","charger","esc","motor","drive"]);
const STAGE=[
  ["study","Study / verify the source","STUDY_ONLY","Beginner: identify selected variants, prices, manufacturer instructions and source dates"],
  ["receive","Receiving and variant inspection","HOLD_REVISION","Document actual manufacturer, SKU, label photos, revision markings, included pieces and condition before any assembly"],
  ["fit","Mechanical interface measurement","HOLD_MEASURE","Measure deck/truck mounts, axle/hub fit, retention, steering sweep, brake and drive clearance against exact received revisions"],
  ["mechanical","Mechanical construction readiness","QUALIFICATION_REQUIRED","Use manufacturer instructions, specified fasteners and independent mechanical inspection only after separate qualification"],
  ["electrical","Electrical system integration","POWER_GATED","Qualified electrical specialist only; use a separately approved pack, BMS, fuse, wiring enclosure and matched charger"],
  ["release","Independent validation and release","QUALIFICATION_REQUIRED","Obtain independent structural, braking and controls verification under a separately authorized protocol"]
];
const identity=fields=>JSON.stringify(fields.map(value=>value===undefined?null:value));
const numeric=value=>typeof value==="number" && Number.isFinite(value)?value:null;
const two=value=>Math.round((value+Number.EPSILON)*100)/100;
const orderedUnique=values=>[...new Set(values)].sort();
function priceSnapshot(part){
  const price=part.price || null,qty=numeric(price?.qty) ?? 1;
  let min=null,max=null;
  if(price && qty>0){
    if(["unit","ceiling"].includes(price.kind) && numeric(price.unit_price_usd)!==null)
      min=max=two(price.unit_price_usd*qty);
    else if(price.kind==="range" && numeric(price.min_usd)!==null && numeric(price.max_usd)!==null){
      min=two(price.min_usd*qty);
      max=two(price.max_usd*qty);
    }
  }
  const sourced=["vendor","retailer","manufacturer"].includes(part.source?.kind) &&
    !!part.source?.snapshot_id && !!part.source?.as_of;
  return {
    kind:price?.kind || "UNPRICED",
    pricing_reference_qty:price?.qty ?? null,
    assembly_required_qty:null,
    quantity_authority:"CATALOG_PRICE_MULTIPLIER_NOT_ASSEMBLY_QUANTITY",
    min_usd:min,max_usd:max,
    price_basis:min===null?"UNKNOWN":sourced?"DATED_SOURCE_REFERENCE_USD":"UNSOURCED_PLANNING_ESTIMATE_USD",
    native_price_snapshot:part.source?.native_price_snapshot || null,
    availability:"UNKNOWN_NOT_LIVE",
    quote_verified:false
  };
}
export function buildBuildPassport(candidate,bundle){
  if(!candidate?.id || !candidate.evidence || !Array.isArray(candidate.bom) ||
    !bundle?.catalog?.components)throw new Error("Passport requires a scored candidate and catalog");
  const index=new Map(bundle.catalog.components.map(row=>[row.id,row]));
  const health=new Map((bundle.catalogHealth?.component_health || []).map(row=>[row.component_id,row]));
  const parts=candidate.bom.map(row=>{
    const c=index.get(row.component_id);
    if(!c)throw new Error("Missing catalog part "+row.component_id);
    const h=health.get(c.id),source=c.source || {};
    const revision=typeof c.revision==="string" && c.revision.trim()?c.revision:null;
    const datedSource=source.snapshot_id && source.as_of && source.url;
    const partIdentity=identity([c.id,c.sku||null,revision,source.snapshot_id||null,source.as_of||null]);
    return {
      component_id:c.id,category:c.category,label:c.label,manufacturer:c.manufacturer || null,
      sku_text:c.sku || null,
      catalog_revision:revision,
      revision_status:"EXACT_VARIANT_REVISION_UNVERIFIED",
      variant_identity_key:partIdentity,
      procurement_state:c.procurement_state,
      evidence_state:c.evidence_state,
      supplier:{
        name:source.seller || null,source_url:source.url || null,
        source_kind:source.kind || "UNKNOWN",snapshot_id:source.snapshot_id || null,
        catalog_as_of:source.as_of || null,verified_as_of:h?.verified_as_of || null,
        source_health:h?.status || "HEALTH_UNAVAILABLE",
        verified_specific_revision:false,verified_current_stock:false,
        source_status:datedSource?"DATED_REFERENCE_ONLY":"INCOMPLETE_OR_NON_VENDOR_REFERENCE"
      },
      price:priceSnapshot(c),
      included_by_donor:Array.isArray(c.includes)?[...c.includes]:[],
      hold_reason:c.hold_reason || null,
      manufacturer_instructions_url:null,
      instructions_state:"MANUFACTURER_INSTRUCTIONS_NOT_INDEXED",
      receiving_checks:[
        "Record exact received brand/SKU/revision and photograph markings",
        "Verify item counts, contents, damage and included fasteners against maker documentation",
        "Obtain revision-matched installation and torque instructions"
      ]
    };
  });
  const partIndex=new Map(parts.map(p=>[p.component_id,p]));
  const depKeys=new Map((candidate.evidence.source_evidence || []).map(x=>[x.component_id,
    identity([x.component_id,null,null,x.snapshot_id||null,x.verified_as_of||null])]));
  const interfaces=(candidate.evidence.interfaces || []).map(rule=>{
    const ids=[rule.a,rule.b].sort();
    return {
      id:rule.id,component_ids:ids,reference_state:rule.state,
      catalog_rule_origin:rule.evidence_kind || "UNKNOWN_RULE_SOURCE",
      reason:rule.reason,variant_binding:ids.map(id=>({
        component_id:id,identity_key:partIndex.get(id)?.variant_identity_key ||
          depKeys.get(id) || null,
        direct_bom_part:partIndex.has(id)
      })),
      revision_evidence_state:"EXACT_VARIANT_CONFIRMATION_REQUIRED",
      valid_for_physical_build:false
    };
  }).sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0);
  const sourced=parts.filter(p=>p.price.min_usd!==null &&
    p.price.price_basis==="DATED_SOURCE_REFERENCE_USD");
  const planning=parts.filter(p=>p.price.min_usd!==null &&
    p.price.price_basis==="UNSOURCED_PLANNING_ESTIMATE_USD");
  const sum=(list,key)=>two(list.reduce((v,p)=>v+p.price[key],0));
  const powered=parts.some(p=>POWER.has(p.category)) ||
    candidate.capabilities?.drive_path!=="NOT_PRESENT" &&
    candidate.capabilities?.drive_path!==undefined;
  const stages=STAGE.map(([id,label,status,skill])=>({
    id,label,status:id==="electrical"&&!powered?"NOT_APPLICABLE":
      id==="release"&&powered?"POWER_GATED":status,
    skills_and_work:skill,
    required_evidence:id==="study"?"Dated vendor sources and variant-specific manuals":
      id==="receive"?"Receiving photos and exact counts":
      id==="fit"?"Dimensioned measurements, brake and retention evidence":
      id==="mechanical"?"Qualified drawings, torque and inspection records":
      id==="electrical"?"Professional electrical/battery/charger review":
      "Independent qualification artifacts and formal authority"
  }));
  return {
    schema_version:1,scope:"NON_AUTHORITATIVE_BUILD_PASSPORT",
    candidate_id:candidate.id,candidate_label:candidate.label,
    origin:candidate.origin || "CURATED",
    study_identity_key:identity([candidate.id,...parts.map(p=>p.variant_identity_key).sort()]),
    parts,
    interface_claims:interfaces,
    sourcing:{
      sourced_usd_snapshot:{min:sum(sourced,"min_usd"),max:sum(sourced,"max_usd")},
      unsourced_planning_usd_estimate:{min:sum(planning,"min_usd"),max:sum(planning,"max_usd")},
      native_currency_snapshots:parts.filter(p=>p.price.native_price_snapshot).map(p=>({
        component_id:p.component_id,raw_text:p.price.native_price_snapshot
      })),
      unpriced_ids:parts.filter(p=>p.price.min_usd===null).map(p=>p.component_id),
      all_in_total_usd:null,all_in_status:"UNKNOWN_INCOMPLETE_COST_AND_QUANTITY",
      purchase_quantities_confirmed:false,live_stock_verified:false,
      exclusions:["shipping","sales tax/duties","tools and PPE","professional assembly and electrical inspection","testing/validation","quantity and inclusion audit"]
    },
    assembly:{
      powered:Boolean(powered),
      stages,
      instructions_status:"REQUIRES_EXACT_VARIANT_MANUFACTURER_MANUALS",
      receiving_inspection_complete:false,
      electrical_integration_authorized:false,
      chassis_assembly_authorized:false,
      note:"Assembly planning/learning only. Never energize or charge from this guide."
    },
    unresolved:{
      blocker_reasons:[...(candidate.blockers||[])],
      measurement_worklist:(candidate.evidence.measurement_worklist||[]).map(x=>({
        id:x.id,component_ids:[...x.component_ids],state:x.state,
        question:x.question,evidence_required:x.evidence_required
      })),
      unverified_revision_part_ids:parts.filter(p=>p.revision_status!=="VERIFIED_EXACT_REVISION")
        .map(p=>p.component_id),
      missing_manual_part_ids:parts.filter(p=>!p.manufacturer_instructions_url).map(p=>p.component_id),
      source_refresh_ids:parts.filter(p=>p.supplier.source_health!=="SOURCE_FRESH")
        .map(p=>p.component_id),
      donor_inclusion_review_ids:parts.filter(p=>p.included_by_donor.length).map(p=>p.component_id)
    },
    physical_qualification:"NOT_QUALIFIED",
    authority:{...AUTHORITY},
    disclaimer:"Catalog reference, SKU text, vendor listing and source price do not specify a revision-qualified, compatible or buyable kit."
  };
}
export function proposePassportRevisionChange(passport,componentId,newRevision){
  if(passport?.scope!=="NON_AUTHORITATIVE_BUILD_PASSPORT" ||
    !passport.parts?.some(p=>p.component_id===componentId))
    throw new Error("Choose a component from the passport");
  if(typeof newRevision!=="string" || !newRevision.trim() || newRevision.length>120)
    throw new Error("Enter a bounded, explicit proposed revision");
  const result=JSON.parse(JSON.stringify(passport));
  const part=result.parts.find(p=>p.component_id===componentId);
  part.proposed_revision=newRevision.trim();
  part.revision_status="PROPOSED_REVISION_REQUIRES_NEW_VENDOR_EVIDENCE";
  part.variant_identity_key=identity([part.component_id,part.sku_text,part.proposed_revision,
    null,null]);
  part.supplier.verified_specific_revision=false;
  part.supplier.verified_current_stock=false;
  part.supplier.source_status="PROPOSED_REVISION_NOT_VERIFIED_BY_SNAPSHOT";
  const invalidated=[];
  for(const claim of result.interface_claims){
    if(claim.component_ids.includes(componentId)){
      claim.revision_evidence_state="INVALIDATED_BY_REVISION_CHANGE";
      claim.valid_for_physical_build=false;
      invalidated.push(claim.id);
    }
  }
  result.study_identity_key=identity([result.candidate_id,...result.parts.map(p=>p.variant_identity_key).sort()]);
  result.change_receipt={
    component_id:componentId,proposed_revision:part.proposed_revision,
    invalidated_interface_ids:invalidated.sort(),
    required_action:"Refresh vendor variant evidence, repeat affected dimensional interface checks and independently requalify physical system."
  };
  result.physical_qualification="NOT_QUALIFIED";
  return result;
}
