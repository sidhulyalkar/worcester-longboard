import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {buildPickerStudy} from "../../builder/parts_picker_engine.mjs";
import {validateSupplierObservations,auditMakerOrderUnits} from "../../builder/offer_qualification.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const catalog=read("catalog/outdoor_parts_picker.v1.json");
const observations=read("catalog/outdoor_supplier_observations.v1.json");
const select=(sport,selections)=>buildPickerStudy(catalog,{domain_id:sport,selections});
const id=(product,label)=>catalog.products.find(p=>p.id===product).variants.find(v=>v.label===label).id;
const report=study=>auditMakerOrderUnits(study,observations,catalog);
test("exact maker listing observations remain distinct from qualified assembly/source receipts",()=>{
 const coverage=validateSupplierObservations(observations,catalog);
 assert.equal(coverage.observations,7);
 assert.equal(coverage.targets,6);
 assert.ok(Object.values(coverage.authority).every(x=>x===false));
 assert.ok(observations.listing_observations.every(x=>
   !x.receipt_contents_inspected&&!x.financial_checkout_authorized&&
   !x.source_identity_exact_variant_verified&&x.availability_state==="NOT_REVALIDATED"));
});
test("MBS 12300 each produces historical 2-pack reference, never a live total",()=>{
 const study=select("mountainboard",{mt_trucks:id("mbs-matrix3","Matrix III 12×400 mm black · maker part 12300")});
 const audit=report(study);
 const truck=audit.rows.find(x=>x.slot==="mt_trucks");
 assert.equal(truck.status,"HISTORICAL_MAKER_UNIT_REFERENCE_ONLY");
 assert.equal(truck.maker_product_code,"12300");
 assert.equal(truck.required_item_count,2);
 assert.equal(truck.seller_unit_items,1);
 assert.equal(truck.reference_pack_count,2);
 assert.equal(truck.reference_extended_amount,239.9);
 assert.equal(audit.historical_partial_subtotals_by_currency.USD,239.9);
 assert.equal(audit.actual_checkout_total,null);
 assert.equal(audit.qualified_supplier_order_lines,0);
 assert.ok(Object.values(audit.authority).every(x=>x===false));
});
test("MBS F5 seller 'pair' counts as one historical seller package, not two",()=>{
 const study=select("mountainboard",{mt_bindings:id("mbs-f5","F5 binding pair · maker part 14051")});
 const audit=report(study);
 const row=audit.rows.find(x=>x.slot==="mt_bindings");
 assert.equal(row.required_item_count,2);
 assert.equal(row.item_kind,"individual_binding");
 assert.equal(row.seller_unit_items,2);
 assert.equal(row.reference_pack_count,1);
 assert.equal(row.reference_extended_amount,119.95);
 assert.equal(audit.live_stock_verified,false);
});
test("three maker-coded MBS parts can form a PARTIAL historical line subtotal",()=>{
 const study=select("mountainboard",{
  mt_deck:id("mbs-comp95","Silver Hex 95 cm · maker part 11303"),
  mt_trucks:id("mbs-matrix3","Matrix III 12×400 mm black · maker part 12300"),
  mt_bindings:id("mbs-f5","F5 binding pair · maker part 14051")
 });
 const r=report(study);
 assert.equal(r.matched_historical_unit_lines,3);
 assert.equal(r.historical_partial_subtotals_by_currency.USD,479.8);
 assert.equal(r.actual_checkout_total,null);
 assert.equal(r.all_required_items_resolved,false);
 assert.ok(r.rows.some(x=>x.slot==="mt_wheels"&&x.status==="REQUIRED_COMPONENT_NOT_SELECTED"));
});
test("MBS CNC420 conflicts with the maker brake and freezes ALL unit planning",()=>{
 const study=select("mountainboard",{
  mt_trucks:id("mbs-cnc420","CNC black 420 mm · maker part 12307"),
  mt_deck:id("mbs-comp95","Silver Hex 95 cm · maker part 11303"),
  mt_brake:catalog.products.find(x=>x.id==="mbs-brake").variants[0].id
 });
 assert.ok(study.report.conflicts.some(x=>x.code==="MBS_CNC_420_BRAKE_CONFLICT"));
 const r=report(study);
 assert.equal(r.has_declared_compatibility_conflict,true);
 assert.equal(r.matched_historical_unit_lines,0);
 assert.equal(r.historical_partial_subtotals_by_currency.USD,undefined);
 assert.ok(r.rows.filter(x=>x.selected_variant_id&&x.source_url).every(x=>
   x.reference_pack_count===null));
 assert.equal(r.rows.find(x=>x.slot==="mt_trucks").status,"KNOWN_ASSEMBLY_INTERFACE_CONFLICT");
});
test("historical identity is exact option only: family code and complete without SKU stay HOLD",()=>{
 let r=report(select("alpine_ski",{ski_pair:id("atomic-bent90","157 cm")}));
 assert.equal(r.rows.find(x=>x.slot==="ski_pair").status,"EXACT_SELECTED_OPTION_CODE_NOT_ESTABLISHED");
 assert.equal(r.rows.find(x=>x.slot==="ski_pair").reference_pack_count,null);
 r=report(select("snowboard",{snowboard:id("burton-goodcompany","145 cm")}));
 assert.equal(r.rows.find(x=>x.slot==="snowboard").status,"EXACT_SELECTED_OPTION_CODE_NOT_ESTABLISHED");
 r=report(select("skateboard_longboard",{
  long_complete:catalog.products.find(x=>x.id==="loaded-tangent-complete").variants[0].id
 }));
 assert.equal(r.rows.find(x=>x.slot==="long_complete").status,"EXACT_SELECTED_OPTION_CODE_NOT_ESTABLISHED");
 assert.ok(r.rows.some(x=>x.status==="MAKER_KIT_CONTENTS_RECEIPT_HOLD"));
});
test("historical offer automatically expires; user cannot advance beyond last observed snapshot",()=>{
 const study=select("mountainboard",{mt_trucks:"mbs-matrix3-12300-black-400"});
 for(const as_of of ["2026-11-10","2026-10-09"]){
  const r=auditMakerOrderUnits(study,observations,catalog,{as_of});
  const row=r.rows.find(x=>x.slot==="mt_trucks");
  assert.equal(row.status,"EXPIRED_OR_FUTURE_LISTING");
  assert.equal(row.reference_pack_count,null);
 }
 const good=auditMakerOrderUnits(study,observations,catalog,{as_of:"2026-11-09"});
 assert.equal(good.rows.find(x=>x.slot==="mt_trucks").reference_pack_count,2);
});
test("tampered seller hosts, variant IDs, quantities, dates, fake approvals fail closed",()=>{
 const mutate=fn=>{const d=structuredClone(observations);fn(d);return d;};
 const cases=[
  d=>d.listing_observations[0].source_url="http://example.com/cheap",
  d=>d.listing_observations[0].source_url="https://www.atomic.com/en-us/products/bent",
  d=>d.listing_observations[0].product_id="mbs-f5",
  d=>d.listing_observations[0].selected_variant_id="mbs-matrix3-12300-black-400",
  d=>d.listing_observations[0].seller_unit.individual_items=0,
  d=>d.listing_observations[0].seller_unit.individual_items=2.4,
  d=>d.listing_observations[0].maker_product_code=null,
  d=>d.listing_observations[0].source_identity_exact_variant_verified=true,
  d=>d.listing_observations[0].financial_checkout_authorized=true,
  d=>d.listing_observations[0].receipt_contents_inspected=true,
  d=>d.listing_observations[0].observed_on="2026-10-11",
  d=>d.listing_observations[0].displayed_price.price_scope="MAKER_FAMILY_PRICE_NOT_VARIANT_QUOTE",
  d=>d.listing_observations[0].displayed_price.amount=-8,
  d=>d.unit_requirements.push({...d.unit_requirements[0]}),
  d=>d.authority.procurement_authorized=true,
  d=>d.expiry_policy.max_age_days=365
 ];
 for(const fn of cases)assert.throws(()=>validateSupplierObservations(mutate(fn),catalog),/Offer audit:/);
 const study=select("mountainboard",{mt_trucks:"mbs-matrix3-12300-black-400"});
 const forged=structuredClone(study);
 forged.report.checkout_eligible=true;
 assert.throws(()=>report(forged),/authority locked/);
 forged.report.checkout_eligible=false;
 forged.selection.mt_trucks="mbs-cnc420-12307";
 assert.throws(()=>report(forged),/audited selection/);
});
test("source row validation detects duplicate IDs and impossible days",()=>{
 const d=structuredClone(observations);
 d.listing_observations.push({...d.listing_observations[0]});
 assert.throws(()=>validateSupplierObservations(d,catalog),/duplicate/);
 d.listing_observations.pop();
 d.reviewed_as_of="2026-02-30";
 assert.throws(()=>validateSupplierObservations(d,catalog),/impossible calendar date/);
});
