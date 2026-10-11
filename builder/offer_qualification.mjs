// v1.2 manufacturer listing unit audit.
// Evidence and read-only historical cost examples only. NEVER a cart, current
// stock quote, measured assembly, or professional ski-binding release approval.
import {validatePartsRegistry} from "./parts_picker_engine.mjs";

export const OFFER_SCOPE="MANUFACTURER_LISTING_OBSERVATIONS_RESEARCH_NOT_PURCHASE_QUOTES";
const AUDIT_SCOPE="HISTORICAL_MAKER_UNIT_AUDIT_NOT_A_CART";
const ALLOWED_IDENTITY=new Set([
 "PUBLISHED_MODEL_OPTION_CODE","FAMILY_CODE_NOT_SIZE_SKU","SELECTED_SETUP_NO_EXACT_SKU"
]);
const AUTH={procurement_authorized:false,fabrication_authorized:false,
 charging_authorized:false,powered_operation_authorized:false,
 generic_builder_may_promote_x1_authority:false};
const fail=message=>{throw Error("Offer audit: "+message);};
const check=(value,message)=>{if(!value)fail(message);};
const uniq=(items,field)=>{
 const keys=items.map(x=>x[field]);
 check(keys.every(x=>typeof x==="string"&&x.length>0)&&new Set(keys).size===keys.length,
  "duplicate or missing "+field);
};
const utcDay=value=>{
 if(typeof value!=="string"||!/^(\d{4})-(\d{2})-(\d{2})$/.test(value))
  fail("invalid UTC calendar date");
 const milliseconds=Date.parse(value+"T00:00:00Z");
 if(!Number.isFinite(milliseconds)||new Date(milliseconds).toISOString().slice(0,10)!==value)
  fail("impossible calendar date");
 return milliseconds;
};
const safeUrl=value=>{
 try{const x=new URL(value);
  return x.protocol==="https:"&&!x.username&&!x.password&&!x.hash&&
    x.hostname!=="localhost";
 }catch{return false;}
};
const priceValid=price=>price&&Number.isFinite(price.amount)&&price.amount>0&&
 /^[A-Z]{3}$/.test(price.currency)&&[
  "PUBLISHED_OPTION_LISTING","MAKER_FAMILY_PRICE_NOT_VARIANT_QUOTE"
 ].includes(price.price_scope);
const cloneAuthority=()=>({...AUTH});
const refKey=x=>x.domain_id+"|"+x.slot;
const REFERENCE_TARGETS=Object.freeze({
 "mountainboard|mt_deck":["deck",1],
 "mountainboard|mt_trucks":["truck",2],
 "mountainboard|mt_bindings":["individual_binding",2],
 "skateboard_longboard|long_complete":["complete_board",1],
 "snowboard|snowboard":["snowboard",1],
 "alpine_ski|ski_pair":["individual_ski",2]
});

