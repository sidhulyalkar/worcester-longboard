#!/usr/bin/env node
// Stage a local GLB candidate by content digest. NO fit, mounting or order approval.
// Usage documented in docs/browser_cad_asset_staging_v1.md.
import {readFile,writeFile,copyFile,mkdir,rename,unlink} from "node:fs/promises";
import {createHash} from "node:crypto";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {inspectGlbBytes} from "../builder/cad_glb_contract.mjs";
import {validateCadAssetRegistry} from "../builder/cad_asset_registry.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
function args(argv){
 const out={};
 for(let i=0;i<argv.length;i+=2){
  const k=argv[i];
  if(!k?.startsWith("--")||!argv[i+1])throw Error("Expected --key value pairs");
  out[k.slice(2)]=argv[i+1];
 }
 return out;
}
async function main(){
 const a=args(process.argv.slice(2));
 const required=["file","kit-variant-id","role","part-number","revision",
  "source-url","license","origin","evidence-date","conversion-receipt"];
 if(required.some(k=>!a[k]))throw Error("Missing required flag(s): "+required.filter(k=>!a[k]).join(", "));
 const p=path.resolve(a.file);
 const bytes=await readFile(p);
 const metrics=inspectGlbBytes(bytes);
 const hash=createHash("sha256").update(bytes).digest("hex");
 const receiptBytes=await readFile(path.resolve(a["conversion-receipt"]));
 if(receiptBytes.length>32768)throw Error("Conversion receipt too large");
 const receipt=JSON.parse(receiptBytes.toString("utf8"));
 const digest=x=>typeof x==="string"&&/^[0-9a-f]{64}$/.test(x);
 if(receipt?.schema_version!==1||receipt.scope!==
  "STEP_TO_GLTF_CONVERSION_RECEIPT_NOT_MEASURED_FIT"||
  receipt.output_glb_sha256!==hash||
  !digest(receipt.source_step_sha256)||
  receipt.source_cad_units!=="mm"||receipt.gltf_scene_units!=="m"||
  receipt.mm_to_gltf_m_scale!==0.001||
  receipt.output_glb_bytes!==bytes.length||
  receipt.geometry_revision_confirmed!==false||
  receipt.mounting_datums_verified!==false||
  receipt.physical_clearance_qualified!==false||
  receipt.procurement_authorized!==false||
  receipt.fabrication_authorized!==false||
  !Array.isArray(receipt.source_extents_mm)||
  receipt.source_extents_mm.length!==3||
  !receipt.source_extents_mm.every(x=>Number.isFinite(x)&&x>0&&x<10000)||
  !Number.isFinite(receipt.max_sorted_extent_error_mm)||
  receipt.max_sorted_extent_error_mm<0||
  receipt.max_sorted_extent_error_mm>Math.max(
   receipt.tessellation_tolerance_mm*0.1,0.02))
  throw Error("Pinned millimeter-to-meter conversion receipt invalid or mismatched");
 const receiptHash=createHash("sha256").update(receiptBytes).digest("hex");
 const regPath=path.join(root,"catalog/outdoor_cad_asset_registry.v1.json");
 const reg=JSON.parse(await readFile(regPath,"utf8"));
 validateCadAssetRegistry(reg);
 const kit=JSON.parse(await readFile(path.join(root,"catalog/outdoor_complete_kit_claims.v1.json"),"utf8"));
 if(!kit.kits.some(x=>x.variant_id===a["kit-variant-id"]))
  throw Error("Kit identity must be an existing source-declared complete kit variant");
 const asset={
  asset_id:"cad-"+createHash("sha256").update(a["kit-variant-id"]+":"+a.role+":"+hash)
   .digest("hex").slice(0,32),
  kit_variant_id:a["kit-variant-id"],role:a.role,
  part_number:a["part-number"],revision:a.revision,
  source_url:a["source-url"],license:a.license,
  origin:a.origin,evidence_date:a["evidence-date"],
  format:"glb",units:"mm",gltf_scene_units:"m",
  mm_to_gltf_m_scale:0.001,source_step_sha256:receipt.source_step_sha256,
  conversion_receipt_sha256:receiptHash,sha256:hash,
  path:"/assets/cad/"+hash+".glb",byte_length:bytes.length,
  asset_revision_confirmed:false,verified_mount_datums:false,
  clearance_qualified:false,physical_fit_qualified:false,
  preview_pose_authority:"NONE",actual_received_units:null,
  separate_order_lines:0,metric_assembly_transform:null,mount_datums_mm:null
 };
 // glTF uses meters; the conversion receipt proves the tool's scale choice,
 // NOT that the STEP was authentic or the physical part is dimensionally valid.
 reg.assets.push(asset);validateCadAssetRegistry(reg);
 const target=path.join(root,"assets/cad",hash+".glb");
 await mkdir(path.dirname(target),{recursive:true});
 await copyFile(p,target);
 // Detect a changing input and refuse to record the wrong bytes.
 if(createHash("sha256").update(await readFile(target)).digest("hex")!==hash)
  throw Error("Staged asset hash mismatch");
 const temp=regPath+".pending-"+process.pid;
 try{
  await writeFile(temp,JSON.stringify(reg,null,2)+"\n",{flag:"wx"});
  await rename(temp,regPath);
 }finally{await unlink(temp).catch(()=>{});}
 console.log(JSON.stringify({staged:asset.path,asset_id:asset.asset_id,
  sha256:hash,conversion_receipt_sha256:receiptHash,
  source_step_sha256:receipt.source_step_sha256,
  gltf_scene_units:"m",meshes:metrics.mesh_count,source_revision_confirmed:false,
  fit_qualified:false,clearance_status:"NOT_EVALUATED"},null,2));
}
main().catch(e=>{console.error("CAD import held:",e.message);process.exitCode=1;});
