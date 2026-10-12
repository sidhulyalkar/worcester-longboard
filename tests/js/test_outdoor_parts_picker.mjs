import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {validatePartsRegistry,buildPickerStudy} from "../../builder/parts_picker_engine.mjs";
import {renderExplodedAssemblySvg} from "../../builder/exploded_renderer.mjs";
import {planExplodedScene} from "../../builder/exploded_scene_model.mjs";
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const read=p=>JSON.parse(fs.readFileSync(path.join(ROOT,p),"utf8"));
const catalog=read("catalog/outdoor_parts_picker.v1.json");
const canonical=read("catalog/outdoor_equipment_domains.v0.json");
const variant=(productId,index=0)=>catalog.products.find(x=>x.id===productId).variants[index].id;
const study=(domain_id,selections={},profile={})=>
 buildPickerStudy(catalog,{domain_id,selections,profile});

test("part picker seed matches all canonical domains and has maker-provenance",()=>{
 const coverage=validatePartsRegistry(catalog);
 assert.ok(coverage.product_families>=20);
 assert.ok(coverage.variant_choices>=30);
 assert.ok(coverage.suppliers>=15);
 assert.deepEqual(new Set(catalog.domains.map(x=>x.id)),
  new Set(canonical.domains.map(x=>x.id)));
 assert.ok(catalog.products.every(p=>p.variants.every(v=>v.manufacturer_sku===null)));
 assert.ok(catalog.sources.every(s=>s.source_kind==="manufacturer_page"));
 assert.ok(catalog.vendors.every(v=>v.stock_verified===false));
 assert.ok(Object.values(catalog.policy).every(v=>v===false));
 const taxOnly=catalog.domains.filter(x=>x.coverage.includes("TAXONOMY"));
 assert.equal(taxOnly.length,5);
 assert.ok(taxOnly.every(d=>!catalog.products.some(p=>p.domain_id===d.id)));
});
test("unselected ski scene includes visible platform/binding/boot review placeholders",()=>{
 const x=study("alpine_ski");
 assert.equal(x.report.qualified_supplier_order_lines,0);
 assert.equal(x.report.known_order_total_usd,null);
 assert.ok(x.report.missing_required_count>=3);
 assert.ok(x.graph.components.some(p=>p.role==="ski_pair"));
 assert.ok(x.graph.components.some(p=>p.role==="binding_pair"));
 assert.ok(x.graph.components.some(p=>p.role==="boot_pair"));
 assert.ok(x.graph.components.every(p=>p.visual_proxy_only&&!p.exact_variant_verified));
 assert.ok(Object.values(x.graph.authority).every(v=>v===false));
 assert.equal(x.graph.safety.usable_for_binding_release,false);
 assert.match(renderExplodedAssemblySvg(x.graph,{explode:65}),/PHYSICAL FIT UNVERIFIED/);
 const planned=planExplodedScene(x.graph,{separation:100});
 assert.equal(planned.units,"ARBITRARY_VISUAL_UNITS");
 assert.equal(planned.physical_fit_verified,false);
});
test("selected Atomic ski, GW binding and alpine boot remain release gated",()=>{
 const x=study("alpine_ski",{ski_pair:variant("atomic-bent90"),
  ski_binding:variant("tyrolia-gw-ref"),ski_boot:variant("salomon-alpha130")});
 assert.equal(x.report.missing_required_count,1); // professional mounting service
 assert.ok(x.report.findings.some(f=>f.kind==="PROFESSIONAL_SERVICE"));
 assert.ok(x.report.findings.some(f=>f.kind==="REVIEW" && /sole-norm/.test(f.message)));
 assert.equal(x.report.checkout_eligible,false);
 assert.equal(x.report.known_order_total_usd,null);
 assert.equal(x.graph.completeness.supplier_order_quantities_qualified,0);
 assert.equal(x.graph.completeness.source_bound_variant_revisions_qualified,0);
 assert.ok(x.selected_variants.some(v=>v.dimensions_mm?.length_mm===1570));
});
test("Step On versus strap boots are an explicit incompatibility",()=>{
 const x=study("snowboard",{snowboard:variant("burton-goodcompany"),
  snow_binding:variant("burton-stepon"),snow_boot:variant("burton-strap-boot-ref")});
 assert.equal(x.report.status,"INCOMPATIBLE_REFERENCE");
 assert.ok(x.report.conflicts.some(x=>/retention families/.test(x.message)));
 assert.equal(x.report.checkout_eligible,false);
});
test("Step On study tests foot lengths as chart REVIEW, never auto-sizes or claims fit",()=>{
 const x=study("snowboard",{snowboard:variant("burton-goodcompany"),
  snow_binding:variant("burton-stepon"),snow_boot:variant("burton-stepon-boot-ref")},{
  left_mondo_mm:225,right_mondo_mm:230
 });
 assert.ok(x.report.findings.some(f=>/outside the published/.test(f.message)));
 assert.ok(x.report.findings.some(f=>/Different left\/right/.test(f.message)));
 assert.equal(x.report.conflicts.length,0); // measured foot is not a confirmed boot size
 assert.equal(x.graph.safety.usable_for_mounting,false);
});
test("complete Loaded longboard cannot double-count standalone kit rows",()=>{
 assert.throws(()=>study("skateboard_longboard",{
  long_complete:variant("loaded-tangent-complete"),
  long_wheels:variant("loaded-dadbod-ref")}),/double-count/);
 const x=study("skateboard_longboard",{long_complete:variant("loaded-tangent-complete")});
 assert.ok(x.report.rows.filter(r=>r.status==="MAKER_CLAIMED_INCLUDED_IN_COMPLETE_REVIEW").length>=3);
 assert.equal(x.report.qualified_supplier_order_lines,0);
 assert.equal(x.graph.completeness.physical_connections_qualified,0);
});
test("MBS each-vs-pair claims never become fabricated seller quantities",()=>{
 const x=study("mountainboard",{mt_deck:variant("mbs-comp95"),
  mt_trucks:variant("mbs-matrix3"),mt_wheels:variant("mbs-rockstar"),
  mt_bindings:variant("mbs-f5")});
 assert.ok(x.selected_variants.some(p=>p.inclusion_claim[0].includes("each")));
 assert.ok(x.report.rows.every(r=>r.exact_seller_order_units===null));
 assert.equal(x.graph.safety.physical_qualification,"NOT_QUALIFIED");
});
test("forged sources, revisions, unexpected slots, dangerous authorizations fail closed",()=>{
 let x=structuredClone(catalog);
 x.policy.exact_cart_authorized=true;
 assert.throws(()=>validatePartsRegistry(x),/physical or checkout/);
 x=structuredClone(catalog);
 x.sources[0].url="javascript:alert(1)";
 assert.throws(()=>validatePartsRegistry(x),/untrusted or stale source/);
 x=structuredClone(catalog);
 x.products[0].checkout_eligible=true;
 assert.throws(()=>validatePartsRegistry(x),/qualified-looking/);
 x=structuredClone(catalog);
 x.products[0].variants[0].manufacturer_sku="FAKE-SKU";
 assert.throws(()=>validatePartsRegistry(x),/unsourced exact SKU/);
 assert.throws(()=>study("snowboard",{ski_pair:variant("atomic-bent90")}),/unrecognized selected slot/);
 assert.throws(()=>study("snowboard",{snowboard:variant("atomic-bent90")}),/does not match/);
 assert.throws(()=>study("touring_ski"),/no research template/);
});
test("printing taxonomy explicitly holds structurally critical equipment",()=>{
 const unsafe=catalog.print_guidance.find(x=>x.id==="critical-hardware");
 assert.equal(unsafe.classification,"DO_NOT_SUBSTITUTE_WITH_GENERIC_FDM_PRINT");
 assert.match(unsafe.notes,/release|retention/);
});

