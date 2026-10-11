import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {validateRetailRegistry,compareRetailOffers,validateBuildStudies,
 researchRelatedSellerListings,composeResearchAlternatives} from "../../builder/retail_build_comparison.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const read=s=>JSON.parse(fs.readFileSync(path.join(root,s),"utf8"));
const catalog=read("catalog/outdoor_parts_picker.v1.json");
const supplier=read("catalog/outdoor_supplier_observations.v1.json");
const retail=read("catalog/outdoor_retail_comparisons.v1.json");
const studies=read("catalog/outdoor_build_studies.v1.json");
const variant=(id)=>catalog.products.find(p=>p.id===id).variants[0].id;
test("retail registry only permits dated evidence with registered hosts and explicit no-cart policy",()=>{
 const result=validateRetailRegistry(retail,catalog);
 assert.equal(result.offers,6);assert.equal(result.merchants,3);
 assert.equal(result.checkout_authorized,false);
 assert.equal(validateBuildStudies(studies,catalog).studies,12);
 assert.ok(Object.values(studies.authority).every(x=>x===false));
});
test("V2 versus V3 trucks hold the apparently matched 105 mm wheel setup",()=>{
 const result=compareRetailOffers(retail,catalog,variant("loaded-tangent-complete"));
 assert.equal(result.rows.length,2);
 assert.equal(result.compared_merchants,0);
 assert.equal(result.status,"INCLUSION_REVISION_CONFLICT_HOLD");
 assert.equal(result.conflict.code,"INCLUDED_TRUCK_REVISION_MISMATCH");
 assert.equal(result.historical_listing_price_span_usd,null);
 assert.ok(result.rows.some(x=>x.advertised_truck_revision_claim.includes("V2")));
 assert.ok(result.rows.some(x=>x.advertised_truck_revision_claim.includes("V3")));
 assert.equal(result.current_price_quote,null);assert.equal(result.orderable,false);
 assert.ok(result.rows.every(x=>!x.stock_verified&&!x.shipping_verified));
});
test("85 mm Caguama setup is not falsely compared with 105 mm Dad Bod",()=>{
 const r=compareRetailOffers(retail,catalog,variant("loaded-tangent-caguama"));
 assert.equal(r.rows.length,2);
 assert.equal(r.rows[0].displayed_amount_usd,364);
 assert.equal(r.status,"INCLUSION_REVISION_CONFLICT_HOLD");
 assert.equal(r.historical_listing_price_span_usd,null);
 assert.equal(r.rows.some(x=>x.setup.includes("105mm")),false);
});
test("different 2026 ski-only and ski-plus-binding bundles are excluded from setup comparisons",()=>{
 const r=compareRetailOffers(retail,catalog,variant("atomic-bent90"));
 assert.equal(r.rows.length,0);assert.equal(r.status,"SINGLE_OR_STALE_SOURCE_HOLD");
 assert.ok(retail.offers.filter(o=>o.observed_setup.includes("2026 Atomic")).every(o=>
  o.selected_variant_id===null&&!o.option_selection_verified_on_page));
 assert.equal(retail.offers.filter(o=>o.seller_variant_sku?.startsWith("AA0030696")).length,2);
});
test("31-day old retail offer cannot be ranked as today's current retailer quote",()=>{
 const old=compareRetailOffers(retail,catalog,variant("loaded-tangent-complete"),{as_of:"2026-11-11"});
 assert.equal(old.status,"SINGLE_OR_STALE_SOURCE_HOLD");
 assert.equal(old.compared_merchants,0);
 assert.equal(old.historical_listing_price_span_usd,null);
 assert.ok(old.rows.every(x=>x.status==="EXPIRED_OR_FUTURE_HOLD"));
});
test("three research studies per sport preserve separate selections and source-backed 3D dimensions",()=>{
 for(const domain of catalog.assembly_templates.map(x=>x.domain_id)){
  const out=composeResearchAlternatives(catalog,studies,supplier,retail,domain);
  assert.equal(out.cards.length,3);
  assert.equal(out.differences.length,3);
  assert.ok(out.differences.every(x=>x.meaningful_difference));
  assert.equal(out.current_order_total,null);
  assert.equal(out.all_assemblies_qualified,false);
  assert.ok(out.cards.every(x=>!x.physical_fit_verified&&
   !x.qualifications_complete&&x.checkout_total===null));
 }
 const snow=composeResearchAlternatives(catalog,studies,supplier,retail,"snowboard");
 assert.ok(snow.cards.some(x=>x.indicative_published_dimensions.some(d=>d.dimensions_mm.length_mm===1450)));
 const mt=composeResearchAlternatives(catalog,studies,supplier,retail,"mountainboard");
 assert.ok(mt.cards.some(x=>x.selection.mt_trucks==="mbs-cnc420-12307"));
 assert.ok(mt.cards.every(x=>x.compatibility_status!=="INCOMPATIBLE_REFERENCE"));
 const long=composeResearchAlternatives(catalog,studies,supplier,retail,"skateboard_longboard");
 assert.equal(long.cards.filter(x=>x.source_coverage===2).length,0);
});
test("weight prompts only produce advisory manufacturer range review, not an automatic size choice",()=>{
 const out=composeResearchAlternatives(catalog,studies,supplier,retail,"snowboard",{profile:{mass_kg:105}});
 assert.ok(out.cards.some(x=>x.findings.some(f=>f.code==="MAKER_WEIGHT_BAND_REVIEW")));
 assert.ok(out.cards.every(x=>x.checkout_total===null));
 assert.throws(()=>composeResearchAlternatives(catalog,studies,supplier,retail,"snowboard",
  {profile:{mass_kg:999}}),/invalid rider mass/);
});
test("adversarial seller identity, mismatched package, and fake privileges fail closed",()=>{
 const mutate=fn=>{const o=structuredClone(retail);fn(o);return o;};
 const changes=[
  x=>x.offers[0].source_url="http://example.com/cheap",
  x=>x.offers[0].source_url="https://www.skatesusa.com/fake",
  x=>x.offers[0].product_id="loaded-tangent-caguama",
  x=>x.offers[0].selected_variant_id="loaded-tangent-caguama-85 mm Caguama 80a",
  x=>x.offers[0].maker_setup_signature="LOADED_TANGENT_CAGUAMA85_ORANGE80A",
  x=>x.offers[0].observed_package_kind="DECK_ONLY",
  x=>x.offers[0].pack_count=2,
  x=>x.offers[0].exact_checkout_variant_verified=true,
  x=>x.offers[0].checkout_eligible=true,
  x=>x.offers[0].sales_tax_verified=true,
  x=>x.offers[0].observed_on="2026-10-11",
  x=>x.offers[0].listed_amount_usd=-5,
  x=>x.offers.push({...x.offers[0]}),
  x=>x.comparison_policy.permit_checkout=true,
  x=>x.authority.procurement_authorized=true,
  x=>x.offers[0].seller_variant_sku="FAKE-SELLER-OPTION",
  x=>x.offers[0].advertised_truck_revision_claim="PARIS_V2_150MM_50_RAW",
  x=>x.offers[0].observed_setup=x.offers[0].observed_setup.replace("V3","V2"),
  x=>x.comparison_policy.require_identical_included_truck_revision=false,
  x=>x.offers[0].related_product_family_id="atomic-bent90",
  x=>x.offers[4].related_product_family_id="salomon-qst94",
  x=>x.offers[4].related_product_family_id="bogus-family",
  x=>x.offers[4].related_product_family_id=null
 ];
 changes.forEach((fn,i)=>assert.throws(()=>validateRetailRegistry(mutate(fn),catalog),
  /Outdoor comparisons:/,"retailer tamper case "+i));
});
test("duplicate builds, unfamiliar variants and unsafe status cannot be silently presented",()=>{
 const mutate=fn=>{const o=structuredClone(studies);fn(o);return o;};
 const changes=[
  x=>x.studies[1].selections={...x.studies[0].selections},
  x=>x.studies[0].selections.ski_pair="unheard-of",
  x=>x.studies[0].authority="CHECKOUT",
  x=>x.constraints.no_cart_generation=false,
  x=>x.studies[0].domain_id="unknown",
  x=>x.studies.pop()
 ];
 changes.forEach((fn,i)=>assert.throws(()=>validateBuildStudies(mutate(fn),catalog),
  /Outdoor comparisons:|Parts Picker:/,"study tamper case "+i));
});

