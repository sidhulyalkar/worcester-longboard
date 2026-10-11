import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {validateCadAssetRegistry,planCadAssetReadiness}
 from "../../builder/cad_asset_registry.mjs";
import {inspectGlbBytes} from "../../builder/cad_glb_contract.mjs";
import {compileCompleteKitCadDisplay} from "../../builder/complete_kit_cad_schema.mjs";
import {buildPickerStudy} from "../../builder/parts_picker_engine.mjs";
import {auditCompleteKitClaim} from "../../builder/complete_kit_closure.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const load=n=>JSON.parse(fs.readFileSync(path.join(root,"catalog",n),"utf8"));
const registry=load("outdoor_cad_asset_registry.v1.json");
const catalog=load("outdoor_parts_picker.v1.json");
const kit=load("outdoor_complete_kit_claims.v1.json");
const retail=load("outdoor_retail_comparisons.v1.json");
const recipe=load("outdoor_complete_kit_cad_recipes.v1.json");
const id=catalog.products.find(p=>p.id==="loaded-tangent-complete").variants[0].id;
function cad(){
 const study=buildPickerStudy(catalog,{domain_id:"skateboard_longboard",
  selections:{long_complete:id}});
 const audit=auditCompleteKitClaim(study,kit,catalog,retail);
 return compileCompleteKitCadDisplay(study,audit,kit,recipe);
}
const candidate=(variant,role="deck")=>({
 asset_id:"local-test-"+role,kit_variant_id:variant,role,
 part_number:"rev-test",revision:"r1",origin:"INDEPENDENTLY_MEASURED",
 source_url:"https://example.org/evidence",
 license:"CC-BY-4.0",evidence_date:"2026-10-11",
 format:"glb",units:"mm",sha256:"a".repeat(64),
 path:"/assets/cad/"+"a".repeat(64)+".glb",byte_length:1200,
 asset_revision_confirmed:false,verified_mount_datums:false,
 clearance_qualified:false,physical_fit_qualified:false,
 preview_pose_authority:"NONE",actual_received_units:null,
 separate_order_lines:0,metric_assembly_transform:null,mount_datums_mm:null
});
function glbFixture(){
 const positions=new Float32Array([0,0,0,1,0,0,0,1,0]);
 const json={asset:{version:"2.0"},buffers:[{byteLength:36}],
  bufferViews:[{buffer:0,byteOffset:0,byteLength:36}],
  accessors:[{bufferView:0,componentType:5126,count:3,type:"VEC3",
   min:[0,0,0],max:[1,1,0]}],
  meshes:[{primitives:[{attributes:{POSITION:0}}]}],
  nodes:[{mesh:0}],scenes:[{nodes:[0]}],scene:0};
 const body=Buffer.from(JSON.stringify(json));
 const pad=(4-body.length%4)%4;
 const out=Buffer.alloc(12+8+body.length+pad+8+positions.byteLength);
 out.write("glTF",0);out.writeUInt32LE(2,4);out.writeUInt32LE(out.length,8);
 out.writeUInt32LE(body.length+pad,12);out.write("JSON",16);
 body.copy(out,20);out.fill(32,20+body.length,20+body.length+pad);
 const chunk=20+body.length+pad;
 out.writeUInt32LE(positions.byteLength,chunk);out.write("BIN\u0000",chunk+4);
 Buffer.from(positions.buffer).copy(out,chunk+8);
 return out;
}
test("empty CAD registry and complete board stay explicitly unqualified",()=>{
 assert.equal(validateCadAssetRegistry(registry).asset_candidates,0);
 const result=planCadAssetReadiness(cad(),registry);
 assert.equal(result.rows.length,7);
 assert.equal(result.missing_geometry,7);
 assert.equal(result.asset_candidates,0);
 assert.equal(result.clearance_status,"NOT_EVALUATED");
 assert.equal(result.verified_mount_datums,0);
 assert.equal(result.additional_purchase_lines,0);
});
test("revision-specific candidate is visible but cannot imply aligned kit geometry",()=>{
 const model=cad();
 const reg=structuredClone(registry);
 reg.assets=[candidate(model.selected_variant_id)];
 assert.equal(validateCadAssetRegistry(reg).asset_candidates,1);
 const result=planCadAssetReadiness(model,reg);
 assert.equal(result.asset_candidates,1);
 assert.equal(result.rows[0].geometry_status,"GLB_CANDIDATE_UNALIGNED");
 assert.equal(result.rows[0].revision,"r1");
 assert.equal(result.verified_mount_datums,0);
 const other=structuredClone(model);other.selected_variant_id="unrelated-kit";
 assert.equal(planCadAssetReadiness(other,reg).asset_candidates,0);
});
test("duplicate roles, remote paths, false units, authority and datums fail closed",()=>{
 const original=candidate(id);
 const bads=[
  a=>{a.assets.push({...original,asset_id:"another"});},
  a=>{a.assets[0].path="https://example.org/untrusted.glb";},
  a=>{a.assets[0].units="unknown";},
  a=>{a.assets[0].verified_mount_datums=true;},
  a=>{a.assets[0].metric_assembly_transform=[0,0,0];},
  a=>{a.assets[0].sha256="0";},
  a=>{a.authority.procurement_authorized=true;},
  a=>{a.coordinate_policy.allow_automatic_visual_to_metric_alignment=true;}
 ];
 for(const mutate of bads){
  const r=structuredClone(registry);r.assets=[structuredClone(original)];
  mutate(r);
  assert.throws(()=>validateCadAssetRegistry(r),/CAD asset registry:/);
 }
});
test("GLB preflight recognizes self-contained mesh but never assumes millimeters",()=>{
 const bytes=glbFixture();
 const result=inspectGlbBytes(bytes);
 assert.equal(result.mesh_count,1);
 assert.equal(result.vertex_reference_count,3);
 assert.equal(result.units,"UNKNOWN_NOT_INFERRED");
 assert.equal(result.clearance_status,"NOT_EVALUATED");
 const remote=glbFixture();
 const jsonBytes=remote.subarray(20,20+remote.readUInt32LE(12));
 const parsed=JSON.parse(jsonBytes.toString("utf8"));
 parsed.buffers[0].uri="external.bin";
 const serialized=Buffer.from(JSON.stringify(parsed));
 // Structural mutation uses the header length, not a hard-coded offset.
 const extra=Buffer.alloc(12+8+Math.ceil(serialized.length/4)*4+8+36);
 extra.write("glTF");extra.writeUInt32LE(2,4);
 extra.writeUInt32LE(extra.length,8);
 extra.writeUInt32LE(Math.ceil(serialized.length/4)*4,12);
 extra.write("JSON",16);serialized.copy(extra,20);
 extra.fill(32,20+serialized.length,20+Math.ceil(serialized.length/4)*4);
 assert.throws(()=>inspectGlbBytes(extra),/external or data URI/);
 const corrupt=Buffer.from(bytes);corrupt.writeUInt32LE(900,8);
 assert.throws(()=>inspectGlbBytes(corrupt),/header/);
});
