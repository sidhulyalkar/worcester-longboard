// Browser release gate: real Chromium, real local HTTP server and four source catalogs.
// Historical supplier data must not turn into a checkout-ready or qualified product.
// Run: npm install --no-save --no-package-lock playwright@1.56.1
//      npx playwright install chromium
//      node tests/browser/parts_picker_smoke.mjs
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import {spawn} from "node:child_process";
import {mkdtemp,mkdir,readFile,writeFile} from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import {fileURLToPath} from "node:url";
import {chromium} from "playwright";

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const base="http://127.0.0.1:18765";
const artifacts=path.resolve(process.env.PARTS_BROWSER_ARTIFACTS||
  path.join(root,"/tmp/parts-picker-browser-artifacts"));
const faults=[],checks=[];
const assertBrowser=(condition,message)=>assert.ok(condition,message);
const note=(name,result="PASS")=>{checks.push({name,result});process.stdout.write("✓ "+name+"\n");};
const srv=spawn(process.env.PYTHON||"python3",["-m","http.server","18765","--bind","127.0.0.1"],{
 cwd:root,stdio:["ignore","ignore","pipe"]
});
let serverErrors="";
srv.stderr.on("data",x=>serverErrors+=String(x));
async function ready(){
 for(let i=0;i<80;i++){
  if(srv.exitCode!==null)throw Error("Local HTTP server stopped: "+serverErrors);
  try{
   const response=await fetch(base+"/builder/parts.html");
   if(response.ok)return;
  }catch{}
  await new Promise(resolve=>setTimeout(resolve,125));
 }
 throw Error("Local HTTP server did not become ready: "+serverErrors);
}
async function initialized(page){
 await page.goto(base+"/builder/parts.html",{waitUntil:"domcontentloaded"});
 await page.locator("#picker-study-cards .study-card").first().waitFor({timeout:20000});
 assert.equal(await page.locator("#picker-study-cards .study-card").count(),3);
 assertBrowser((await page.locator("#picker-coverage").innerText()).includes("product families"),
  "Catalog did not initialize correctly");
 const errors=await page.locator("#picker-order-status").innerText();
 assertBrowser(!errors.includes("Selection held"),"Picker initialization error: "+errors);
}
async function screenshot(page,name){
 await page.screenshot({path:path.join(artifacts,name+".png"),fullPage:true,
  animations:"disabled",timeout:20000});
}
async function browserErrors(page,context){
 const errors=[];
 page.on("pageerror",e=>errors.push(String(e)));
 return ()=>assert.deepEqual(errors,[],context+" page exceptions");
}
async function checkNoOverflow(page,label){
 const result=await page.evaluate(()=>({
  vw:document.documentElement.clientWidth,
  sw:document.documentElement.scrollWidth,
  inner:window.innerWidth
 }));
 assertBrowser(result.sw<=result.vw+3,label+" horizontal overflow: "+JSON.stringify(result));
}
async function clickStudy(page,id){
 const selector='[data-load-study="'+id+'"]';
 await page.locator(selector).click();
 await page.locator(selector+'[aria-pressed="true"]').waitFor({timeout:10000});
 assertBrowser((await page.locator("#picker-study-status").innerText()).length>2,
  "Study update status missing");
}

