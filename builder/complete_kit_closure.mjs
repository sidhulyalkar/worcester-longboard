// Research-only kit closure: manufacturer-advertised children are NOT verified
// delivered seller units, measured mates, or standalone shopping rows.
import {validatePartsRegistry} from "./parts_picker_engine.mjs";
import {validateRetailRegistry,compareRetailOffers} from "./retail_build_comparison.mjs";

const SCOPE="MAKER_COMPLETE_KIT_ADVERTISED_CONTENTS_NOT_PHYSICAL_RECEIPT";
const authority=["procurement_authorized","fabrication_authorized",
 "charging_authorized","powered_operation_authorized",
 "generic_builder_may_promote_x1_authority"];
const assert=(x,msg)=>{if(!x)throw Error("Kit closure: "+msg);};
const unique=items=>assert(new Set(items).size===items.length,"duplicate stable IDs");
const date=s=>{
 assert(typeof s==="string"&&/^\d{4}-\d\d-\d\d$/.test(s)&&
  Number.isFinite(Date.parse(s+"T00:00:00Z"))&&
  new Date(s+"T00:00:00Z").toISOString().startsWith(s),"invalid source date");
 return Date.parse(s+"T00:00:00Z");
};
export function validateMakerKitClaims(kits,catalog){
 validatePartsRegistry(catalog);
 assert(kits?.schema_version===1&&kits.scope===SCOPE&&
  Array.isArray(kits.kits)&&kits.kits.length===2,"kit contract mismatch");
 assert(authority.every(x=>kits.authority?.[x]===false),"kit source has unexpected approval");
 date(kits.reviewed_on);unique(kits.kits.map(x=>x.id));
 const known=catalog.products.flatMap(p=>p.variants.map(v=>({p,v})));
 const seen=[];
 for(const kit of kits.kits){
  const ref=known.find(x=>x.v.id===kit.variant_id);
  assert(ref&&ref.p.domain_id==="skateboard_longboard"&&
   ref.p.slot==="long_complete","kit must match one complete-maker research option");
  assert(kit.manufacturer==="Loaded Boards"&&
   ref.p.source_id==="loaded-tangent"+(ref.p.id==="loaded-tangent-caguama"?"-caguama":""),
   "maker product/kit identity mismatch");
  const maker=catalog.sources.find(x=>x.id===ref.p.source_id);
  assert(maker&&maker.url===kit.source_url&&
   new URL(kit.source_url).hostname==="www.loadedboards.com",
   "maker source URL differs from documented original maker product");
  assert(kit.reviewed_on===kits.reviewed_on&&
   kit.maker_catalog_seller_sku===null&&
   kit.maker_explicitly_lists_complete_kit===true&&
   kit.seller_checkout_option_verified===false&&
   kit.seller_stock_currently_verified===false&&
   kit.actual_received_kit_verified===false&&
   kit.measured_mechanical_interfaces_qualified===false,
   "source kit cannot claim seller confirmation or physical fit");
  const dims=kit.published_complete_dimensions_mm;
  assert(dims?.length_mm>500&&dims.width_mm>100&&
   Number.isFinite(dims.length_mm)&&Number.isFinite(dims.width_mm),
   "kit geometry must be a bounded published product envelope");
  assert(Array.isArray(kit.children)&&kit.children.length===7&&
   Array.isArray(kit.kit_level_unknowns)&&kit.kit_level_unknowns.length>2,
   "unknown kit child coverage");
  unique(kit.children.map(x=>x.id));
  const roles=new Set(kit.children.map(x=>x.role));
  assert(roles.size===7&&
   ["deck","zee_brackets","trucks","wheels","bearings",
   "deck_hardware","truck_hardware"].every(x=>roles.has(x)),
   "expected complete-kit reference roles missing");
  for(const child of kit.children){
   assert(["platform","mount","ground"].includes(child.group)&&
    child.id.startsWith(kit.id.replace("-complete-maker-claim","-"))&&
    typeof child.source_claim_label==="string"&&child.source_claim_label.length>=8,
    "kit child does not have source-specific identity");
   assert(child.status==="MAKER_LISTED_IN_COMPLETE_NOT_RECEIVED"&&
    child.maker_advertised_included===true&&
    child.actual_received_units===null&&
    child.confirmed_shipped_units===null&&
    child.unit_count_physically_verified===false&&
    child.included_hardware_revision_verified===false&&
    child.direct_seller_purchase_required===false,
    "kit inclusion must not imply received item counts or new seller rows");
   assert(child.expected_assembly_units===null||
    Number.isInteger(child.expected_assembly_units)&&
    child.expected_assembly_units>=1&&child.expected_assembly_units<=8,
    "unbounded predicted assembly item counts");
   assert(typeof child.expectation_basis==="string"&&
    child.expectation_basis.length>10,"physical count assumption not explained");
  }
  const wheel=kit.children.find(x=>x.role==="wheels").source_claim_label;
  assert(wheel.toLowerCase().includes(ref.v.label.slice(0,2))&&
   wheel.toLowerCase().includes(ref.v.label.split(" ")[2].toLowerCase()),
   "complete kit wheel configuration does not match selected variant");
  const truck=kit.children.find(x=>x.role==="trucks");
  assert(truck.source_claim_label.includes("Paris V3"),
   "maker truck-revision claim changed without new review");
  seen.push(kit.variant_id);
 }
 unique(seen);
 return {kit_count:kits.kits.length,advertised_child_count:kits.kits.reduce(
  (n,x)=>n+x.children.length,0),complete_delivered_kits_confirmed:0};
}
export function auditCompleteKitClaim(study,kits,catalog,retail,
 {as_of=kits.reviewed_on}={}){
 validateMakerKitClaims(kits,catalog);
 validateRetailRegistry(retail,catalog);
 date(as_of);
 const chosen=study?.selected_variants??[];
 const complete=chosen.filter(x=>x.slot==="long_complete");
 assert(complete.length<=1,"one complete seller kit maximum");
 if(!complete.length){
  return {schema_version:1,scope:"PUBLISHED_KIT_CLOSURE_NO_CART",
   status:"NO_COMPLETE_KIT_SELECTED",variant_id:null,rows:[],
   order_units:null,verified_kit_count:0,physical_connections_qualified:0,
   authority:Object.fromEntries(authority.map(x=>[x,false]))};
 }
 assert(study.graph.domain_id==="skateboard_longboard"&&
  chosen.every(x=>x.slot==="long_complete"),
  "complete longboard cannot double-purchase separate replacement parts");
 const variant=complete[0].variant_id;
 const kit=kits.kits.find(x=>x.variant_id===variant);
 assert(kit,"unsupported complete package, no automatic contents");
 const compared=compareRetailOffers(retail,catalog,variant,{as_of});
 const observations=compared.rows.map(x=>({
  merchant:x.merchant_name,revision:x.advertised_truck_revision_claim,
  price_usd_historical:x.displayed_amount_usd,
  original_url:x.source_url,status:x.status
 }));
 const rows=kit.children.map(child=>({
  child_id:child.id,role:child.role,label:child.label,
  source_claim:child.source_claim_label,
  source_url:kit.source_url,
  expected_assembly_units:child.expected_assembly_units,
  expectation_basis:child.expectation_basis,
  maker_claimed_included:true,
  exact_seller_pack_units:null,
  actual_received_units:null,
  status:"CLAIMED_INCLUDED_NOT_RECEIVED",
  add_independent_purchase_line:false,
  qualified_mount:false
 }));
 return {schema_version:1,scope:"PUBLISHED_KIT_CLOSURE_NO_CART",
  status:compared.conflict?"SELLER_PACKAGE_REVISION_CONFLICT_HOLD":
   "MAKER_DECLARED_COMPLETE_NOT_RECEIVED",
  kit_id:kit.id,variant_id:variant,source_url:kit.source_url,
  package_total_historical_usd:null,current_cart_total:null,
  maker_claimed_complete:true,actual_received_complete:false,
  physical_kit_contents_count_confirmed:0,
  children_expected:rows.length,children_source_claimed:rows.length,
  children_received_confirmed:0,rows,
  seller_page_revisions:observations,
  inclusion_conflict:compared.conflict,known_unknowns:kit.kit_level_unknowns,
  independent_additional_item_orders:0,
  actual_seller_unit_count:null,order_units:null,verified_kit_count:0,
  physical_connections_qualified:0,
  authority:Object.fromEntries(authority.map(x=>[x,false]))};
}
