// Fail-closed GLB v2 preflight, before any file reaches the optional GLTFLoader.
// A mesh alone never establishes scale, revision, mating datums or fit.
const fail=msg=>{throw Error("GLB inspection: "+msg);};
const check=(ok,msg)=>{if(!ok)fail(msg);};
export function inspectGlbBytes(input){
 const data=input instanceof ArrayBuffer?input:
  ArrayBuffer.isView(input)?input.buffer.slice(input.byteOffset,input.byteOffset+input.byteLength):null;
 check(data&&data.byteLength>=28&&data.byteLength<=25000000,
  "select a nonempty .glb smaller than 25 MB");
 const view=new DataView(data);
 check(view.getUint32(0,true)===0x46546c67&&view.getUint32(4,true)===2&&
  view.getUint32(8,true)===data.byteLength,"GLB v2 header / length mismatch");
 const jsonLength=view.getUint32(12,true);
 check(view.getUint32(16,true)===0x4e4f534a&&
  jsonLength>0&&jsonLength<=2000000&&20+jsonLength<=data.byteLength,
  "missing or oversized JSON chunk");
 let json;
 try{json=JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(
  new Uint8Array(data,20,jsonLength)).trim());}
 catch{fail("invalid glTF JSON");}
 check(json?.asset?.version==="2.0"&&Array.isArray(json.meshes)&&
  json.meshes.length>0&&json.meshes.length<=256&&
  Array.isArray(json.nodes)&&json.nodes.length<=4096,
  "unsupported scene or mesh count");
 check((json.extensionsRequired??[]).every(x=>typeof x==="string"&&
  !x.startsWith("KHR_draco")&&!x.startsWith("EXT_meshopt")),
  "compressed or unsupported required extension needs offline conversion");
 // Local untrusted files must be fully self-contained; no external URLs
 // or data URI bombs. GLB buffers with absent URI use the binary chunk.
 for(const b of [...(json.buffers??[]),...(json.images??[])]){
  check(!("uri" in b),"external or data URI resources are not allowed");
 }
 check((json.buffers??[]).length<=1&&json.accessors?.length<=16384,
  "GLB structure exceeds inspector budget");
 const meshes=json.meshes;
 let vertices=0;
 for(const m of meshes){
  check(Array.isArray(m.primitives)&&m.primitives.length<=64,
   "mesh primitive count invalid");
  for(const p of m.primitives){
   const accessor=json.accessors?.[p.attributes?.POSITION];
   check(accessor&&Number.isSafeInteger(accessor.count)&&accessor.count>=0,
    "POSITION accessor required");
   vertices+=accessor.count;
   check(vertices<=1000000,"more than one million vertices");
  }
 }
 return {format:"glb",version:2,bytes:data.byteLength,
  mesh_count:meshes.length,node_count:json.nodes.length,
  vertex_reference_count:vertices,source:"LOCAL_UNVERIFIED_FILE",
  units:"UNKNOWN_NOT_INFERRED",mount_datums_verified:0,
  clearance_status:"NOT_EVALUATED",physical_fit_qualified:false};
}
