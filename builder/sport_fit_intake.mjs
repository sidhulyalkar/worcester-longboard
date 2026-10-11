// Personal fit intake for snowboard and alpine ski STUDIES, not a sizing solver.
// No input here is an exact manufacturer size chart, release setting or purchase approval.
import {evaluateSnowboardMountReference} from "./snowboard_mount_reference.mjs";
const AUTHORITY=Object.freeze({
 procurement_authorized:false, fabrication_authorized:false,
 charging_authorized:false,powered_operation_authorized:false,
 generic_builder_may_promote_x1_authority:false
});
const knownSoleNorms=["ISO_5355_ADULT","ISO_23223_GRIPWALK","ISO_9523_TOURING"];
const field=(code,status,text)=>({code,status,text});
const num=(v,min,max)=>{
 if(v===null||v===undefined||String(v).trim()==="")return null;
 const n=Number(v);return Number.isFinite(n)&&n>=min&&n<=max?n:null;
};
export function assessBoardSportFit(input={}){
 const sport=input.sport;
 if(sport!=="snowboard" && sport!=="alpine_ski")
  throw new Error("Fit intake is limited to snowboard and alpine ski research");
 const findings=[];
 const height=num(input.rider_height_cm,80,230);
 const mass=num(input.rider_mass_kg,20,250);
 const left=num(input.left_mondo_mm,150,360);
 const right=num(input.right_mondo_mm,150,360);
 const stated=[height,mass,left,right];
 if(stated.some(v=>v===null))findings.push(field("INCOMPLETE_RIDER_INPUT","UNKNOWN",
  "Record rider height, mass and each foot's measured Mondo length. No boot size is inferred."));
 if(left!==null&&right!==null&&left!==right)
  findings.push(field("ASYMMETRIC_BOOT_FIT","REVIEW_REQUIRED",
  "Left and right foot measurements differ. Size each boot and verify retention independently; do not assume a symmetric setup."));
 let mount=null;
 if(sport==="snowboard"){
  mount=evaluateSnowboardMountReference({
   board_mount:input.board_mount||null,
   binding_mount:input.binding_mount||null,
   disc_family:input.disc_family||null,
   boot_retention:input.boot_retention||null
  });
  findings.push(field("SNOWBOARD_MOUNT_FAMILY",
   mount.verdict==="MANUFACTURER_REFERENCE_INCOMPATIBLE" ||
   mount.verdict==="REQUIRED_SPECIAL_DISC_MISSING"?"INCOMPATIBLE":
   mount.verdict==="UNKNOWN_REFERENCE"?"UNKNOWN":"REVIEW_REQUIRED",
   mount.reason));
  findings.push(field("SNOWBOARD_EXACT_VARIANT","REVIEW_REQUIRED",
   "Capture exact board length/revision, binding size/revision, mounting disc, insert hardware and official size charts."));
  if(input.boot_retention==="STEP_ON_ONLY")
   findings.push(field("STEP_ON_BOOT_PAIR","REVIEW_REQUIRED",
    "Match each actual Step On boot model and size to an exact compatible binding size and revision."));
  else findings.push(field("STRAP_BOOT_BINDING_SIZE","REVIEW_REQUIRED",
    "Use the manufacturer's boot and binding size charts for both feet; check stance width and setback physically."));
 }else{
  const sole=input.boot_sole_norm||null;
  const accepted=Array.isArray(input.binding_accepted_norms)?input.binding_accepted_norms:[];
  const valid=knownSoleNorms.includes(sole)&&accepted.length>0&&
   accepted.every(v=>knownSoleNorms.includes(v));
  const mismatch=valid&&!accepted.includes(sole);
  findings.push(field("SKI_BOOT_BINDING_NORM",
   mismatch?"INCOMPATIBLE":valid?"REVIEW_REQUIRED":"UNKNOWN",
   mismatch?"Declared ski boot sole standard is not among declared binding-accepted standards. Do not pair.":
   valid?"Nominal standard pairing is a research candidate only; verify exact boot and binding model revisions with manufacturer.":
   "Exact boot sole norm and manufacturer-confirmed accepted binding norms are required."));
  const bsl=num(input.boot_sole_length_mm,180,380);
  findings.push(field("SKI_BOOT_SOLE_LENGTH",bsl===null?"UNKNOWN":"REVIEW_REQUIRED",
   bsl===null?"Record each boot's marked sole length in millimeters.":
   "Boot sole length recorded. Binding adjustment range and exact mount position are still unverified."));
  const waist=num(input.ski_waist_mm,45,180);
  const brake=num(input.brake_width_mm,50,200);
  findings.push(field("SKI_BRAKE_AND_WAIST",waist===null||brake===null?"UNKNOWN":"REVIEW_REQUIRED",
   "Manufacturer-approved brake model, measured clearance and ski waist/interface must be matched by a technician; numeric width alone never qualifies fit."));
  findings.push(field("PROFESSIONAL_SKI_BINDING_RELEASE","REVIEW_REQUIRED",
   "Qualified ski technician must mount/inspect binding, verify boot interface and determine/test release settings. No DIY or automatic release setting."));
 }
 const conflict=findings.some(x=>x.status==="INCOMPATIBLE");
 return {
  schema_version:1,scope:"PERSONALIZED_BOARD_SPORT_FIT_RESEARCH_ONLY",
  sport,qualification:conflict?"DECLARED_INTERFACE_CONFLICT":"NOT_QUALIFIED",
  data_provenance:"USER_DECLARATIONS_NOT_MANUFACTURER_VERIFIED",
  rider:{height_cm:height,mass_kg:mass,left_mondo_mm:left,right_mondo_mm:right},
  manufacturer_reference:mount,findings,
  exact_product_variants_verified:false,physical_fit_verified:false,
  binding_release_verified:false,checkout_eligible:false,
  authority:{...AUTHORITY},
  note:"Fit intake is a conservative research checklist, not personalized approved equipment selection."
 };
}
