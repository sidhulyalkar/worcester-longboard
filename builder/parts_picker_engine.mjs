// Outdoor Parts Picker research adapter.
// Converts ONLY canonical manufacturer-page selections into the existing unqualified
// assembly graph shape; does not create a cart, reliable stock, mates or physical authority.
import {evaluateSnowboardMountReference} from "./snowboard_mount_reference.mjs";
const SCOPE="EVIDENCE_AWARE_OUTDOOR_PARTS_RESEARCH_NO_CHECKOUT";
const AUTH=Object.freeze({procurement_authorized:false,fabrication_authorized:false,
 charging_authorized:false,powered_operation_authorized:false,
 generic_builder_may_promote_x1_authority:false});
const mapRole={
 ski_pair:["platform","ski_pair"],ski_binding:["mount","binding_pair"],
 ski_boot:["rider","boot_pair"],ski_poles:["utility","pole_pair"],
 ski_service:["utility","maintenance_tool"],
 snowboard:["platform","snowboard"],snow_binding:["rider","binding_pair"],
 snow_boot:["rider","boot_pair"],snow_hardware:["mount","mounting_disc"],
 long_complete:["platform","deck"],long_deck:["platform","deck"],
 long_trucks:["mount","truck_pair"],long_wheels:["ground","wheelset"],
 long_hardware:["mount","mounting_hardware"],
 mt_deck:["platform","deck"],mt_trucks:["mount","truck_pair"],
 mt_wheels:["ground","wheelset"],mt_bindings:["rider","binding_pair"],
 mt_brake:["control","brake_system"],mt_power:["power","battery"]
};
const groups=[
 {id:"platform",label:"Riding platform",shape:"platform",vector:[0,0]},
 {id:"mount",label:"Mounting / hardware",shape:"mount",vector:[-1.18,0.92]},
 {id:"ground",label:"Terrain contact",shape:"wheel",vector:[1.18,0.95]},
 {id:"rider",label:"Boots and rider interface",shape:"binding",vector:[0,-1.22]},
 {id:"control",label:"Braking / propulsion",shape:"control",vector:[1.55,-0.45]},
 {id:"power",label:"Power components",shape:"power",vector:[-1.55,-0.45]},
 {id:"utility",label:"Accessories / services",shape:"utility",vector:[0,1.55]}
];
const assert=(v,msg)=>{if(!v)throw Error("Parts Picker: "+msg);};
const unique=(arr,key)=>assert(new Set(arr.map(key)).size===arr.length,"duplicate IDs");
const safeLink=url=>{try{const x=new URL(url);return x.protocol==="https:"&&!x.username&&!x.password&&!x.hash;}catch{return false;}};
export function validatePartsRegistry(data){
 assert(data?.scope===SCOPE&&data.schema_version===1,"unsupported catalog");
 assert(Array.isArray(data.domains)&&Array.isArray(data.assembly_templates)&&
   Array.isArray(data.products)&&Array.isArray(data.sources)&&
   Array.isArray(data.vendors)&&Array.isArray(data.print_guidance),"missing registry sections");
 unique(data.domains,x=>x.id);unique(data.sources,x=>x.id);
 unique(data.vendors,x=>x.id);unique(data.products,x=>x.id);
 const sources=new Map(data.sources.map(x=>[x.id,x]));
 const templates=new Map(data.assembly_templates.map(x=>[x.domain_id,x]));
 unique(data.assembly_templates,x=>x.domain_id);
 for(const [id,t] of templates){
  assert(data.domains.some(x=>x.id===id),"template has unsupported sport");
  unique(t.slots,x=>x.id);
  for(const s of t.slots)assert(Boolean(mapRole[s.id]),"unknown assembly slot "+s.id);
 }
 for(const source of data.sources)assert(safeLink(source.url)&&
  source.source_kind==="manufacturer_page"&&source.reviewed_on===data.as_of,
  "untrusted or stale source reference");
 for(const vendor of data.vendors)assert(safeLink(vendor.url)&&
  vendor.stock_verified===false,"merchant stock cannot be inferred");
 for(const p of data.products){
  assert(templates.has(p.domain_id)&&templates.get(p.domain_id).slots.some(s=>s.id===p.slot),
   "product domain or slot not in registry");
  assert(sources.has(p.source_id),"product without manufacturer source");
  assert(p.checkout_eligible===false&&p.supplier_order_unit_verified===false&&
   p.revision_status==="FAMILY_OR_SIZE_REFERENCE_NOT_SKU_CONFIRMED","qualified-looking product");
  assert(Array.isArray(p.variants)&&p.variants.length>0,"missing variant study");
  unique(p.variants,x=>x.id);
  for(const v of p.variants){
   assert(typeof v.label==="string"&&v.label.length>0&&v.manufacturer_sku===null,
    "unsourced exact SKU claim");
   const d=v.dimensions_mm;
   if(d!==undefined&&d!==null){
    assert(Object.entries(d).every(([k,n])=>k.endsWith("_mm")&&
     Number.isFinite(n)&&n>0),"invalid typed metric dimension");
   }
  }
 }
 assert(Object.values(data.policy).every(v=>v===false),"catalog cannot grant physical or checkout rights");
 return {domains:data.domains.length,product_families:data.products.length,
  variant_choices:data.products.reduce((a,p)=>a+p.variants.length,0),
  suppliers:data.vendors.length,source_documents:data.sources.length};
}
const getVariant=(data,id)=>{
 for(const p of data.products){
  const v=p.variants.find(v=>v.id===id);if(v)return {product:p,variant:v};
 }
 return null;
};
function pairChecks(domain, selected, profile={}){
 const findings=[];
 const left=profile.left_mondo_mm==null?null:Number(profile.left_mondo_mm);
 const right=profile.right_mondo_mm==null?null:Number(profile.right_mondo_mm);
 if(left!==null&&right!==null&&left!==right)
  findings.push({kind:"REVIEW",message:"Different left/right Mondo measurements require independent boot fit and retention confirmation."});
 if(domain==="snowboard"){
  const board=selected.get("snowboard")?.product;
  const binding=selected.get("snow_binding");
  const boot=selected.get("snow_boot")?.product;
  if(board&&binding){
   const mount=evaluateSnowboardMountReference({
    board_mount:board.interface_claims?.board_mount,
    binding_mount:binding.product.interface_claims?.binding_mount,
    disc_family:binding.product.interface_claims?.disc_family,
    boot_retention:binding.product.interface_claims?.boot_retention
   });
   findings.push({kind:mount.verdict==="MANUFACTURER_REFERENCE_INCOMPATIBLE" ||
    mount.verdict==="REQUIRED_SPECIAL_DISC_MISSING"?"INCOMPATIBLE":"REVIEW",
    message:"Mounting-family reference: "+mount.verdict+". "+mount.reason});
  }
  if(binding&&boot&&binding.product.interface_claims.boot_retention!==
    boot.interface_claims.boot_retention){
   findings.push({kind:"INCOMPATIBLE",message:"Step On and conventional strap-boot retention families cannot be mixed."});
  }
  if(binding?.product.interface_claims.size_family==="MENS_STEP_ON"){
   const bands={S:[240,260],M:[265,285],L:[290,310],XL:[320,330]};
   const band=bands[binding.variant.label];
   if(band&&[left,right].some(v=>Number.isFinite(v)&&(v<band[0]||v>band[1]))){
    findings.push({kind:"REVIEW",message:"Recorded foot Mondo value is outside the published men's Step On binding boot-size band. These are FOOT measurements, not confirmed boot sizes. A fitting and model-specific chart are required."});
   }
  }
 }else if(domain==="alpine_ski"){
  const boot=selected.get("ski_boot")?.product;
  const binding=selected.get("ski_binding")?.product;
  const norm=boot?.interface_claims?.boot_sole_norm;
  const accepts=binding?.interface_claims?.accepted_boot_norms;
  if(binding&&boot){
   const published=norm==="ISO_5355_ADULT_FROM_MAKER_TEXT"?"ISO_5355_ADULT":norm;
   if(!published||published==="UNKNOWN"||!Array.isArray(accepts))
    findings.push({kind:"UNKNOWN",message:"Exact boot sole revision and binding-accepted norms are not confirmed."});
   else findings.push({kind:accepts.includes(published)?"REVIEW":"INCOMPATIBLE",
    message:accepts.includes(published)?
     "Manufacturer-level sole-norm reference overlaps, but exact binding model, boot shell/BSL, AFD/brake and release test remain unverified.":
     "Declared sole norm conflicts with reference binding accepted norms."});
  }
  findings.push({kind:"PROFESSIONAL_SERVICE",message:"Skis require exact model binding/brake, professional mounting, boot adjustment, function and release testing. No DIN algorithm or DIY binding jig."});
 }
 return findings;
}
export function buildPickerStudy(data,{domain_id,selections={},profile={}}={}){
 validatePartsRegistry(data);
 const template=data.assembly_templates.find(x=>x.domain_id===domain_id);
 assert(template,"no research template for this domain");
 assert(selections&&typeof selections==="object"&&!Array.isArray(selections),"invalid selection");
 const slots=new Map(template.slots.map(s=>[s.id,s]));
 for(const key of Object.keys(selections))assert(slots.has(key),"unrecognized selected slot");
 const chosen=new Map();
 for(const [slot,id] of Object.entries(selections)){
  if(id===null||id==="")continue;
  assert(typeof id==="string","invalid variant selection");
  const item=getVariant(data,id);
  assert(item&&item.product.domain_id===domain_id&&item.product.slot===slot,
   "variant does not match selected sport and slot");
  chosen.set(slot,item);
 }
 const hasComplete=chosen.has("long_complete");
 if(domain_id==="skateboard_longboard"&&hasComplete&&
   ["long_deck","long_trucks","long_wheels","long_hardware"].some(k=>chosen.has(k)))
  throw Error("Parts Picker: complete and component kit would double-count hardware");
 const worklist=template.slots.map(s=>{
  const item=chosen.get(s.id),isAlternative=s.status==="ALTERNATIVE";
  const coveredByComplete=domain_id==="skateboard_longboard"&&hasComplete&&s.id!=="long_complete";
  const selected=Boolean(item);
  const isRequired=s.status.startsWith("REQUIRED")||
    (domain_id==="skateboard_longboard"&&!hasComplete&&s.id!=="long_complete"&&s.status==="CONDITIONAL");
  const issue=coveredByComplete?"MAKER_CLAIMED_INCLUDED_IN_COMPLETE_REVIEW":
    selected?"SELECTED_FAMILY_REVIEW_REQUIRED":isRequired?"MISSING_REQUIRED_REFERENCE":
    isAlternative?"ALTERNATIVE_NOT_SELECTED":"OPTIONAL_NOT_SELECTED";
  return {slot:s.id,label:s.label,needed:s.needed,status:issue,
    variant_id:item?.variant.id??null,
    expected_assembly_amount:s.needed,
    exact_seller_order_units:null,package_contents_received_verified:false,
    exact_variant_revision_verified:false};
 });
 const sourceById=new Map(data.sources.map(x=>[x.id,x]));
 const components=template.slots.filter(s=>s.id!=="ski_service"&&
   s.id!=="long_complete"||chosen.has(s.id)).flatMap(s=>{
  const item=chosen.get(s.id);
  if(!item){
   if(s.status.startsWith("REQUIRED")||
    (domain_id==="skateboard_longboard"&&!hasComplete&&s.id!=="long_complete"&&s.status==="CONDITIONAL")){
    const [group_id,role]=mapRole[s.id];
    return [{id:"part:missing:"+s.id,component_id:"missing:"+s.id,
     group_id,role,label:"Unselected: "+s.label,order_index:0,
     manufacturer:null,sku_text:null,source_kind:"missing_required_reference",
     source_url:null,source_snapshot_id:null,exact_variant_verified:false,
     assembly_required_quantity:null,supplier_order_quantity:null,
     visual_proxy_only:true,inclusion_status:"NOT_INDEPENDENTLY_CONFIRMED",
     approval_status:"HOLD_REQUIRED_PART_UNSELECTED",reference_price_factor:null}];
   }
   return [];
  }
  const [group_id,role]=mapRole[s.id],source=sourceById.get(item.product.source_id);
  return [{id:"part:"+item.variant.id,component_id:item.variant.id,
   group_id,role,label:item.product.name+" · "+item.variant.label,
   order_index:0,manufacturer:item.product.brand,sku_text:null,
   source_kind:"maker_page_reference",source_url:source.url,source_snapshot_id:source.id,
   exact_variant_verified:false,assembly_required_quantity:null,
   supplier_order_quantity:null,visual_proxy_only:true,
   inclusion_status:"MANUFACTURER_CLAIM_UNVERIFIED_RECEIPT",
   approval_status:"HOLD_SIZE_REVISION_INTERFACE_PACKAGE_AND_MOUNT",reference_price_factor:null}];
 });
 const activeGroups=groups.filter(g=>components.some(c=>c.group_id===g.id))
  .map(g=>({...g,component_ids:components.filter(c=>c.group_id===g.id).map(c=>c.component_id),
   item_count:components.filter(c=>c.group_id===g.id).length,
   exact_assembly_geometry_verified:false}));
 const findings=pairChecks(domain_id,chosen,profile);
 const missing=worklist.filter(x=>x.status==="MISSING_REQUIRED_REFERENCE");
 const review=worklist.filter(x=>x.status==="SELECTED_FAMILY_REVIEW_REQUIRED");
 const holdCount=missing.length+review.length+findings.length;
 const report={schema_version:1,scope:"OUTDOOR_PARTS_ORDER_WORKLIST_NOT_A_CART",
  domain_id,source_snapshot_as_of:data.as_of,
  selection:Object.fromEntries([...chosen].map(([slot,x])=>[slot,x.variant.id])),
  rows:worklist,findings,missing_required_count:missing.length,review_required_count:review.length,
  conflicts:findings.filter(x=>x.kind==="INCOMPATIBLE"),
  qualified_supplier_order_lines:0,known_order_total_usd:null,
  status:findings.some(x=>x.kind==="INCOMPATIBLE")?"INCOMPATIBLE_REFERENCE":
   holdCount?"REVIEW_REQUIRED":"UNQUALIFIED",
  authority:{...AUTH},checkout_eligible:false,
  note:"Research worklist. Neither selection nor a manufacturer family-match confirms a safe/complete package or current stock."};
 const graph={schema_version:1,scope:"UNQUALIFIED_SEMANTIC_ASSEMBLY_EXPLODED_VIEW",
  subject_id:"parts-picker:"+domain_id,domain_id,label:domain_id.replaceAll("_"," ")+" · sourced part families",
  origin:"MAKER_FAMILY_SELECTION_RESEARCH",source_snapshot_as_of:data.as_of,
  groups:activeGroups,components,connections:[],
  package_inclusion_hypotheses:[],
  manufacturer_advertised_contents:[],manufacturer_mount_reference:null,
  unresolved_system_checks:[...worklist.filter(x=>x.status!=="OPTIONAL_NOT_SELECTED").map(x=>x.label+": "+x.status),
    ...findings.map(x=>x.message)],
  completeness:{catalog_components_included:components.length,
   unique_bom_component_ids:components.length,conceptual_assembly_groups:activeGroups.length,
   source_bound_variant_revisions_qualified:0,supplier_order_quantities_qualified:0,
   physical_connections_qualified:0},
  safety:{visual_geometry:"ILLUSTRATIVE_SEMANTIC_PROXY_ONLY",
   sequence:"NOT_INSTALLATION_INSTRUCTIONS",physical_qualification:"NOT_QUALIFIED",
   usable_for_fabrication:false,usable_for_mounting:false,usable_for_binding_release:false},
  authority:{...AUTH},
  note:"Maker-referenced product families and selected size labels. Meshes and exploded positions are illustrative, not measured assembly geometry, safe boot/binding fit or order units."};
 return {graph,report,selection:report.selection,selected_variants:[...chosen].map(([slot,x])=>({
  slot,product_id:x.product.id,variant_id:x.variant.id,
  label:x.product.name+" · "+x.variant.label,
  source_url:sourceById.get(x.product.source_id).url,
  dimensions_mm:x.variant.dimensions_mm??null,
  inclusion_claim:x.product.inclusion_claim
 }))};
}
