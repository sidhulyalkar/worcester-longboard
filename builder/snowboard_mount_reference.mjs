// Maker-family mounting reference checks, not binding assembly or physical fit approval.
const AUTH={procurement_authorized:false,fabrication_authorized:false,
 charging_authorized:false,powered_operation_authorized:false,
 generic_builder_may_promote_x1_authority:false};
export function evaluateSnowboardMountReference(input){
 const board=input?.board_mount??null,binding=input?.binding_mount??null;
 const disc=input?.disc_family??null,retention=input?.boot_retention??null;
 const validBoard=["CHANNEL_M6_REFERENCE","2X4_REFERENCE","4X4_REFERENCE","3D_LEGACY_REFERENCE"];
 const validBinding=["REFLEX","EST","UNSPECIFIED"];
 const validDisc=[null,"BURTON_REFLEX_COMBO","BURTON_3D_HINGE","UNSPECIFIED"];
 if(!validBoard.includes(board)||!validBinding.includes(binding)||!validDisc.includes(disc))
   return {
     scope:"MAKER_MOUNTING_FAMILY_PLANNING_ONLY",verdict:"UNKNOWN_REFERENCE",
     reason:"Unrecognized or missing mounting/adapter family. Hold for an exact manufacturer reference.",
     boot_fit:"NOT_VERIFIED",physical_fit_verified:false,
     install_authorized:false,authority:{...AUTH}
   };
 let verdict="UNKNOWN_REFERENCE",reason="Mounting variant/disc details are unresolved.";
 if(binding==="EST" && board!=="CHANNEL_M6_REFERENCE"){
   verdict="MANUFACTURER_REFERENCE_INCOMPATIBLE";
   reason="Burton EST has Channel-only mounting; non-Channel board reference conflicts.";
 }else if(binding==="EST"){
   verdict="CHANNEL_FAMILY_CANDIDATE_REVIEW";
   reason="Channel-only EST family matches this board reference, but physical hardware/revision must be checked.";
 }else if(binding==="REFLEX"){
   if(board==="3D_LEGACY_REFERENCE" && disc!=="BURTON_3D_HINGE"){
     verdict="REQUIRED_SPECIAL_DISC_MISSING";
     reason="Burton Re:Flex on the legacy 3D pattern needs a 3D Hinge disc, not asserted included.";
   }else if(board==="CHANNEL_M6_REFERENCE" && disc==="BURTON_REFLEX_COMBO"){
     verdict="MAKER_FAMILY_REFERENCE_MATCH_REVIEW_REQUIRED";
     reason="Burton names the Combo Disc for Re:Flex and Channel; exact hardware, binding size and boot fit remain unverified.";
   }else if(board==="4X4_REFERENCE" && disc==="BURTON_REFLEX_COMBO"){
     verdict="MAKER_FAMILY_REFERENCE_MATCH_REVIEW_REQUIRED";
     reason="Burton names Re:Flex Combo Disc for 4x4; exact binding/fasteners/fit still require review.";
   }else{
     verdict="ADAPTER_AND_HARDWARE_REVIEW_REQUIRED";
     reason="Burton Re:Flex needs the correct mounting disc and exact hardware for this board family.";
   }
 }
 return {
   scope:"MAKER_MOUNTING_FAMILY_PLANNING_ONLY",verdict,reason,
   boot_fit:retention==="STEP_ON_ONLY"?"STEP_ON_BOOT_MODEL_SIZE_REQUIRED":
     "BOOT_BINDING_FIT_NOT_VERIFIED",
   physical_fit_verified:false,install_authorized:false,authority:{...AUTH}
 };
}
