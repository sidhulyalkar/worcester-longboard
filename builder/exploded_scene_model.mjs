// Graph-driven 3D layout contract. All coordinates are UNIT-LESS proxies.
// No scene coordinates are physical measurements, mounting offsets or clearances.
export const SCENE_SCOPE = "UNQUALIFIED_ASSEMBLY_3D_VISUAL_PROXY";
const BASIS = "UNSCALED_SEMANTIC_PROXY_NOT_DIMENSIONAL_CAD";
const vectors = Object.freeze({
  platform: [0, 0, 0], mount: [-1.0, 0.5, 1.0],
  ground: [1.2, -0.15, 0.1], rider: [0, 0, 1.65],
  control: [1.1, 0.9, 0.7], power: [-1.1, -0.75, -0.55],
  utility: [0, 1.3, 1.1]
});
const clamp = (n, fallback=78) => Number.isFinite(Number(n))
  ? Math.max(0, Math.min(100, Number(n))) : fallback;

export function planExplodedScene(graph, {separation=78, selectedId=null}={}) {
  if (graph?.scope !== "UNQUALIFIED_SEMANTIC_ASSEMBLY_EXPLODED_VIEW" ||
      !Array.isArray(graph.components) || !Array.isArray(graph.groups) ||
      !graph.components.length ||
      graph.safety?.physical_qualification !== "NOT_QUALIFIED" ||
      !graph.authority || Object.values(graph.authority).some(Boolean))
    throw new Error("3D viewer requires an unqualified, authority-locked assembly graph");
  const groupIds = new Set(graph.groups.map(g=>g.id));
  if (groupIds.size !== graph.groups.length ||
      [...groupIds].some(id=>!Object.hasOwn(vectors,id)))
    throw new Error("Unsupported or duplicate 3D assembly group");
  const ids = new Set();
  const t = clamp(separation)/100;
  const positions = graph.components.map(node => {
    if (!node || typeof node.component_id !== "string" || !node.component_id ||
        ids.has(node.component_id) || !groupIds.has(node.group_id) ||
        node.exact_variant_verified !== false || node.visual_proxy_only !== true)
      throw new Error("Invalid, duplicate or claimed-qualified 3D part");
    ids.add(node.component_id);
    const peers = graph.components.filter(p=>p.group_id===node.group_id);
    const ordinal = peers.findIndex(p=>p.component_id===node.component_id);
    const offset = ordinal-(peers.length-1)/2;
    const [gx,gy,gz] = vectors[node.group_id];
    // Local ordinals avoid perfectly superposed reference lines at zero separation.
    const position = [
      gx*3.0*t + offset*0.33*t,
      gy*2.8*t + offset*1.25*t,
      (node.group_id==="platform" ? 0 : 0.18) + gz*2.35*t +
        (node.group_id==="rider" ? 0.32 : 0)
    ];
    return {
      component_id:node.component_id, label:node.label, role:node.role,
      group_id:node.group_id, source_kind:node.source_kind,
      selected:node.component_id===selectedId, position,
      proxy_geometry:true, exact_geometry_verified:false,
      metric_dimensions_mm:null, physical_mount_point_mm:null
    };
  });
  return {
    schema_version:1, scope:SCENE_SCOPE, basis:BASIS,
    subject_id:graph.subject_id, domain_id:graph.domain_id,
    separation_percent:clamp(separation), selected_id:ids.has(selectedId)?selectedId:null,
    parts:positions, physical_fit_verified:false, physical_release_authorized:false,
    quantity_verified:false, units:"ARBITRARY_VISUAL_UNITS",
    safety_note:"All shapes, part sizes and placements are illustrative. No dimensions or fastener locations have been qualified."
  };
}
