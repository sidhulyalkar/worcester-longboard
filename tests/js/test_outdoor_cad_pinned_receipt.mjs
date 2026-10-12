import test from "node:test";
import assert from "node:assert/strict";
import {createHash,webcrypto} from "node:crypto";
import {verifyPinnedCadCandidate,verifyPinnedCadSceneExtents}
 from "../../builder/cad_pinned_receipt_check.mjs";
const hash=b=>createHash("sha256").update(b).digest("hex");
function fixture(){
 const glb=Buffer.alloc(48,1);glb.write("glTF",0);
 const sourceHash="c".repeat(64);
 const receipt={
  schema_version:1,scope:"STEP_TO_GLTF_CONVERSION_RECEIPT_NOT_MEASURED_FIT",
  source_step_sha256:sourceHash,output_glb_sha256:hash(glb),
  source_cad_units:"mm",gltf_scene_units:"m",mm_to_gltf_m_scale:0.001,
  source_step_bytes:1024,output_glb_bytes:glb.length,
  source_bounds_mm:[[0,0,0],[40,20,12]],
  source_extents_mm:[40,20,12],
  gltf_sorted_extents_m:[.012,.020,.040],max_sorted_extent_error_mm:0,
  tessellation_tolerance_mm:.2,angular_tolerance_rad:.15,
  geometry_revision_confirmed:false,mounting_datums_verified:false,
  physical_clearance_qualified:false,procurement_authorized:false,
  fabrication_authorized:false
 };
 const receiptBytes=Buffer.from(JSON.stringify(receipt));
 const candidate={
  sha256:hash(glb),byte_length:glb.length,
  source_step_sha256:sourceHash,
  conversion_receipt_sha256:hash(receiptBytes),
  conversion_receipt_path:"/assets/cad/"+hash(glb)+".conversion.json",
  path:"/assets/cad/"+hash(glb)+".glb",
  units:"mm",gltf_scene_units:"m",mm_to_gltf_m_scale:0.001
 };
 return {glb,receipt,receiptBytes,candidate};
}
const verify=(a)=>verifyPinnedCadCandidate(a.candidate,a.glb,
 a.receiptBytes,{cryptoImpl:webcrypto});
test("both pinned byte digests and mm to glTF meter receipt must match",async()=>{
 const data=await verify(fixture());
 assert.equal(data.scope,"HASH_AND_SCALE_RECEIPT_MATCH_NOT_OEM_APPROVAL");
 assert.equal(data.scale_m_per_source_mm,.001);
 assert.equal(data.manufacturer_authenticity_qualified,false);
 assert.equal(data.source_revision_qualified,false);
 assert.equal(data.mounting_datums_qualified,false);
 assert.equal(data.physical_clearance_qualified,false);
 assert.equal(data.purchase_authorized,false);
 const match=verifyPinnedCadSceneExtents(data,{x:.04,y:.02,z:.012});
 assert.equal(match.scope,"VISIBLE_GLB_EXTENTS_AGREE_WITH_RECEIPT_NOT_FIT");
 assert.equal(match.physical_clearance_qualified,false);
 assert.throws(()=>verifyPinnedCadSceneExtents(data,{x:.04,y:.02,z:.013}),/loaded 3D mesh dimensions differ/);
 assert.throws(()=>verifyPinnedCadSceneExtents(data,{x:.04,y:.02,z:0}),/nondegenerate/);
});
test("tampered geometry, receipt, source digest, path and forged approval are held",async()=>{
 const mutate=[
  a=>a.glb[31]^=3,
  a=>a.receiptBytes=Buffer.concat([a.receiptBytes,Buffer.from(" ")]),
  a=>a.candidate.sha256="f".repeat(64),
  a=>a.candidate.source_step_sha256="a".repeat(64),
  a=>a.candidate.conversion_receipt_sha256="a".repeat(64),
  a=>a.candidate.conversion_receipt_path="/source/unpinned.json",
  a=>a.candidate.gltf_scene_units="mm",
  a=>a.candidate.byte_length-=1,
  a=>{a.receipt.fabrication_authorized=true;
   a.receiptBytes=Buffer.from(JSON.stringify(a.receipt));
   a.candidate.conversion_receipt_sha256=hash(a.receiptBytes);}
 ];
 for(const update of mutate){
  const v=fixture();update(v);
  await assert.rejects(()=>verify(v),/(Pinned CAD receipt:|CAD conversion receipt:)/);
 }
});
test("parse-failed and oversized audit receipts never open candidate geometry",async()=>{
 const v=fixture();
 v.receiptBytes=Buffer.from("bad-json-doesnt-work-anymore");
 v.candidate.conversion_receipt_sha256=hash(v.receiptBytes);
 await assert.rejects(()=>verify(v),/not valid UTF-8 JSON/);
 const big=fixture();
 big.receiptBytes=Buffer.alloc(33000,7);
 await assert.rejects(()=>verify(big),/bounded GLB and conversion receipt/);
});
