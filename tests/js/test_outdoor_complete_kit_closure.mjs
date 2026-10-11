import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {buildPickerStudy} from "../../builder/parts_picker_engine.mjs";
import {validateMakerKitClaims,auditCompleteKitClaim} from "../../builder/complete_kit_closure.mjs";

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const catalog=read("catalog/outdoor_parts_picker.v1.json");
const retail=read("catalog/outdoor_retail_comparisons.v1.json");
const kits=read("catalog/outdoor_complete_kit_claims.v1.json");
const named=id=>catalog.products.find(x=>x.id===id).variants[0].id;
const study=variant=>buildPickerStudy(catalog,{domain_id:"skateboard_longboard",
 selections:{long_complete:variant}});
const as=(variant,reg=kits,stores=retail)=>
 auditCompleteKitClaim(study(variant),reg,catalog,stores,{as_of:"2026-10-11"});

test("two maker-claimed complete board setups have seven distinct child identity slots each",()=>{
 const result=validateMakerKitClaims(kits,catalog);
 assert.equal(result.kit_count,2);
 assert.equal(result.advertised_child_count,14);
 assert.equal(result.complete_delivered_kits_confirmed,0);
 const ids=kits.kits.flatMap(x=>x.children.map(y=>y.id));
 assert.equal(new Set(ids).size,14);
});

test("maker-declared Dad Bod 105 includes child hypotheses, never seven additional purchases",()=>{
 const r=as(named("loaded-tangent-complete"));
 assert.equal(r.status,"SELLER_PACKAGE_REVISION_CONFLICT_HOLD");
 assert.equal(r.rows.length,7);
 assert.deepEqual(r.rows.map(x=>x.role),[
  "deck","zee_brackets","trucks","wheels","bearings","deck_hardware","truck_hardware"]);
 assert.equal(r.inclusion_conflict.code,"INCLUDED_TRUCK_REVISION_MISMATCH");
 assert.equal(r.independent_additional_item_orders,0);
 assert.equal(r.actual_seller_unit_count,null);
 assert.equal(r.verified_kit_count,0);
 assert.equal(r.actual_received_complete,false);
 assert.equal(r.physical_connections_qualified,0);
 assert.equal(r.current_cart_total,null);
 assert.ok(r.rows.every(x=>x.maker_claimed_included&&
  x.add_independent_purchase_line===false&&
  x.exact_seller_pack_units===null&&x.actual_received_units===null&&
  x.qualified_mount===false));
 assert.ok(Object.values(r.authority).every(x=>x===false));
 const trucks=r.rows.find(x=>x.role==="trucks");
 assert.match(trucks.source_claim,/Paris V3/);
 assert.ok(r.seller_page_revisions.some(x=>x.revision?.includes("V2")));
 assert.ok(r.seller_page_revisions.some(x=>x.revision?.includes("V3")));
});

test("switch to 85mm Caguama invalidates old wheel child source and previous kit ID",()=>{
 const a=as(named("loaded-tangent-complete"));
 const b=as(named("loaded-tangent-caguama"));
 assert.notEqual(a.kit_id,b.kit_id);
 assert.notEqual(a.variant_id,b.variant_id);
 assert.notEqual(a.rows.find(x=>x.role==="wheels").source_claim,
  b.rows.find(x=>x.role==="wheels").source_claim);
 assert.deepEqual(a.rows.map(x=>x.role),b.rows.map(x=>x.role));
 assert.equal(b.rows.length,7);
 assert.ok(b.rows.every(x=>!a.rows.some(y=>y.child_id===x.child_id)));
});

test("no complete kit means no falsely inferred included contents",()=>{
 const r=auditCompleteKitClaim(
  buildPickerStudy(catalog,{domain_id:"skateboard_longboard",selections:{}}),
  kits,catalog,retail);
 assert.equal(r.status,"NO_COMPLETE_KIT_SELECTED");
 assert.deepEqual(r.rows,[]);
 assert.equal(r.order_units,null);
});

test("insufficient seller receipt or forged maker kit data cannot promote authority",()=>{
 const mutate=fn=>{const x=structuredClone(kits);fn(x);return x;};
 const bad=[
  x=>x.authority.procurement_authorized=true,
  x=>x.kits[0].seller_checkout_option_verified=true,
  x=>x.kits[0].actual_received_kit_verified=true,
  x=>x.kits[0].children[0].actual_received_units=1,
  x=>x.kits[0].children[0].direct_seller_purchase_required=true,
  x=>x.kits[0].children[0].expected_assembly_units=-1,
  x=>x.kits[0].children[1].id=x.kits[0].children[0].id,
  x=>x.kits[0].children[3].source_claim_label="85 mm Caguama",
  x=>x.kits[0].children[2].source_claim_label="Paris V2 150mm",
  x=>x.kits[0].source_url="https://www.skatesusa.com/anything",
  x=>x.kits[0].variant_id=x.kits[1].variant_id,
  x=>x.kits[0].children.pop()
 ];
 bad.forEach((fn,i)=>assert.throws(()=>validateMakerKitClaims(mutate(fn),catalog),
  /Kit closure:/,"kit adversarial case "+i));
});

test("a complete longboard plus separate replacement trucks cannot sneak through kit closure",()=>{
 const s=study(named("loaded-tangent-complete"));
 s.selected_variants.push({slot:"long_trucks",variant_id:named("loaded-tangent-trucks-ref")});
 assert.throws(()=>auditCompleteKitClaim(s,kits,catalog,retail),
  /Kit closure:/);
});