function syntheticLocalGlb(metric=false){
 // Explicitly test-only mesh, not Loaded/Paris geometry or an approved component.
 const vertices=new Float32Array(metric?[0,0,0,.04,.02,.012,0,.02,0]:
  [0,0,0,1,0,0,0,1,0]);
 const payload={asset:{version:"2.0"},buffers:[{byteLength:36}],
  bufferViews:[{buffer:0,byteOffset:0,byteLength:36}],
  accessors:[{bufferView:0,componentType:5126,count:3,type:"VEC3",
   min:[0,0,0],max:metric?[.04,.02,.012]:[1,1,0]}],
  meshes:[{primitives:[{attributes:{POSITION:0}}]}],
  nodes:[{mesh:0}],scenes:[{nodes:[0]}],scene:0};
 const bytes=Buffer.from(JSON.stringify(payload));
 const padded=Math.ceil(bytes.length/4)*4;
 const result=Buffer.alloc(12+8+padded+8+36);
 result.write("glTF");result.writeUInt32LE(2,4);
 result.writeUInt32LE(result.length,8);
 result.writeUInt32LE(padded,12);result.write("JSON",16);
 bytes.copy(result,20);result.fill(32,20+bytes.length,20+padded);
 result.writeUInt32LE(36,20+padded);
 result.write("BIN\u0000",24+padded);
 Buffer.from(vertices.buffer).copy(result,28+padded);
 return result;
}
async function main(){
 await mkdir(artifacts,{recursive:true});
 await ready();
 let browser=null;
 try{
  browser=await chromium.launch({headless:true,
   args:["--use-gl=swiftshader","--enable-webgl"]});
  const desktop=await browser.newContext({
   viewport:{width:1440,height:900},deviceScaleFactor:1,acceptDownloads:true});
  const page=await desktop.newPage();
  const noErrors=await browserErrors(page,"desktop initial");
  await initialized(page);
  for(const [domain,first] of [
   ["alpine_ski","ski-playful-short"],
   ["snowboard","snow-compact-step"],
   ["skateboard_longboard","long-rollover"],
   ["mountainboard","mt-stable-standard"]
  ]){
   await page.locator("#picker-domain").selectOption(domain);
   assert.equal(await page.locator(".study-card").count(),3,domain+" three study options");
   await clickStudy(page,first);
   assert.equal(await page.locator("#picker-order-table tbody tr").count()>0,true,
    domain+" worklist is empty");
   assertBrowser((await page.locator("#picker-quantity-status").innerText()).includes("0 verified"),
    domain+" incorrectly gained procurement authority");
   assertBrowser((await page.locator("#picker-view-note").innerText()).toLowerCase().includes("not measured")||
    (await page.locator("#picker-view-note").innerText()).toLowerCase().includes("proportion"),
    "3D should not imply measured physical geometry");
   await checkNoOverflow(page,domain+" desktop");
   await screenshot(page,"desktop-"+domain);
  }
  note("Four sports render three cards, load source-bound assemblies and stay non-orderable");
  await page.locator("#picker-domain").selectOption("skateboard_longboard");
  await clickStudy(page,"long-rollover");
  await page.locator("#picker-cad-import-lab > summary").click();
  assertBrowser((await page.locator("#picker-cad-readiness").innerText())
   .includes("0/7 file-backed candidates"),"No CAD coverage hold");
  assert.equal(await page.locator("#picker-cad-coverage-rows tr").count(),7);
  assert.equal(await page.locator("#picker-cad-upload").isDisabled(),false);
  const cadEvidenceDownload=page.waitForEvent("download");
  await page.locator("#picker-cad-evidence-export").click();
  const readiness=JSON.parse(await readFile(await (await cadEvidenceDownload).path(),"utf8"));
  assert.equal(readiness.asset_candidates,0);
  assert.equal(readiness.verified_mount_datums,0);
  assert.equal(readiness.clearance_status,"NOT_EVALUATED");
  assert.equal(readiness.additional_purchase_lines,0);
  assert.equal(await page.locator("#picker-cad-maker-dimensions tr").count(),17);
  await page.locator("#picker-cad-import-lab .cad-maker-evidence > summary").click();
  const makerDownload=page.waitForEvent("download");
  await page.locator("#picker-cad-maker-export").click();
  const makerReport=JSON.parse(await readFile(await (await makerDownload).path(),"utf8"));
  assert.equal(makerReport.claims.length,17);
  assert.equal(makerReport.claims.find(c=>c.label==="nominal_wheel_diameter").value_mm,105);
  assert.equal(makerReport.claims.find(c=>c.label==="template_along_holes").value_mm,53.975);
  assert.ok(makerReport.claims.every(c=>!c.usable_as_mounting_datum));
  await page.locator("#picker-cad-import-lab .cad-source-acquisition > summary").click();
  assertBrowser((await page.locator("#picker-cad-source-status").innerText())
   .includes("7/7 part categories still need licensed CAD"),
   "Known official pages cannot be counted as real component CAD");
  assert.equal(await page.locator("#picker-cad-source-roles .cad-source-role").count(),7);
  assert.equal(await page.locator("#picker-cad-source-exclusions > div").count(),2);
  const leadDownload=page.waitForEvent("download");
  await page.locator("#picker-cad-source-export").click();
  const sourceLead=JSON.parse(await readFile(await (await leadDownload).path(),"utf8"));
  assert.equal(sourceLead.rows.length,7);
  assert.equal(sourceLead.manufacturer_request_packets.length,3);
  assert.match(sourceLead.rows.find(x=>x.role==="wheels").source_url,/dad-bod-105mm/);
  assert.ok(sourceLead.excluded_artifacts.every(x=>!x.qualifies_seven_component_models));
  assert.equal(sourceLead.additional_purchase_lines,0);
  const requestsDownload=page.waitForEvent("download");
  await page.locator("#picker-cad-source-requests").click();
  const requestsText=await readFile(await (await requestsDownload).path(),"utf8");
  assertBrowser(requestsText.includes("Loaded Boards team")&&
   requestsText.includes("Paris Truck Co team")&&
   requestsText.includes("Orangatang Wheels team")&&
   requestsText.includes("express written permissions"),
   "Part-qualified, rights-aware maker inquiries missing");
  await page.locator("#picker-cad-import-lab .cad-capture-campaign > summary").click();
  assert.equal(await page.locator("#picker-cad-capture-tasks .cad-capture-role").count(),7);
  assert.equal(await page.locator("#picker-cad-capture-interfaces li").count(),7);
  assertBrowser((await page.locator("#picker-cad-capture-status").innerText())
   .includes("20/20 evidence tasks open"),"Initial unmeasured survey tasks must be fully open");
  const fieldTemplateDownload=page.waitForEvent("download");
  await page.locator("#picker-cad-capture-template").click();
  const fieldTemplate=JSON.parse(await readFile(await (await fieldTemplateDownload).path(),"utf8"));
  assert.equal(fieldTemplate.scope,"UNREVIEWED_CAD_FIELD_OBSERVATIONS");
  assert.equal(fieldTemplate.kit_variant_id,readiness.selected_variant_id);
  assert.deepEqual(fieldTemplate.records,[]);
  const reportDownload=page.waitForEvent("download");
  await page.locator("#picker-cad-capture-export").click();
  const captureBefore=JSON.parse(await readFile(await (await reportDownload).path(),"utf8"));
  assert.equal(captureBefore.task_count,20);
  assert.equal(captureBefore.interfaces.length,7);
  assert.equal(captureBefore.seller_revision_conflict_unresolved,true);
  assert.equal(captureBefore.independently_verified,0);
  const claimedField={...fieldTemplate,records:[{
   task_id:"truck-seller-revision",method:"REVISION_RECONCILIATION",
   part_revision:"OPERATOR_REPORT_NOT_CONFIRMED",
   evidence_url:"https://example.com/unreviewed-field-note",
   recorded_on:"2026-10-12",uncertainty_mm:null,
   note:"An unreviewed sample receipt, not actual inspected hardware.",
   source_sha256:null
  }]};
  await page.locator("#picker-cad-capture-upload").setInputFiles({
   name:"field-report.json",mimeType:"application/json",
   buffer:Buffer.from(JSON.stringify(claimedField))});
  await page.waitForFunction(()=>document.querySelector("#picker-cad-capture-status")
   ?.textContent.includes("1 field-reported (NOT reviewed)"),null,{timeout:10000});
  const capturedDownload=page.waitForEvent("download");
  await page.locator("#picker-cad-capture-export").click();
  const captureAfter=JSON.parse(await readFile(await (await capturedDownload).path(),"utf8"));
  assert.equal(captureAfter.missing_evidence,19);
  assert.equal(captureAfter.reported_unreviewed,1);
  assert.equal(captureAfter.independently_verified,0);
  assert.equal(captureAfter.physical_mates_verified,0);
  assert.equal(captureAfter.additional_purchase_lines,0);
  const forgedField=structuredClone(claimedField);
  forgedField.authority.fabrication_authorized=true;
  await page.locator("#picker-cad-capture-upload").setInputFiles({
   name:"forged-approval.json",mimeType:"application/json",
   buffer:Buffer.from(JSON.stringify(forgedField))});
  await page.waitForFunction(()=>document.querySelector("#picker-cad-capture-status")
   ?.textContent.includes("Observation packet held:"),null,{timeout:10000});
  const clearedDownload=page.waitForEvent("download");
  await page.locator("#picker-cad-capture-export").click();
  assert.equal(JSON.parse(await readFile(await (await clearedDownload).path(),"utf8"))
   .reported_unreviewed,0);
  note("CAD field campaign keeps 20 measurements unapproved, rejects forged reports and exports exact-kit source checklist");
  await page.locator("#picker-cad-import-lab .cad-metric-lab > summary").click();
  const fakePart=(id,offset)=>({
   id,source_url:"https://example.com/synthetic-not-cad",revision:"synthetic-only",
   geometry_evidence:"UNVERIFIED_CANDIDATE_BOUNDS",
   mating_datums_physically_verified:false,exact_revision_received:false,
   survey_tolerance_mm:0.25,
   local_bounds_mm:{min_mm:[-1,-1,-1],max_mm:[1,1,1]},
   correspondences:[[0,0,0],[5,0,0],[0,5,0],[0,0,5]]
    .map(p=>({local_mm:p,assembly_mm:p.map((x,i)=>x+(i===0?offset:0))}))
  });
  await page.locator("#picker-cad-motion-demo").click();
  await page.waitForFunction(()=>document.querySelector("#picker-cad-motion-status")
   ?.textContent.includes("SYNTHETIC ALGORITHM EXAMPLE ONLY"),null,{timeout:10000});
  assert.equal(await page.locator("#picker-cad-motion-plot svg").count(),1);
  assertBrowser((await page.locator("#picker-cad-metric-status").innerText())
   .includes("SYNTHETIC, NOT MANUFACTURER GEOMETRY"),
   "Synthetic demonstration was falsely promoted to measured geometry");
  await page.waitForFunction(()=>{
   const canvas=document.querySelector("#picker-cad-scene-view canvas");
   return canvas?.dataset.candidatePartCount==="2"&&canvas?.dataset.sampleIndex==="0";
  },null,{timeout:30000});
  const candidateCanvas=page.locator("#picker-cad-scene-view canvas");
  assert.equal(await candidateCanvas.getAttribute("data-scope"),
   "CANDIDATE_METRIC_BOXES_UNVERIFIED");
  assert.equal(await candidateCanvas.getAttribute("data-physical-clearances-verified"),"0");
  assert.equal(await candidateCanvas.getAttribute("data-manufacturer-cad-loaded"),"false");
  assert.equal(await page.locator("#picker-cad-scene-angle").getAttribute("max"),"6");
  const initialMarker=await page.locator('#picker-cad-motion-plot circle[stroke="#ffffff"]')
   .first().getAttribute("cx");
  await page.locator("#picker-cad-scene-angle").focus();
  await page.locator("#picker-cad-scene-angle").press("End");
  await page.waitForFunction(()=>document.querySelector("#picker-cad-scene-view canvas")
   ?.dataset.sampleIndex==="6",null,{timeout:10000});
  assert.equal(await page.locator("#picker-cad-scene-angle-output").innerText(),"45°");
  const finalMarker=await page.locator('#picker-cad-motion-plot circle[stroke="#ffffff"]')
   .first().getAttribute("cx");
  assert.notEqual(initialMarker,finalMarker,"2D motion plot did not track the 3D sample");
  await page.locator("#picker-cad-scene-angle").press("Home");
  await page.waitForFunction(()=>document.querySelector("#picker-cad-scene-view canvas")
   ?.dataset.sampleIndex==="0",null,{timeout:10000});
  assert.equal(await page.locator("#picker-visual-svg [data-exploded-part]").count(),7,
   "Candidate 3D displaced the source-bound board");
  await screenshot(page,"cad-synthetic-candidate-envelopes-3d");
  const demoExport=page.waitForEvent("download");
  await page.locator("#picker-cad-motion-export").click();
  const demo=JSON.parse(await readFile(await (await demoExport).path(),"utf8"));
  assert.equal(demo.physical_clearances_verified,0);
  assert.equal(demo.motion_kinematics_verified,false);
  assert.equal(demo.between_samples_checked,false);
  note("One-click synthetic motion demo keeps kit purchase and engineering authority locked");
  const metricFixture={
   schema_version:1,scope:"METRIC_CAD_SURVEY_FIXTURE_RESEARCH_ONLY",
   kit_variant_id:readiness.selected_variant_id,units:"mm",
   authority:{procurement_authorized:false,fabrication_authorized:false,
    physical_fit_qualified:false},
   parts:[fakePart("synthetic_deck",0),fakePart("synthetic_truck",12)]
  };
  await page.locator("#picker-cad-metric-upload").setInputFiles({
   name:"wrong-kit.json",mimeType:"application/json",
   buffer:Buffer.from(JSON.stringify({...metricFixture,kit_variant_id:"forged-other-kit"}))});
  await page.waitForFunction(()=>document.querySelector("#picker-cad-metric-status")
   ?.textContent.includes("Metric survey held:"),null,{timeout:10000});
  await page.locator("#picker-cad-metric-upload").setInputFiles({
   name:"synthetic-survey.json",mimeType:"application/json",
   buffer:Buffer.from(JSON.stringify(metricFixture))});
  await page.waitForFunction(()=>document.querySelector("#picker-cad-metric-status")
   ?.textContent.includes("candidate pair(s)"),null,{timeout:10000});
  assertBrowser((await page.locator("#picker-cad-metric-status").innerText())
   .includes("0 physical clearances verified"),"Candidate survey granted a physical clearance");
  assert.equal(await page.locator("#picker-cad-metric-results tr").count(),2);
  const surveyDownload=page.waitForEvent("download");
  await page.locator("#picker-cad-metric-export").click();
  const survey=JSON.parse(await readFile(await (await surveyDownload).path(),"utf8"));
  assert.equal(survey.physical_clearances_verified,0);
  assert.equal(survey.procurement_authorized,false);
  assert.equal(survey.pairs[0].classification,"CANDIDATE_AABBS_SEPARATED");
  assert.equal(await page.locator("#picker-cad-scene-angle").isDisabled(),true,
   "Static survey should not permit fabricated steering poses");
  assert.equal(await candidateCanvas.getAttribute("data-sample-index"),"0");
  assert.equal(await page.locator("#picker-cad-motion-export").isDisabled(),true);
  const motionFixture={...metricFixture,motion:{
   scope:"CANDIDATE_MOTION_RESEARCH_ONLY",
   moving_part_id:"synthetic_truck",
   stationary_part_ids:["synthetic_deck"],
   axis_point_assembly_mm:[12,0,0],
   axis_direction_assembly:[0,0,1],
   angle_range_deg:[-30,30],sample_step_deg:10,uncertainty_mm:.25,
   kinematics_physically_verified:false,dynamic_clearance_qualified:false,
   contact_verified:false
  }};
  await page.locator("#picker-cad-metric-upload").setInputFiles({
   name:"synthetic-candidate-motion.json",mimeType:"application/json",
   buffer:Buffer.from(JSON.stringify(motionFixture))});
  await page.waitForFunction(()=>document.querySelector("#picker-cad-motion-plot svg")&&
   document.querySelector("#picker-cad-motion-status")?.textContent.includes("Candidate motion"),
   null,{timeout:10000});
  assertBrowser((await page.locator("#picker-cad-motion-plot").innerText())
   .includes("NOT VERIFIED STEERING CLEARANCE"),"Unqualified motion plot missing");
  const motionDownload=page.waitForEvent("download");
  await page.locator("#picker-cad-motion-export").click();
  const motion=JSON.parse(await readFile(await (await motionDownload).path(),"utf8"));
  assert.equal(motion.sample_count,7);
  assert.equal(motion.pair_count,1);
  assert.equal(motion.physical_clearances_verified,0);
  assert.equal(motion.between_samples_checked,false);
  assert.equal(motion.procurement_authorized,false);
  const tamperedMotion=structuredClone(motionFixture);
  tamperedMotion.motion.dynamic_clearance_qualified=true;
  await page.locator("#picker-cad-metric-upload").setInputFiles({
   name:"forged-motion.json",mimeType:"application/json",
   buffer:Buffer.from(JSON.stringify(tamperedMotion))});
  await page.waitForFunction(()=>document.querySelector("#picker-cad-metric-status")
   ?.textContent.includes("Metric survey held:"),null,{timeout:10000});
  assert.equal(await page.locator("#picker-cad-scene-panel").isHidden(),true,
   "Tampered survey left stale 3D evidence visible");
  assert.equal(await page.locator("#picker-cad-motion-export").isDisabled(),true);
  note("Candidate steering sweep is bounded, exportable and never claims safe clearance");
  note("Manufacturer stencil, 105mm source identity and fail-closed metric candidate analyzer");
  await page.locator("#picker-cad-upload").setInputFiles({
   name:"tampered.glb",mimeType:"model/gltf-binary",
   buffer:Buffer.from("not a valid GLB")});
  assertBrowser((await page.locator("#picker-cad-inspect-status").innerText())
   .includes("Local CAD file held:"),"Corrupt geometry not rejected");
  assert.equal(await page.locator("#picker-cad-file-inspector").isHidden(),true);
  await page.locator("#picker-cad-upload").setInputFiles({
   name:"synthetic-geometry.glb",mimeType:"model/gltf-binary",
   buffer:syntheticLocalGlb()});
  await page.waitForFunction(()=>document.querySelector("#picker-cad-inspect-status")
   ?.textContent.includes("Local-only GLB attached"),null,{timeout:20000});
  const isolated=page.locator("#picker-cad-file-inspector canvas");
  await isolated.waitFor({state:"visible",timeout:10000});
  assert.equal(await isolated.getAttribute("data-cad-inspection"),"ISOLATED_NOT_ASSEMBLED");
  assert.equal(await isolated.getAttribute("data-fit-authority"),"NONE");
  assertBrowser((await page.locator("#picker-cad-inspect-status").innerText())
   .includes("UNITS UNKNOWN"),"Local mesh was silently converted to millimeters");
  assert.equal(await page.locator("#picker-visual-svg [data-exploded-part]").count(),7,
   "Imported mesh replaced the integrated board");
  note("Real Chromium imports and orbits isolated synthetic GLB without assembly authority");
  assert.equal(await page.locator("#picker-kit-rows tr").count(),7,
   "Complete Loaded maker kit must expose seven source-listed child categories");
  assert.equal(await page.locator("#picker-explode").inputValue(),"0");
  assert.equal(await page.locator("#picker-assemble").getAttribute("aria-pressed"),"true");
  assertBrowser((await page.locator("#picker-visual-svg").innerText()).includes(
   "INTEGRATED BOARD"),"Complete board not visibly assembled by default");
  assertBrowser((await page.locator("#picker-cad-status").innerText())
   .includes("normalized schematic"),"Unmeasured CAD semantics missing");
  assert.equal(await page.locator("#picker-part-tree [data-picker-part]").count(),7,
   "Source-bound tree must expose seven separately selectable kit components");
  assert.equal(await page.locator("#picker-visual-svg [data-exploded-part]").count(),7,
   "2D visual must contain seven independently explodable kit components");
  const inspectButton=page.locator("#picker-kit-rows [data-kit-inspect]").nth(2);
  const inspectId=await inspectButton.getAttribute("data-kit-inspect");
  await inspectButton.click();
  assert.equal(await page.locator("#picker-part-tree [aria-pressed=true]")
    .getAttribute("data-picker-part"),inspectId);
  assertBrowser((await page.locator("#picker-component-detail").innerText())
   .includes("not a standalone seller order line"),
   "Kit ledger selection failed to explain that children are not new purchases");
  assertBrowser((await page.locator("#picker-rendered-scene-status").innerText())
   .includes("0 measured mounts or received pieces"),"3D falsely claims a received kit");
  const kit105=await page.locator("#picker-kit-summary").innerText();
  assertBrowser(kit105.includes("SELLER PACKAGE REVISION CONFLICT HOLD")&&
    kit105.includes("0 verified received components")&&
    kit105.includes("0 separate child purchases"),
   "Source package rows must preserve V2/V3 conflict and no-double-buy status");
  const kitDownload=page.waitForEvent("download");
  await page.locator("#picker-export-kit").click();
  const kitPacket=JSON.parse(await readFile(await (await kitDownload).path(),"utf8"));
  assert.equal(kitPacket.rows.length,7);
  assert.equal(kitPacket.actual_seller_unit_count,null);
  assert.equal(kitPacket.independent_additional_item_orders,0);
  assert.equal(kitPacket.authority.procurement_authorized,false);
  const fullDownload=page.waitForEvent("download");
  await page.locator("#picker-export-json").click();
  const fullPacket=JSON.parse(await readFile(await (await fullDownload).path(),"utf8"));
  assert.equal(fullPacket.display_graph.components.length,7);
  assert.equal(fullPacket.display_graph.kit_parent_variant_id,kitPacket.variant_id);
  assert.equal(fullPacket.report.qualified_supplier_order_lines,0);
  assert.equal(fullPacket.display_graph.completeness.physical_connections_qualified,0);
  assert.equal(fullPacket.parametric_cad_display.child_count,7);
  assert.equal(fullPacket.parametric_cad_display.published_dimensions_mm.wheel_diameter,105);
  assert.equal(fullPacket.parametric_cad_display.physical_mates_verified,0);
  const cadEvent=page.waitForEvent("download");
  await page.locator("#picker-cad-export").click();
  const schema=JSON.parse(await readFile(await (await cadEvent).path(),"utf8"));
  assert.equal(schema.scope,"BROWSER_PARAMETRIC_CAD_DISPLAY_UNQUALIFIED");
  assert.equal(schema.published_dimensions_mm.complete_length,914);
  assert.equal(schema.children.length,7);
  assert.equal(schema.authority.fabrication_authorized,false);
  assert.ok(schema.children.every(x=>x.true_mount_datum_mm===null));
  let retail=await page.locator("#picker-retail-results").innerText();
  assertBrowser(retail.includes("Loaded Boards")&&retail.includes("Skates USA"),
   "105 mm setup must compare two merchants");
  assertBrowser(retail.includes("424.00"),"105 mm listed price missing");
  assertBrowser(retail.includes("NOT verified exact checkout SKU"),
   "Unqualified seller identity warning missing");
  assertBrowser(retail.includes("INCLUSION REVISION CONFLICT HOLD")&&
   retail.includes("Do not treat these as identical seller kits")&&
   retail.includes("PARIS V2")&&retail.includes("PARIS V3"),
   "Retail truck revision conflict was hidden from the user");
  assertBrowser(!retail.includes("Published setup price gap"),
   "Mismatched retailer packages must not show an equal-price comparison");
  await clickStudy(page,"long-nimble");
  assert.equal(await page.locator("#picker-kit-rows tr").count(),7);
  assert.equal(await page.locator("#picker-cad-capture-tasks .cad-capture-role").count(),7);
  assertBrowser((await page.locator("#picker-cad-capture-status").innerText())
   .includes("20/20 evidence tasks open"),"Kit switch should reset measurement evidence");
  const capture85Download=page.waitForEvent("download");
  await page.locator("#picker-cad-capture-template").click();
  const capture85Template=JSON.parse(await readFile(await (await capture85Download).path(),"utf8"));
  assert.notEqual(capture85Template.kit_variant_id,fieldTemplate.kit_variant_id);
  assert.deepEqual(capture85Template.records,[]);
  const leads85Download=page.waitForEvent("download");
  await page.locator("#picker-cad-source-export").click();
  const leads85=JSON.parse(await readFile(await (await leads85Download).path(),"utf8"));
  assert.match(leads85.rows.find(x=>x.role==="wheels").source_url,/caguama-85mm/);
  assert.equal(leads85.qualified_models,0);
  assert.notEqual(leads85.kit_variant_id,sourceLead.kit_variant_id);
  const kit85=await page.locator("#picker-kit-summary").innerText();
  assertBrowser(kit85.includes("loaded-tangent-caguama85")&&
    !kit85.includes("loaded-tangent-dadbod105"),
    "Choosing Caguama left the old Dad Bod complete kit graph active");
  retail=await page.locator("#picker-retail-results").innerText();
  assertBrowser(retail.includes("364.00"),"85 mm offer price not visible");
  assertBrowser(!retail.includes("424.00"),"85 mm selection leaked 105 mm retailer offer");
  note("Retail offers distinguish 85/105 mm named setups and disclaim checkout identity");
  assert.equal(await page.locator("#picker-explode").inputValue(),"0");
  const visual85=await page.locator("#picker-visual-svg [data-exploded-part]")
    .evaluateAll(els=>els.map(x=>x.getAttribute("data-exploded-part")));
  assert.equal(await page.locator("#picker-cad-metric-export").isDisabled(),true);
  const switchedEvidence=await page.locator("#picker-cad-maker-dimensions").textContent();
  assertBrowser(switchedEvidence.includes("85 mm")&&!switchedEvidence.includes("105 mm"),
   "Maker wheel diameter evidence leaked from 105 to 85 mm");
  assertBrowser(visual85.every(id=>id.includes("caguama85")),
   "Old 105 mm kit child IDs leaked into new visual graph");
  await page.locator("#picker-3d").click();
  const canvas=page.locator("#picker-visual-3d canvas");
  await canvas.waitFor({state:"visible",timeout:30000});
  await page.waitForFunction(()=>{
    const c=document.querySelector("#picker-visual-3d canvas");
    return c?.dataset.scenePartCount==="7"&&Number(c.dataset.renderedFrames)>0;
  },null,{timeout:30000});
  assertBrowser(await canvas.evaluate(c=>!!(
    c.getContext("webgl2")||c.getContext("webgl"))&&c.width>100&&c.height>100),
    "No successful WebGL context with seven maker source-named children");
  assertBrowser((await canvas.getAttribute("data-scene-part-ids")).includes("caguama85"),
    "Canvas painted incorrect source kit");
  assert.equal(await canvas.getAttribute("data-assembly-pose"),"ASSEMBLED_VISUAL_STUDY");
  assert.equal(await canvas.getAttribute("data-assembly-separation"),"0");
  assert.equal(await canvas.getAttribute("data-cad-schema-scope"),
   "BROWSER_PARAMETRIC_CAD_DISPLAY_UNQUALIFIED");
  const gpu=await canvas.evaluate(el=>({
    calls:Number(el.dataset.drawCalls),triangles:Number(el.dataset.triangles)
  }));
  assertBrowser(Number.isFinite(gpu.calls)&&gpu.calls>0&&gpu.calls<=90&&
   Number.isFinite(gpu.triangles)&&gpu.triangles>0&&gpu.triangles<120000,
   "CAD viewer geometry exceeded prototype draw budget: "+JSON.stringify(gpu));

  await screenshot(page,"integrated-board-parametric-cad-webgl");
  await page.locator("#picker-separate").click();
  assert.equal(await canvas.getAttribute("data-assembly-pose"),"EXPLODED_VISUAL_STUDY");
  assert.equal(await canvas.getAttribute("data-assembly-separation"),"100");
  assert.equal(await page.locator("#picker-separate").getAttribute("aria-pressed"),"true");
  await page.locator('#picker-camera-controls [data-camera="top"]').click();
  assert.equal(await canvas.getAttribute("data-camera-preset"),"top");
  await page.locator('#picker-part-tree [data-picker-part]').nth(3).click();
  const chosenId=await page.locator('#picker-part-tree [data-picker-part]')
   .nth(3).getAttribute("data-picker-part");
  assert.equal(await canvas.getAttribute("data-selected-component-id"),chosenId);
  await page.locator("#picker-explode").evaluate(el=>{
    el.value="100";el.dispatchEvent(new Event("input",{bubbles:true}));
  });
  assertBrowser((await page.locator("#picker-explode-output").innerText()).includes("100"),
    "Exploded slider failed to update real WebGL scene");
  await screenshot(page,"longboard-kit-seven-part-live-webgl");
  await page.locator("#picker-assemble").click();
  assert.equal(await canvas.getAttribute("data-assembly-pose"),"ASSEMBLED_VISUAL_STUDY");
  assert.equal(await canvas.getAttribute("data-assembly-separation"),"0");
  await page.locator("#picker-2d").click();
  assertBrowser((await page.locator("#picker-visual-svg").innerText())
   .includes("INTEGRATED BOARD"),"SVG and WebGL assembled states diverged");
  note("Parametric complete board assembles and explodes in actual WebGL, SVG and source-locked exports");
  note("Seven child IDs render in actual local WebGL, camera and keyboard selection work");
  await page.locator("#picker-domain").selectOption("alpine_ski");
  await clickStudy(page,"ski-playful-short");
  const skiListings=await page.locator("#picker-retail-results").innerText();
  assertBrowser(skiListings.includes("must NOT be compared")&&
   skiListings.includes("skis plus Marker")&&skiListings.includes("skis /"),
   "Different ski-only and with-binding packages were treated as equal");
  assertBrowser((await page.locator("#picker-findings").innerText()).toLowerCase()
   .includes("professional"),"Ski professional release/mount warnings missing");
  await clickStudy(page,"ski-balanced-94");
  const salomonRetail=await page.locator("#picker-retail-results").innerText();
  assertBrowser(!salomonRetail.includes("Atomic Bent 90"),
   "Unrelated Atomic retailer bundles leaked into a selected Salomon QST study");
  assertBrowser(salomonRetail.includes("No distinct seller sources"),
   "Missing size-matched Salomon retailer evidence must remain a clear hold");
  note("Ski bundles are family-bound; unqualified Atomic offers do not leak into Salomon");
  await page.locator("#picker-domain").selectOption("snowboard");
  await clickStudy(page,"snow-compact-step");
  await page.locator("details.fit-controls summary").click();
  await page.locator("#picker-left").fill("230");
  await page.locator("#picker-right").fill("235");
  const warnings=await page.locator("#picker-findings").innerText();
  assertBrowser(warnings.includes("Different left/right Mondo"),
   "Independent foot-length review missing");
  await page.locator("#picker-mass").fill("105");
  const cardText=await page.locator("#picker-study-cards").innerText();
  assertBrowser(cardText.includes("compatibility/review findings"),
   "Rider range warnings not reflected in cards");
  await page.locator("#picker-study-cards .study-card").first()
   .locator("summary").click();
  assertBrowser((await page.locator(
   '#picker-study-cards [data-warning-code="MAKER_WEIGHT_BAND_REVIEW"]').count())>=1,
   "The published weight-range warning was not accessible to the rider");
  await page.locator("#picker-mass").fill("999");
  assertBrowser((await page.locator("#picker-mass-validation").innerText())
   .includes("outside the supported"),"Invalid rider mass lacks visible explanation");
  assertBrowser(!(await page.locator("#picker-order-status").innerText())
   .includes("Selection held"),"Invalid optional mass left stale order study");
  await page.locator("#picker-mass").fill("105");
  note("Asymmetric foot sizing and invalid/range weight data remain review-only");
  // Download must remain a research report, never an order.
  const event=page.waitForEvent("download");
  await page.locator("#picker-export-json").click();
  const download=await event;
  const p=await download.path();
  const json=JSON.parse(await readFile(p,"utf8"));
  assert.equal(json.report.checkout_eligible,false);
  assert.equal(json.report.known_order_total_usd,null);
  assert.equal(json.report.qualified_supplier_order_lines,0);
  assert.equal(json.report.authority.procurement_authorized,false);
  assert.equal(json.report.authority.fabrication_authorized,false);
  assert.equal(json.maker_unit_observations.actual_checkout_total,null);
  const d2=page.waitForEvent("download");
  await page.locator("#picker-export-csv").click();
  const csv=await readFile(await (await d2).path(),"utf8");
  assertBrowser(csv.includes('"UNKNOWN"')&&csv.includes("Historical maker pack examples"),
   "CSV does not distinguish research pack evidence from seller order units");
  note("Actual browser JSON/CSV downloads preserve zero approved order lines");
  // Focus operation should work from keyboard, independent of the WebGL surface.
  await page.locator("#picker-part-tree [data-picker-part]").first().focus();
  await page.keyboard.press("Enter");
  const selected=await page.locator("#picker-part-tree [data-picker-part][aria-pressed=true]").count();
  assert.equal(selected,1);
  note("Part tree remains keyboard operable");
  await page.emulateMedia({media:"print"});
  assert.equal(await page.locator("#picker-export-json").isVisible(),false);
  assert.equal(await page.locator("#picker-order-table").isVisible(),true);
  assert.equal(await page.locator("#picker-visual-svg").isVisible(),true);
  await screenshot(page,"print-css-preview");
  await page.emulateMedia({media:"screen"});
  note("Print stylesheet preserves evidence and hides misleading interactive checkout controls");
  noErrors();
  await desktop.close();

  // Fully synthetic intercepted registry: neither OEM geometry nor a real catalog asset.
  const sha=b=>createHash("sha256").update(b).digest("hex");
  const glb=syntheticLocalGlb(true),glbSha=sha(glb),stepSha="f".repeat(64);
  const receipt={
   schema_version:1,scope:"STEP_TO_GLTF_CONVERSION_RECEIPT_NOT_MEASURED_FIT",
   source_step_sha256:stepSha,output_glb_sha256:glbSha,
   source_cad_units:"mm",gltf_scene_units:"m",mm_to_gltf_m_scale:.001,
   source_step_bytes:8192,output_glb_bytes:glb.length,
   source_bounds_mm:[[0,0,0],[40,20,12]],source_extents_mm:[40,20,12],
   gltf_sorted_extents_m:[.012,.02,.04],max_sorted_extent_error_mm:0,
   tessellation_tolerance_mm:.2,angular_tolerance_rad:.15,
   geometry_revision_confirmed:false,mounting_datums_verified:false,
   physical_clearance_qualified:false,procurement_authorized:false,
   fabrication_authorized:false
  };
  const receiptBytes=Buffer.from(JSON.stringify(receipt));
  const fake={
   asset_id:"cad-synthetic-browser-test",
   kit_variant_id:"loaded-tangent-complete-105 mm Dad Bod 77a",role:"deck",
   part_number:"SYNTHETIC-TEST-ONLY",revision:"NOT-OEM",origin:"INDEPENDENTLY_MEASURED",
   source_url:"https://example.com/unverified-synthetic",license:"TEST_ONLY_NO_REDISTRIBUTION",
   evidence_date:"2026-10-12",format:"glb",units:"mm",gltf_scene_units:"m",
   mm_to_gltf_m_scale:.001,source_step_sha256:stepSha,
   conversion_receipt_sha256:sha(receiptBytes),
   conversion_receipt_path:"/assets/cad/"+glbSha+".conversion.json",
   sha256:glbSha,path:"/assets/cad/"+glbSha+".glb",byte_length:glb.length,
   asset_revision_confirmed:false,verified_mount_datums:false,
   clearance_qualified:false,physical_fit_qualified:false,
   preview_pose_authority:"NONE",actual_received_units:null,
   separate_order_lines:0,metric_assembly_transform:null,mount_datums_mm:null
  };
  const registry=JSON.parse(await readFile(
   path.join(root,"catalog/outdoor_cad_asset_registry.v1.json"),"utf8"));
  registry.assets.push(fake);
  const pinnedContext=await browser.newContext({viewport:{width:1280,height:800}});
  const pinnedPage=await pinnedContext.newPage();
  const pinnedErrors=await browserErrors(pinnedPage,"pinned receipt experiment");
  await pinnedPage.route("**/catalog/outdoor_cad_asset_registry.v1.json",route=>
   route.fulfill({status:200,contentType:"application/json",body:JSON.stringify(registry)}));
  await pinnedPage.route("**/assets/cad/"+glbSha+".glb",route=>
   route.fulfill({status:200,contentType:"model/gltf-binary",body:glb}));
  const receiptRoute="**/assets/cad/"+glbSha+".conversion.json";
  await pinnedPage.route(receiptRoute,route=>route.fulfill({
   status:200,contentType:"application/json",body:receiptBytes}));
  await initialized(pinnedPage);
  await pinnedPage.locator("#picker-cad-import-lab > summary").click();
  assert.equal(await pinnedPage.locator("[data-cad-asset]").count(),1);
  await pinnedPage.locator("[data-cad-asset]").click();
  await pinnedPage.waitForFunction(()=>document.querySelector("#picker-cad-inspect-status")
   ?.textContent.includes("visible model extents agree"),null,{timeout:30000});
  assert.equal(await pinnedPage.locator("#picker-cad-file-inspector canvas")
   .getAttribute("data-fit-authority"),"NONE");
  await pinnedPage.unroute(receiptRoute);
  await pinnedPage.route(receiptRoute,route=>route.fulfill({
   status:200,contentType:"application/json",
   body:Buffer.from(JSON.stringify({...receipt,source_step_sha256:"e".repeat(64)}))}));
  await pinnedPage.locator("[data-cad-asset]").click();
  await pinnedPage.waitForFunction(()=>document.querySelector("#picker-cad-inspect-status")
   ?.textContent.includes("Candidate CAD held:"),null,{timeout:10000});
  assert.equal(await pinnedPage.locator("#picker-cad-file-inspector").isHidden(),true);
  assert.equal(await pinnedPage.locator("#picker-visual-svg [data-exploded-part]").count(),7);
  pinnedErrors();await pinnedContext.close();
  note("Chromium pinned synthetic GLB requires dual hashes and visible dimensions; tampered receipt held");
  for(const vp of [{width:390,height:844,name:"mobile-390"},
                   {width:768,height:1024,name:"tablet-768"},
                   {width:1280,height:800,name:"desktop-1280"}]){
   const context=await browser.newContext({viewport:{width:vp.width,height:vp.height},
    deviceScaleFactor:1,isMobile:vp.width===390,hasTouch:vp.width===390});
   const shot=await context.newPage();
   const errors=await browserErrors(shot,vp.name);
   await initialized(shot);
   await checkNoOverflow(shot,vp.name);
   await shot.locator("#picker-domain").selectOption("skateboard_longboard");
   await clickStudy(shot,"long-nimble");
   await checkNoOverflow(shot,vp.name+" after selecting longboard");
   await screenshot(shot,vp.name);
   errors();await context.close();
  }
  note("390, 768, 1280 and 1440 px screenshots captured with overflow checks");
  // Simulated CDN denial must recover the original source-linked SVG.
  const fallbackContext=await browser.newContext({viewport:{width:1280,height:820}});
  const fallback=await fallbackContext.newPage();
  await fallback.route("https://esm.sh/**",route=>route.abort("failed"));
  await fallback.route("**/node_modules/three/**",route=>route.abort("failed"));
  const fallbackErrors=await browserErrors(fallback,"WebGL dependency fallback");
  await initialized(fallback);
  await fallback.locator("#picker-3d").click();
  await fallback.locator('#picker-2d[aria-pressed="true"]').waitFor({timeout:25000});
  assert.equal(await fallback.locator("#picker-visual-svg").isVisible(),true);
  assertBrowser((await fallback.locator("#picker-view-note").innerText()).includes("SVG"),
   "3D failure did not explain SVG fallback");
  await screenshot(fallback,"cdn-unavailable-svg-fallback");
  fallbackErrors();await fallbackContext.close();
  note("Unavailable pinned-local and CDN Three.js both fall back to SVG without losing parts");
  await writeFile(path.join(artifacts,"browser-qa.json"),JSON.stringify({
   status:"PASS",checks,viewport_widths:[390,768,1280,1440],
   head_sha:process.env.PARTS_BROWSER_HEAD_SHA??null,
   explicit_limitations:["Browser simulation is not physical CAD qualification",
    "CDN success/WebGL performance not qualified","Mobile on-device touch not manually inspected",
    "No seller availability, checkout SKU or current shipping verified"]
  },null,2)+"\n");
  console.log("Browser smoke PASS. Evidence: "+artifacts);
 }finally{
  if(browser)await browser.close();
 }
}
try{await main();}
catch(error){
 faults.push({message:String(error?.stack||error)});
 await mkdir(artifacts,{recursive:true});
 await writeFile(path.join(artifacts,"browser-qa.json"),JSON.stringify({
  status:"FAIL",checks,faults,head_sha:process.env.PARTS_BROWSER_HEAD_SHA??null
 },null,2)+"\n");
 console.error(error);process.exitCode=1;
}finally{
 srv.kill("SIGTERM");
}
