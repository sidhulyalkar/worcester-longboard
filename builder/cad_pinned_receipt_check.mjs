// Byte-to-receipt verification for locally pinned CAD candidates.
// Intentionally does not certify OEM authenticity, shape, mounting or fit.
import {validateCadConversionReceipt} from "./cad_conversion_receipt.mjs";
const hold=msg=>{throw Error("Pinned CAD receipt: "+msg);};
const bytes=x=>x instanceof ArrayBuffer?new Uint8Array(x):
 ArrayBuffer.isView(x)?new Uint8Array(x.buffer,x.byteOffset,x.byteLength):null;
const hash=x=>typeof x==="string"&&/^[a-f0-9]{64}$/.test(x);
async function digest(data,cryptoImpl){
 const result=new Uint8Array(await cryptoImpl.subtle.digest("SHA-256",data));
 return [...result].map(n=>n.toString(16).padStart(2,"0")).join("");
}
export async function verifyPinnedCadCandidate(candidate,glb,receiptData,{
 cryptoImpl=globalThis.crypto}={}){
 const modelBytes=bytes(glb),metadataBytes=bytes(receiptData);
 if(!modelBytes||modelBytes.length<28||modelBytes.length>25000000||
  !metadataBytes||metadataBytes.length<20||metadataBytes.length>32768)
  hold("bounded GLB and conversion receipt bytes required");
 if(!cryptoImpl?.subtle?.digest)hold("browser SHA-256 support required");
 if(!candidate||candidate.byte_length!==modelBytes.length||
  !hash(candidate.sha256)||!hash(candidate.conversion_receipt_sha256)||
  !hash(candidate.source_step_sha256)||
  candidate.conversion_receipt_path!==
   "/assets/cad/"+candidate.sha256+".conversion.json"||
  candidate.path!=="/assets/cad/"+candidate.sha256+".glb"||
  candidate.units!=="mm"||candidate.gltf_scene_units!=="m"||
  candidate.mm_to_gltf_m_scale!==0.001)
  hold("registry geometry identity or declared units invalid");
 const actualModel=await digest(modelBytes,cryptoImpl);
 if(actualModel!==candidate.sha256)hold("GLB SHA-256 mismatch");
 const actualReceipt=await digest(metadataBytes,cryptoImpl);
 if(actualReceipt!==candidate.conversion_receipt_sha256)
  hold("conversion receipt SHA-256 mismatch");
 let receipt;
 try{
  receipt=JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(metadataBytes));
 }catch{hold("receipt is not valid UTF-8 JSON");}
 const verified=validateCadConversionReceipt(receipt,{
  output_sha256:actualModel,output_bytes:modelBytes.length});
 if(verified.source_step_sha256!==candidate.source_step_sha256)
  hold("original STEP digest disagrees with pinned registry");
 return {scope:"HASH_AND_SCALE_RECEIPT_MATCH_NOT_OEM_APPROVAL",
  geometry_sha256:actualModel,
  conversion_receipt_sha256:actualReceipt,
  original_step_sha256:verified.source_step_sha256,
  scale_m_per_source_mm:verified.scale_m_per_source_mm,
  expected_sorted_gltf_extents_m:receipt.gltf_sorted_extents_m,
  bbox_comparison_tolerance_mm:Math.max(receipt.tessellation_tolerance_mm*0.1,0.02),
  manufacturer_authenticity_qualified:false,
  source_revision_qualified:false,mounting_datums_qualified:false,
  physical_clearance_qualified:false,purchase_authorized:false};
}

export function verifyPinnedCadSceneExtents(checked,sceneBounds){
 const numbers=sceneBounds&&[sceneBounds.x,sceneBounds.y,sceneBounds.z];
 if(checked?.scope!=="HASH_AND_SCALE_RECEIPT_MATCH_NOT_OEM_APPROVAL"||
  !Array.isArray(checked.expected_sorted_gltf_extents_m)||
  checked.expected_sorted_gltf_extents_m.length!==3||
  !numbers?.every(n=>typeof n==="number"&&Number.isFinite(n)&&n>0&&n<=10))
  hold("scene extent audit needs nondegenerate glTF-meter bounds");
 const found=[...numbers].sort((a,b)=>a-b);
 const err=Math.max(...found.map((n,i)=>Math.abs(
  n-checked.expected_sorted_gltf_extents_m[i])*1000));
 if(err>checked.bbox_comparison_tolerance_mm)
  hold("loaded 3D mesh dimensions differ from hashed STEP conversion receipt");
 return {scope:"VISIBLE_GLB_EXTENTS_AGREE_WITH_RECEIPT_NOT_FIT",
  max_sorted_extent_difference_mm:err,
  tolerance_mm:checked.bbox_comparison_tolerance_mm,
  manufacturer_authenticity_qualified:false,physical_clearance_qualified:false,
  fabrication_authorized:false};
}
