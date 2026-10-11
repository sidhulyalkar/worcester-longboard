// v1.3: comparable manufacturer-named retail setups and diverse research studies.
// Every entry is a dated reference, not a live quote or a safe construction instruction.
import {validatePartsRegistry,buildPickerStudy} from "./parts_picker_engine.mjs";
import {validateSupplierObservations,auditMakerOrderUnits} from "./offer_qualification.mjs";

const OFFER_SCOPE="HISTORICAL_RETAIL_SETUP_COMPARISONS_NO_CHECKOUT";
const STUDIES_SCOPE="DIVERSE_THREE_WAY_EQUIPMENT_STUDIES_NOT_RECOMMENDATIONS";
const AUTH=Object.freeze({procurement_authorized:false,fabrication_authorized:false,
 charging_authorized:false,powered_operation_authorized:false,
 generic_builder_may_promote_x1_authority:false});
const assert=(x,msg)=>{if(!x)throw Error("Outdoor comparisons: "+msg);};
const uniq=(list,key)=>assert(new Set(list.map(key)).size===list.length,"duplicate or ambiguous identities");
const dateOf=s=>{
 assert(typeof s==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(s),"invalid ISO date");
 const n=Date.parse(s+"T00:00:00Z");
 assert(Number.isFinite(n)&&new Date(n).toISOString().slice(0,10)===s,"invalid date value");
 return n;
};
const age=(t,now)=>Math.round((dateOf(now)-dateOf(t))/86400000);
const validHttps=(v)=>{
 try{const x=new URL(v);return x.protocol==="https:"&&!x.username&&!x.password&&!x.hash;}
 catch{return false;}
};
const allFalse=x=>x&&Object.keys(AUTH).every(k=>x[k]===false);
const productLookup=catalog=>{
 const m=new Map();
 for(const p of catalog.products)for(const v of p.variants)
  m.set(v.id,{product:p,variant:v});
 return m;
};
export function validateRetailRegistry(data,catalog){
 validatePartsRegistry(catalog);
 assert(data?.schema_version===1&&data.scope===OFFER_SCOPE,"invalid retail registry");
 assert(Array.isArray(data.offers)&&Array.isArray(data.merchants)&&
  data.comparison_policy&&allFalse(data.authority),"invalid retail contract");
 const policy=data.comparison_policy;
 assert(policy.max_age_days===30&&policy.match_requires_same_setup_signature===true&&
  policy.match_requires_same_package_kind===true&&
  policy.match_requires_same_selected_variant===true&&
  policy.permit_checkout===false&&policy.permit_inferred_inventory===false,
  "retail comparison policy was weakened");
 dateOf(data.reviewed_on);
 uniq(data.merchants,x=>x.id);
 uniq(data.offers,x=>x.id);
 const variants=productLookup(catalog);
 const shops=new Map(data.merchants.map(x=>[x.id,x]));
 for(const merchant of shops.values()){
  assert(/^[a-z][a-z0-9-]+$/.test(merchant.id)&&
    /^([a-z0-9-]+\.)+[a-z]{2,}$/.test(merchant.host)&&
    ["manufacturer","specialist_retailer"].includes(merchant.vendor_type),
    "invalid merchant identity");
 }
 const keys=[];
 for(const offer of data.offers){
  const seller=shops.get(offer.merchant_id);
  assert(seller&&validHttps(offer.source_url)&&
   new URL(offer.source_url).hostname===seller.host,
   "retail listing off registered seller host");
  assert(typeof offer.observed_setup==="string"&&offer.observed_setup.length>=20&&
   typeof offer.maker_setup_signature==="string"&&
   /^[A-Z0-9_]{12,120}$/.test(offer.maker_setup_signature)&&
   typeof offer.observed_package_kind==="string"&&
   /^[A-Z0-9_]{6,90}$/.test(offer.observed_package_kind),
   "retail package identity is missing");
  assert(Number.isFinite(offer.listed_amount_usd)&&offer.listed_amount_usd>0&&
   offer.currency==="USD"&&offer.observed_on===data.reviewed_on,
   "invalid dated USD price observation");
  assert(offer.exact_checkout_variant_verified===false&&
   offer.manufacturer_exact_revision_qualified===false&&
   offer.checkout_eligible===false&&offer.sales_tax_verified===false&&
   offer.shipping_total_verified===false&&offer.observed_stock_label===null,
   "retail observation cannot imply checkout, shipping or stock");
  assert(offer.seller_variant_sku===null||
    (typeof offer.seller_variant_sku==="string"&&offer.seller_variant_sku.length>=5),
   "malformed merchant SKU");
  assert(offer.pack_count===null||
    (Number.isInteger(offer.pack_count)&&offer.pack_count>=1&&offer.pack_count<=12),
    "unsupported or fractional seller package count");
  const match=offer.selected_variant_id===null?null:variants.get(offer.selected_variant_id);
  if(match){
   assert(offer.product_id===match.product.id&&
    match.product.domain_id==="skateboard_longboard"&&match.product.slot==="long_complete"&&
    offer.option_selection_verified_on_page===true&&offer.pack_count===1&&
    offer.seller_variant_sku===null,
    "listed setup does not match a known selected complete research option");
  }else{
   assert(offer.product_id===null&&offer.selected_variant_id===null&&
    offer.option_selection_verified_on_page===false,
    "unqualified variant may not inherit a matched seller setup");
  }
  dateOf(offer.observed_on);
  keys.push([offer.merchant_id,offer.selected_variant_id??"unselected",
    offer.maker_setup_signature,offer.observed_package_kind].join("|"));
 }
 uniq(keys,x=>x);
 // Each product's selected variant must imply a single coherent published setup
 // across merchants. Conflicting wheel size / package strings cannot match by price.
 const named=new Map();
 for(const o of data.offers.filter(x=>x.selected_variant_id)){
  const key=o.selected_variant_id;
  const signature=o.maker_setup_signature+"|"+o.observed_package_kind+"|"+o.pack_count;
  assert(!named.has(key)||named.get(key)===signature,
   "contradictory wheel/setup package under a selected variant");
  named.set(key,signature);
 }
 return {offers:data.offers.length,merchants:data.merchants.length,
  comparison_status:"HISTORICAL_UNVERIFIED_SETUP_ONLY",checkout_authorized:false};
}
export function compareRetailOffers(data,catalog,variantId,{as_of=data.reviewed_on}={}){
 validateRetailRegistry(data,catalog);
 dateOf(as_of);
 const product=productLookup(catalog).get(variantId);
 assert(product,"unknown selected research variant");
 const all=data.offers.filter(o=>o.selected_variant_id===variantId);
 const rows=all.map(o=>{
  const days=age(o.observed_on,as_of);
  const valid=days>=0&&days<=data.comparison_policy.max_age_days;
  return {id:o.id,merchant_id:o.merchant_id,
   merchant_name:data.merchants.find(m=>m.id===o.merchant_id).brand,
   source_url:o.source_url,setup:o.observed_setup,package:o.observed_package_kind,
   observed_on:o.observed_on,days_old:days,displayed_amount_usd:o.listed_amount_usd,
   included_seller_pack_count:o.pack_count,
   status:valid?"PUBLISHED_SETUP_REFERENCE":"EXPIRED_OR_FUTURE_HOLD",
   valid_for_historical_comparison:valid,
   exact_checkout_variant_verified:false,stock_verified:false,shipping_verified:false,
   total_with_tax_and_shipping:null};
 });
 const active=rows.filter(x=>x.valid_for_historical_comparison);
 const merchants=new Set(active.map(x=>x.merchant_id));
 const comparable=active.length>=2&&merchants.size>=2;
 const sorted=active.slice().sort((a,b)=>a.displayed_amount_usd-b.displayed_amount_usd||
  a.merchant_name.localeCompare(b.merchant_name));
 return {schema_version:1,scope:"PUBLISHED_MATCHED_SETUP_PRICE_REFERENCE_ONLY",
  variant_id:variantId,product_name:product.product.name,as_of,rows,
  status:comparable?"PUBLISHED_SETUP_COMPARISON_REVIEW":"SINGLE_OR_STALE_SOURCE_HOLD",
  compared_merchants:merchants.size,
  historical_listing_price_span_usd:comparable?{
   min:sorted[0].displayed_amount_usd,max:sorted.at(-1).displayed_amount_usd,
   gap:Math.round(100*(sorted.at(-1).displayed_amount_usd-sorted[0].displayed_amount_usd))/100
  }:null,
  current_price_quote:null,live_inventory_checked:false,orderable:false,
  taxes_shipping_and_returns_verified:false,exact_seller_sku_verified:false,
  authority:{...AUTH}};
}
export function validateBuildStudies(data,catalog){
 validatePartsRegistry(catalog);
 assert(data?.schema_version===1&&data.scope===STUDIES_SCOPE&&
  Array.isArray(data.studies)&&data.constraints&&allFalse(data.authority),
  "invalid build study contract");
 const restrictions=data.constraints;
 assert(Object.values(restrictions).every(x=>x===true),"build-study safety gates changed");
 uniq(data.studies,x=>x.id);
 const domains=catalog.assembly_templates.map(x=>x.domain_id);
 assert(data.studies.length===domains.length*3,"exactly three reference studies per active sport");
 for(const domain of domains){
  const subset=data.studies.filter(x=>x.domain_id===domain);
  assert(subset.length===3,"missing diverse configuration studies");
  uniq(subset,x=>JSON.stringify(Object.entries(x.selections).sort(([a],[b])=>a.localeCompare(b))));
  for(const entry of subset){
   assert(entry.authority==="UNQUALIFIED_VISUAL_AND_SOURCING_STUDY"&&
    typeof entry.title==="string"&&entry.title.length>5&&
    typeof entry.design_intent==="string"&&entry.design_intent.length>=10&&
    Array.isArray(entry.notes)&&entry.notes.length>=2,"unsafe or unsupported build description");
   const built=buildPickerStudy(catalog,{domain_id:entry.domain_id,selections:entry.selections});
   assert(built.report.status!=="INCOMPATIBLE_REFERENCE",
    "a manufacturer-incompatible build cannot be a positive study");
   assert(built.report.checkout_eligible===false&&
    built.graph.safety.physical_qualification==="NOT_QUALIFIED",
    "physical or purchase authority leaked into study");
  }
 }
 return {domains:domains.length,studies:data.studies.length,per_sport:3,
  all_physical_approvals:false};
}
export function composeResearchAlternatives(catalog,studies,supplierRegistry,retailRegistry,
 domain_id,{as_of=retailRegistry.reviewed_on,profile={}}={}){
 validateBuildStudies(studies,catalog);
 validateSupplierObservations(supplierRegistry,catalog);
 validateRetailRegistry(retailRegistry,catalog);
 dateOf(as_of);
 const entries=studies.studies.filter(x=>x.domain_id===domain_id);
 assert(entries.length===3,"active domain must have exactly three bounded studies");
 const cards=entries.map(entry=>{
  const built=buildPickerStudy(catalog,{domain_id,selections:entry.selections,profile});
  const units=auditMakerOrderUnits(built,supplierRegistry,catalog,{as_of});
  const matched=Object.values(entry.selections).flatMap(variantId=>
   compareRetailOffers(retailRegistry,catalog,variantId,{as_of}).rows
    .filter(x=>x.valid_for_historical_comparison));
  const size=built.selected_variants.filter(x=>x.dimensions_mm).map(x=>({
   slot:x.slot,variant_id:x.variant_id,dimensions_mm:x.dimensions_mm
  }));
  const findings=built.report.findings.slice();
  const measuredWeight=profile.mass_kg===undefined||profile.mass_kg===null||profile.mass_kg===""?
   null:Number(profile.mass_kg);
  if(measuredWeight!==null){
   assert(Number.isFinite(measuredWeight)&&measuredWeight>=15&&measuredWeight<=250,
    "invalid rider mass for reference range comparison");
   for(const [slot,variantId] of Object.entries(entry.selections)){
    const product=productLookup(catalog).get(variantId);
    const band=product?.variant.rider_mass_band_kg;
    if(band&&Array.isArray(band)&&band.length===2&&
      (measuredWeight<band[0]||measuredWeight>band[1])){
     findings.push({kind:"REVIEW",code:"MAKER_WEIGHT_BAND_REVIEW",message:
      entry.title+": documented manufacturer weight range "+band.join("–")+
      " kg excludes specified mass. Not an automatic size prescription."});
    }
   }
  }
  return {id:entry.id,title:entry.title,intent:entry.design_intent,notes:entry.notes,
   domain_id,selection:{...entry.selections},variant_count:Object.keys(entry.selections).length,
   indicative_published_dimensions:size,missing_required:built.report.missing_required_count,
   review_lines:built.report.review_required_count,findings,
   compatibility_status:built.report.status,source_coverage:matched.length,
   historical_retail_sources:matched.map(x=>({merchant_name:x.merchant_name,
     setup:x.setup,displayed_amount_usd:x.displayed_amount_usd,source_url:x.source_url})),
   historical_maker_subtotals:units.historical_partial_subtotals_by_currency,
   checkout_total:null,physical_fit_verified:false,
   electrical_authority:false,qualifications_complete:false};
 });
 const differences=[];
 for(let i=0;i<cards.length;i++)for(let j=i+1;j<cards.length;j++){
  const a=cards[i],b=cards[j];
  const changed=[...new Set([...Object.keys(a.selection),...Object.keys(b.selection)])]
   .filter(slot=>a.selection[slot]!==b.selection[slot]);
  differences.push({left:a.id,right:b.id,changed_slots:changed,
   meaningful_difference:changed.length>0,performance_claims_qualified:false});
 }
 return {schema_version:1,scope:"THREE_RESEARCH_CONFIGURATIONS_NOT_APPROVED_BUILDS",
  domain_id,as_of,cards,differences,
  current_order_total:null,all_assemblies_qualified:false,
  authority:{...AUTH}};
}
