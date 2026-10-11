import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {buildOutdoorCatalogGraph,replayLegacyBoardCatalog} from "../../builder/outdoor_catalog_graph.mjs";
import {generateBoardDesignSpace} from "../../builder/platform_engine.mjs";
import {buildBuildPassport} from "../../builder/build_passport.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const catalog=read("catalog/board_components.v1.json");
const domains=read("catalog/outdoor_equipment_domains.v0.json");
const inclusions=read("catalog/board_package_inclusions.v1.json");
const make=(c=catalog,d=domains,p=inclusions)=>buildOutdoorCatalogGraph(c,d,p);
const find=(xs,id)=>xs.find(x=>x.component_id===id || x.legacy_component_id===id);

test("all legacy records replay losslessly with separate provisional families/variants",()=>{
 const graph=make();
 assert.deepEqual(replayLegacyBoardCatalog(graph),catalog);
 assert.equal(graph.variants.length,catalog.components.length);
 assert.equal(graph.families.length,catalog.components.length);
 assert.equal(graph.source_snapshots.length,catalog.components.length);
 assert.equal(graph.summary.confirmed_exact_variants,0);
 assert.equal(graph.summary.live_offers,0);
 assert.equal(graph.summary.orderable_kits,0);
 assert.equal(graph.summary.independently_qualified_interfaces,0);
 assert.ok(Object.values(graph.authority).every(x=>x===false));
 assert.ok(graph.families.every(x=>x.provisional && x.variant_equivalence_verified===false));
 assert.ok(graph.variants.every(x=>x.actual_assembly_quantity===null &&
   x.real_seller_order_quantity===null && !x.actual_physical_compatibility_verified));
});
test("family text and component model aren't silently promoted to sellable exact SKU",()=>{
 const graph=make();
 const truck=find(graph.variants,"TRUCK-M3-400");
 const hubs=find(graph.variants,"HUB-RSII");
 const brake=find(graph.variants,"BRAKE-V5");
 assert.equal(truck.sku_resolution,"FAMILY_OR_ALTERNATE_SKUS_UNRESOLVED");
 assert.equal(hubs.sku_resolution,"FAMILY_OR_ALTERNATE_SKUS_UNRESOLVED");
 assert.equal(brake.sku_resolution,"CATALOG_SKU_TEXT_NOT_RECEIVED_VARIANT");
 assert.equal(brake.exact_received_variant_verified,false);
 assert.notEqual(truck.family_id,hubs.family_id);
});
test("dated vendor link is reference not real stock, and no fabricated supplier order counts",()=>{
 const graph=make(),donor=graph.supplier_offer_references.find(x=>x.variant_id==="variant:mountainboard:DONOR-COMP95");
 assert.equal(donor.catalog_price_qty_factor,1);
 assert.equal(donor.seller_pack_unit_count,null);
 assert.equal(donor.assembly_units_per_pack,null);
 assert.equal(donor.checkout_authorized,false);
 assert.equal(donor.verified_quote,false);
 assert.equal(donor.current_availability,"UNKNOWN_NOT_LIVE");
 const hub=graph.supplier_offer_references.find(x=>x.variant_id==="variant:mountainboard:HUB-RSII");
 assert.equal(hub.catalog_price_qty_factor,4);
 assert.equal(hub.seller_pack_unit_count,null);
 assert.equal(hub.assembly_units_per_pack,null);
 const assumed=graph.variants.find(x=>x.legacy_component_id==="BATTERY-TRAIL-CLASS");
 assert.ok(assumed);
 assert.ok(!graph.supplier_offer_references.some(x=>x.variant_id===assumed.id));
 assert.ok(graph.source_holds.some(x=>x.component_id==="BATTERY-TRAIL-CLASS"));
});
test("donor contents remain source-bound research hypotheses and never auto-deduct price",()=>{
 const graph=make(),pkg=graph.sellable_package_hypotheses[0];
 assert.equal(pkg.component_id,"DONOR-COMP95");
 assert.equal(pkg.registry_mapping_status,"BOUND_REFERENCE_NOT_CONTENTS_PROOF");
 assert.equal(pkg.contents_verified,false);
 assert.equal(pkg.items.length,5);
 assert.ok(pkg.items.every(x=>x.included_quantity===null &&
   x.exact_variant_equivalence_verified===false));
 assert.ok(pkg.items.some(x=>x.inclusion_token==="rockstar_ii_hubs" &&
   x.possible_reference_variant_ids.includes("variant:mountainboard:HUB-RSII")));
 assert.equal(graph.summary.orderable_kits,0);
});
test("raw interface claims stay separate from physical fit and provenance",()=>{
 const graph=make();
 const wheel=graph.engineering_claims.find(x=>
   x.id==="claim:mountainboard:WHEEL-TRAMPA-ALPHA8:published_diameter_mm");
 assert.ok(wheel);
 assert.equal(wheel.raw_value_units,"mm");
 assert.ok(typeof wheel.raw_catalog_value==="number");
 assert.equal(wheel.exact_revision_applicability_verified,false);
 assert.equal(wheel.independently_measured,false);
 assert.equal(wheel.typed_interface_qualified,false);
 assert.equal(wheel.source_snapshot_id,"source:mountainboard:WHEEL-TRAMPA-ALPHA8");
});
test("unknown categories, duplicates, orphan packages and mapping ambiguity fail closed",()=>{
 const bad=structuredClone(catalog);
 bad.components.push({...bad.components[0],id:"NEW-WEIRD",category:"binding_release"});
 assert.throws(()=>make(bad),/unmapped category/);
 bad.components.pop();bad.components.push(structuredClone(bad.components[0]));
 assert.throws(()=>make(bad),/duplicate or invalid legacy component/);
 const unbound=structuredClone(inclusions);
 unbound.packages[0].component_id="MISSING-DONOR";
 assert.throws(()=>make(catalog,domains,unbound),/orphan source-bound/);
 const ambiguous=structuredClone(domains);
 ambiguous.legacy_migration.mappings.push({...ambiguous.legacy_migration.mappings[0]});
 assert.throws(()=>make(catalog,ambiguous),/duplicate legacy category mapping/);
});
test("graph replay refuses stale source and SKU changes or missing identity records",()=>{
 const graph=make();
 const changed=structuredClone(graph);
 changed.legacy_catalog_snapshot.components[0].source.snapshot_id="vendor-swap";
 assert.throws(()=>replayLegacyBoardCatalog(changed),/stale graph snapshot/);
 const changedSku=structuredClone(graph);
 changedSku.legacy_catalog_snapshot.components[0].sku="bogus";
 assert.throws(()=>replayLegacyBoardCatalog(changedSku),/stale graph snapshot/);
 const missing=structuredClone(graph);missing.variants.pop();
 assert.throws(()=>replayLegacyBoardCatalog(missing),/partial graph/);
});
test("board design engine and Build Passport are bitwise unchanged by replay",()=>{
 const graph=make();
 const bundle={questionnaire:read("configurator/questionnaire.v1.json"),
  rules:read("configurator/rules.v1.json"),
  architectures:read("configurator/architectures.v1.json"),
  catalog,catalogHealth:read("catalog/catalog_health.v1.json"),
  compatibility:read("configurator/compatibility_rules.v1.json"),
  geometry:read("catalog/board_geometry.v1.json"),
  swapSlots:read("configurator/swap_slots.v1.json"),
  composer:read("configurator/composer.v1.json"),
  packageInclusions:inclusions};
 const p=read("configurator/examples/trail_rider_profile.json");
 const orig=generateBoardDesignSpace(p,bundle);
 const replayBundle={...bundle,catalog:replayLegacyBoardCatalog(graph)};
 const replay=generateBoardDesignSpace(p,replayBundle);
 assert.deepEqual(replay,orig);
 for(const candidate of orig.candidates.slice(0,4))
  assert.deepEqual(buildBuildPassport(candidate,bundle),buildBuildPassport(candidate,replayBundle));
});

test("seller snapshot must have real date, HTTPS without credentials, and price cannot be silently altered",()=>{
 const changed=structuredClone(catalog);
 changed.components[0].source.url="https://user:secret@www.mbs.com/product";
 assert.ok(!make(changed).supplier_offer_references.some(x=>x.variant_id==="variant:mountainboard:DONOR-COMP95"));
 changed.components[0].source.url="https://www.mbs.com/product";
 changed.components[0].source.as_of="2026-02-30";
 assert.ok(!make(changed).supplier_offer_references.some(x=>x.variant_id==="variant:mountainboard:DONOR-COMP95"));
 const report=make();
 report.legacy_catalog_snapshot.components[0].price.unit_price_usd=0.01;
 assert.throws(()=>replayLegacyBoardCatalog(report),/stale graph snapshot/);
});