export function validateSupplierObservations(registry,catalog){
 validatePartsRegistry(catalog);
 check(registry?.schema_version===1&&registry.scope===OFFER_SCOPE,
   "unknown observation registry");
 check(Array.isArray(registry.unit_requirements)&&
       Array.isArray(registry.listing_observations)&&registry.expiry_policy,
       "missing observation arrays or expiry policy");
 check(registry.expiry_policy.max_age_days===30&&
   registry.expiry_policy.no_inferred_stock===true&&
   registry.expiry_policy.shipping_tax_unknown===true&&
   registry.expiry_policy.no_automatic_checkout===true,
   "expiry or stock policy cannot be bypassed");
 check(registry.authority&&Object.keys(AUTH).every(k=>registry.authority[k]===false),
   "source cannot grant assembly or procurement authority");
 const reviewed=utcDay(registry.reviewed_as_of);
 const kinds=new Map();
 const products=new Map(catalog.products.map(x=>[x.id,x]));
 const sellers=new Map(catalog.vendors.map(x=>[x.id,x]));
 for(const r of registry.unit_requirements){
  check(typeof r.domain_id==="string"&&typeof r.slot==="string"&&
    Number.isInteger(r.items_per_assembly)&&r.items_per_assembly>=1&&
    r.items_per_assembly<=16&&typeof r.item_kind==="string"&&r.item_kind&&
    r.source==="RESEARCH_ASSEMBLY_TARGET_NOT_SELLER_ORDER",
    "invalid research assembly item requirements");
  check(catalog.assembly_templates.some(t=>t.domain_id===r.domain_id&&
    t.slots.some(s=>s.id===r.slot&&s.id!=="ski_service")),
    "assembly target not in canonical slots");
  const expected=REFERENCE_TARGETS[refKey(r)];
  check(expected&&expected[0]===r.item_kind&&expected[1]===r.items_per_assembly,
   "unapproved change to research assembly unit target");
  check(!kinds.has(refKey(r)),"duplicate assembly target");
  kinds.set(refKey(r),r);
 }
 check(kinds.size===Object.keys(REFERENCE_TARGETS).length,
   "missing required canonical unit targets");
 uniq(registry.listing_observations,"id");
 const selectedOfferKeys=new Set();
 for(const o of registry.listing_observations){
  const selectionKey=o.domain_id+"|"+o.slot+"|"+o.selected_variant_id;
  check(!selectedOfferKeys.has(selectionKey),
   "duplicate maker listings for a selected research variant require an explicit comparison policy");
  selectedOfferKeys.add(selectionKey);
  const product=products.get(o.product_id);
  // The product key exists independently from maker part code.
  check(product&&product.domain_id===o.domain_id&&product.slot===o.slot,
    "offer references the wrong product/sport/slot");
  check(product.variants.some(v=>v.id===o.selected_variant_id),
    "offer reference variant not in product");
  check(kinds.has(refKey(o)),"offer without known assembly target");
  const seller=sellers.get(o.seller_id);
  check(seller&&seller.kind==="manufacturer"&&safeUrl(o.source_url)&&
    new URL(o.source_url).hostname===new URL(seller.url).hostname,
    "offer source is not an original manufacturer host");
  check(o.manufacturer===product.brand&&ALLOWED_IDENTITY.has(o.selection_identity),
    "offer manufacturer or identity claim conflicts");
  check(o.maker_product_code===null||
    (typeof o.maker_product_code==="string"&&o.maker_product_code.length>0),
    "invalid maker product code");
  const unit=o.seller_unit,requirements=kinds.get(refKey(o));
  check(unit&&unit.item_kind===requirements.item_kind&&
    (unit.individual_items===null||
      (Number.isInteger(unit.individual_items)&&unit.individual_items>=1&&
       unit.individual_items<=16))&&
    typeof unit.pack_contents_confirmed_from_maker_page==="boolean",
    "wrong or unsupported seller pack units");
  if(unit.individual_items===null)
   check(unit.pack_contents_confirmed_from_maker_page===false,
     "cannot confirm an unknown package unit");
  if(o.selection_identity==="PUBLISHED_MODEL_OPTION_CODE")
   check(o.maker_product_code!==null&&unit.individual_items!==null&&
     unit.pack_contents_confirmed_from_maker_page===true&&
     priceValid(o.displayed_price)&&
     o.displayed_price.price_scope==="PUBLISHED_OPTION_LISTING",
     "item-specific listing lacks published maker code, pack or price");
  else check(o.displayed_price===null||
    (priceValid(o.displayed_price)&&
     o.displayed_price.price_scope==="MAKER_FAMILY_PRICE_NOT_VARIANT_QUOTE"),
    "family offer may not claim item-level price");
  const snapshot=utcDay(o.observed_on);
  check(snapshot<=reviewed,"observation after registry review");
  check(o.availability_state==="NOT_REVALIDATED"&&
    o.receipt_contents_inspected===false&&
    o.source_identity_exact_variant_verified===false&&
    o.financial_checkout_authorized===false&&o.physical_fit_verified===false,
    "maker listing cannot promote stock, received contents, or safety");
  check(Array.isArray(o.package_claims)&&
    o.package_claims.every(x=>typeof x==="string"&&x.length>=5),
    "missing explanatory contents evidence");
 }
 return {scope:OFFER_SCOPE,observations:registry.listing_observations.length,
  targets:kinds.size,reviewed_as_of:registry.reviewed_as_of,authority:cloneAuthority()};
}

