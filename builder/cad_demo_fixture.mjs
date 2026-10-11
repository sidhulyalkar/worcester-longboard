// Synthetic numerical example. Deliberately NOT Loaded/Paris/Caguama geometry,
// dimensions, kinematics, measurement data, source CAD or a parts purchase list.
export function makeSyntheticCandidateMotionFixture(variantId){
 if(typeof variantId!=="string"||variantId.length<4)
  throw Error("Synthetic CAD demo requires an exact selected kit identity");
 const pairs=[[0,0,0],[5,0,0],[0,5,0],[0,0,5]];
 const part=(id,dx,box)=>({
  id,source_url:"https://example.com/synthetic-motion-algorithm-fixture",
  revision:"SYNTHETIC-NOT-OEM",geometry_evidence:"UNVERIFIED_CANDIDATE_BOUNDS",
  mating_datums_physically_verified:false,exact_revision_received:false,
  survey_tolerance_mm:0.25,local_bounds_mm:box,
  correspondences:pairs.map(p=>({local_mm:p,
   assembly_mm:[p[0]+dx,p[1],p[2]]}))
 });
 return {schema_version:1,scope:"METRIC_CAD_SURVEY_FIXTURE_RESEARCH_ONLY",
  kit_variant_id:variantId,units:"mm",
  fixture_type:"SYNTHETIC_NUMERICAL_DEMO_NOT_REAL_ASSEMBLY",
  authority:{procurement_authorized:false,fabrication_authorized:false,
   physical_fit_qualified:false},
  parts:[
   part("example_moving_box",0,{min_mm:[3,-1,-1],max_mm:[5,1,1]}),
   part("example_static_box",4,{min_mm:[-1,-1,-1],max_mm:[1,1,1]})
  ],motion:{
   scope:"CANDIDATE_MOTION_RESEARCH_ONLY",
   moving_part_id:"example_moving_box",
   stationary_part_ids:["example_static_box"],
   axis_point_assembly_mm:[0,0,0],
   axis_direction_assembly:[0,0,1],
   angle_range_deg:[-45,45],sample_step_deg:15,
   uncertainty_mm:0.25,kinematics_physically_verified:false,
   dynamic_clearance_qualified:false,contact_verified:false
  }};
}