test("dated indicative maker prices cannot turn into a BOM/order total",()=>{
 assert.ok(catalog.observed_listing_prices.length>=8);
 assert.ok(catalog.observed_listing_prices.every(p=>p.stock_verified===false &&
  p.eligible_for_bom_total===false && p.seller_order_units===null));
 const x=study("alpine_ski",{ski_pair:variant("atomic-bent90")});
 const offer=x.selected_variants[0].indicative_family_price;
 assert.equal(offer.displayed_maker_listing_usd,725);
 assert.equal(offer.observed_on,catalog.as_of);
 assert.equal(x.report.known_order_total_usd,null);
 assert.equal(x.report.qualified_supplier_order_lines,0);
 let bad=structuredClone(catalog);
 bad.observed_listing_prices[0].eligible_for_bom_total=true;
 assert.throws(()=>validatePartsRegistry(bad),/price cannot/);
 bad=structuredClone(catalog);
 bad.observed_listing_prices[0].source_id="other-source";
 assert.throws(()=>validatePartsRegistry(bad),/orphan or mismatched/);
});

test("cross-family variant ID collisions fail before any source/order or 3D study",()=>{
 const bad=structuredClone(catalog);
 bad.products[1].variants[0].id=bad.products[0].variants[0].id;
 assert.throws(()=>validatePartsRegistry(bad),/duplicate IDs/);
 assert.throws(()=>buildPickerStudy(bad,{domain_id:"alpine_ski"}),
  /duplicate IDs/);
});