// Human review of maker pages can evidence historical pack quantities.
// Never returns any current stock, delivery promise, tax, or order permission.
export function auditMakerOrderUnits(study,registry,catalog,{as_of=registry?.reviewed_as_of}={}){
 validateSupplierObservations(registry,catalog);
 check(study?.report?.scope==="OUTDOOR_PARTS_ORDER_WORKLIST_NOT_A_CART"&&
   study.graph?.scope==="UNQUALIFIED_SEMANTIC_ASSEMBLY_EXPLODED_VIEW"&&
   study.report.checkout_eligible===false&&
   Object.keys(AUTH).every(k=>study.report.authority?.[k]===false&&
     study.graph.authority?.[k]===false),
   "source study is not authority locked");
 check(study.graph.domain_id===study.report.domain_id,"graph/report sport mismatch");
 check(JSON.stringify(study.selection)===JSON.stringify(study.report.selection),
   "selected variant state is not the audited selection");
 // Structured cloning and snapshots can preserve aliasing between the two
 // objects above. Cross-check the independent BOM rows + selected variants.
 check(Array.isArray(study.report.rows)&&Array.isArray(study.selected_variants),
   "missing independent selection receipts");
 const rowsBySlot=new Map();
 for(const row of study.report.rows){
  check(typeof row.slot==="string"&&!rowsBySlot.has(row.slot),
   "duplicate or invalid worklist slot");
  rowsBySlot.set(row.slot,row);
 }
 const variantBySlot=new Map();
 for(const v of study.selected_variants){
  check(typeof v.slot==="string"&&!variantBySlot.has(v.slot),
   "duplicate independent selected variant");
  variantBySlot.set(v.slot,v);
  check(rowsBySlot.get(v.slot)?.variant_id===v.variant_id&&
    study.report.selection[v.slot]===v.variant_id&&
    study.graph.components.some(x=>x.component_id===v.variant_id),
    "audited selection differs from independent graph/worklist/variant identity");
 }
 for(const [slot,value] of Object.entries(study.report.selection)){
  check(rowsBySlot.get(slot)?.variant_id===value&&
    variantBySlot.get(slot)?.variant_id===value,
    "audited selection does not match source worklist receipt");
 }
 const now=utcDay(as_of);
 const targets=new Map(registry.unit_requirements.map(x=>[refKey(x),x]));
 const selected=new Map(study.selected_variants.map(x=>[x.slot,x]));
 const observations=registry.listing_observations;
 const conflict=study.report.conflicts?.length>0;
 const lines=study.report.rows.map(row=>{
  const v=selected.get(row.slot);
  const target=targets.get(study.report.domain_id+"|"+row.slot);
  const o=v?observations.find(x=>x.selected_variant_id===v.variant_id&&
    x.slot===row.slot&&x.domain_id===study.report.domain_id):null;
  const line={slot:row.slot,label:row.label,selected_variant_id:row.variant_id,
   source_url:o?.source_url??null,maker_product_code:o?.maker_product_code??null,
   selected_option_identity:o?.selection_identity??null,
   required_item_count:target?.items_per_assembly??null,
   seller_unit_items:o?.seller_unit?.individual_items??null,
   item_kind:target?.item_kind??null,
   reference_pack_count:null,reference_extended_amount:null,
   reference_currency:null,
   reference_pricing_status:"NO_VARIANT_QUOTE",
   order_authorized:false,stock_verified:false,physical_fit_verified:false,
   status:"NO_MAKER_LISTING_OBSERVATION",
   review_actions:[]};
  if(row.status==="MAKER_CLAIMED_INCLUDED_IN_COMPLETE_REVIEW"){
   line.status="MAKER_KIT_CONTENTS_RECEIPT_HOLD";
   line.review_actions.push("Verify exact delivered contents of the complete kit before adding standalone parts");
   return line;
  }
  if(!v){
   line.status=row.slot==="ski_service"?"PROFESSIONAL_SERVICE_NOT_PARTS_ORDER":
     row.status==="MISSING_REQUIRED_REFERENCE"?"REQUIRED_COMPONENT_NOT_SELECTED":"OPTIONAL_NOT_SELECTED";
   return line;
  }
  if(!o){
   line.review_actions.push("Find a size/option-matched original maker listing and a seller unit count");
   return line;
  }
  const age=Math.round((now-utcDay(o.observed_on))/86400000);
  line.observed_on=o.observed_on;
  line.observation_age_days=age;
  line.maker_note=o.remarks;
  if(age<0||age>registry.expiry_policy.max_age_days){
   line.status="EXPIRED_OR_FUTURE_LISTING";
   line.review_actions.push("Refresh original manufacturer listing before reasoning about order units");
   return line;
  }
  if(conflict){
   line.status="KNOWN_ASSEMBLY_INTERFACE_CONFLICT";
   line.review_actions.push("Resolve incompatible physical-interface selection before unit planning");
   return line;
  }
  if(o.selection_identity!=="PUBLISHED_MODEL_OPTION_CODE"){
   line.status="EXACT_SELECTED_OPTION_CODE_NOT_ESTABLISHED";
   line.review_actions.push("Resolve exact model-year/size/finish seller option code, not the family product code");
   return line;
  }
  if(!target||o.seller_unit.individual_items===null||
     o.seller_unit.pack_contents_confirmed_from_maker_page!==true){
   line.status="SELLER_PACK_QUANTITY_UNKNOWN";
   line.review_actions.push("Confirm manufacturer-declared individual units in a single seller package");
   return line;
  }
  const count=Math.ceil(target.items_per_assembly/o.seller_unit.individual_items);
  line.status="HISTORICAL_MAKER_UNIT_REFERENCE_ONLY";
  line.reference_pack_count=count;
  line.reference_pricing_status="HISTORICAL_LISTED_PRICE_NOT_CURRENT_QUOTE";
  line.reference_extended_amount=
    Math.round(100*o.displayed_price.amount*count)/100;
  line.reference_currency=o.displayed_price.currency;
  line.review_actions.push(
   "Confirm revision, present availability, tax, shipping and exact received package contents before ordering");
  line.review_actions.push(
   "Independent mechanical fit/clearance review remains required, even if maker quantities are documented");
  return line;
 });
 const priced=lines.filter(x=>x.reference_extended_amount!==null);
 const amounts={};
 for(const x of priced){
  amounts[x.reference_currency]=Math.round(100*
   ((amounts[x.reference_currency]??0)+x.reference_extended_amount))/100;
 }
 return {
  schema_version:1,scope:AUDIT_SCOPE,as_of,
  source_registry_as_of:registry.reviewed_as_of,
  domain_id:study.report.domain_id,
  subject_id:study.graph.subject_id,
  rows:lines,
  matched_historical_unit_lines:priced.length,
  all_required_items_resolved:false,
  historical_partial_subtotals_by_currency:amounts,
  actual_checkout_total:null,live_stock_verified:false,delivery_quoted:false,
  tax_and_shipping_quoted:false,qualified_supplier_order_lines:0,
  physical_connection_qualified:false,professional_release_authorized:false,
  has_declared_compatibility_conflict:conflict,
  authority:cloneAuthority(),
  note:"Historical manufacturer part/pack evidence only. Partial sums omit unknown offers, accessories, taxes, shipping, mounts and services. Do not order or build from this report."
 };
}