test("alpine retailer bundles only appear with related ski model, never all skis",()=>{
 const atomic=researchRelatedSellerListings(retail,catalog,"atomic-bent90");
 assert.equal(atomic.rows.length,2);
 assert.ok(atomic.rows.every(x=>x.description.includes("Atomic Bent 90")));
 assert.equal(atomic.selected_size_quoted,false);
 assert.equal(atomic.checkout_eligible,false);
 const salomon=researchRelatedSellerListings(retail,catalog,"salomon-qst94");
 assert.deepEqual(salomon.rows,[]);
 const expired=researchRelatedSellerListings(retail,catalog,"atomic-bent90",
   {as_of:"2026-11-11"});
 assert.ok(expired.rows.every(x=>x.state==="EXPIRED_OR_FUTURE_REVIEW"));
 assert.throws(()=>researchRelatedSellerListings(retail,catalog,"none"),
   /known alpine ski family/);
});

test("the same published wheel setup is comparable only if independent seller kit revision claims agree",()=>{
 const consensus=structuredClone(retail);
 for(const o of consensus.offers.filter(x=>x.merchant_id==="skatesusa"&&
    x.selected_variant_id)){
  o.advertised_truck_revision_claim="PARIS_V3_150MM_50_POLISHED";
  o.observed_setup=o.observed_setup.replace("Paris V2", "Paris V3")
    .replace("(raw)","(polished)");
 }
 assert.equal(compareRetailOffers(consensus,catalog,
   variant("loaded-tangent-complete")).status,"PUBLISHED_SETUP_COMPARISON_REVIEW");
 assert.equal(compareRetailOffers(consensus,catalog,
   variant("loaded-tangent-complete")).compared_merchants,2);
 // Research-level comparison STILL cannot promise shipped items or order.
 assert.equal(compareRetailOffers(consensus,catalog,
   variant("loaded-tangent-complete")).orderable,false);
});
