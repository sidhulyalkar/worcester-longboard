// Browser release gate: real Chromium, real local HTTP server and four source catalogs.
// Historical supplier data must not turn into a checkout-ready or qualified product.
// Run: npm install --no-save --no-package-lock playwright@1.56.1
//      npx playwright install chromium
//      node tests/browser/parts_picker_smoke.mjs
import assert from "node:assert/strict";
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
  assert.equal(await page.locator("#picker-kit-rows tr").count(),7,
   "Complete Loaded maker kit must expose seven source-listed child categories");
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
  const kit85=await page.locator("#picker-kit-summary").innerText();
  assertBrowser(kit85.includes("loaded-tangent-caguama85")&&
    !kit85.includes("loaded-tangent-dadbod105"),
    "Choosing Caguama left the old Dad Bod complete kit graph active");
  retail=await page.locator("#picker-retail-results").innerText();
  assertBrowser(retail.includes("364.00"),"85 mm offer price not visible");
  assertBrowser(!retail.includes("424.00"),"85 mm selection leaked 105 mm retailer offer");
  note("Retail offers distinguish 85/105 mm named setups and disclaim checkout identity");
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
  const fallbackErrors=await browserErrors(fallback,"WebGL dependency fallback");
  await initialized(fallback);
  await fallback.locator("#picker-3d").click();
  await fallback.locator('#picker-2d[aria-pressed="true"]').waitFor({timeout:25000});
  assert.equal(await fallback.locator("#picker-visual-svg").isVisible(),true);
  assertBrowser((await fallback.locator("#picker-view-note").innerText()).includes("SVG"),
   "3D failure did not explain SVG fallback");
  await screenshot(fallback,"cdn-unavailable-svg-fallback");
  fallbackErrors();await fallbackContext.close();
  note("Unavailable 3D CDN falls back to source-linked 2D without breaking worklist");
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
