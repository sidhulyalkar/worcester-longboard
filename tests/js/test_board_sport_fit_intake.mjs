import test from "node:test";
import assert from "node:assert/strict";
import {assessBoardSportFit} from "../../builder/sport_fit_intake.mjs";
const base={sport:"snowboard",rider_height_cm:157,rider_mass_kg:50,
 left_mondo_mm:225,right_mondo_mm:230,board_mount:"CHANNEL_M6_REFERENCE",
 binding_mount:"REFLEX",disc_family:"BURTON_REFLEX_COMBO",boot_retention:"STRAP"};
test("known snowboard family match is still a fit and source hold",()=>{
 const result=assessBoardSportFit(base);
 assert.equal(result.qualification,"NOT_QUALIFIED");
 assert.equal(result.manufacturer_reference.verdict,"MAKER_FAMILY_REFERENCE_MATCH_REVIEW_REQUIRED");
 assert.ok(result.findings.some(x=>x.code==="ASYMMETRIC_BOOT_FIT"));
 assert.equal(result.exact_product_variants_verified,false);
 assert.equal(result.checkout_eligible,false);
 assert.ok(Object.values(result.authority).every(x=>x===false));
});
test("wrong mount family and absent legacy disc block instead of guessing",()=>{
 const mismatch=assessBoardSportFit({...base,board_mount:"2X4_REFERENCE",binding_mount:"EST"});
 assert.equal(mismatch.qualification,"DECLARED_INTERFACE_CONFLICT");
 assert.ok(mismatch.findings.some(x=>x.status==="INCOMPATIBLE"));
 const missing=assessBoardSportFit({...base,board_mount:"3D_LEGACY_REFERENCE"});
 assert.equal(missing.qualification,"DECLARED_INTERFACE_CONFLICT");
});
test("Step On reports separate exact boot model and size review",()=>{
 const r=assessBoardSportFit({...base,boot_retention:"STEP_ON_ONLY"});
 assert.ok(r.findings.some(x=>x.code==="STEP_ON_BOOT_PAIR"&&x.status==="REVIEW_REQUIRED"));
 assert.equal(r.physical_fit_verified,false);
});
test("ski sole norm mismatches fail closed, professional release remains mandatory",()=>{
 const r=assessBoardSportFit({sport:"alpine_ski",rider_height_cm:157,
  rider_mass_kg:50,left_mondo_mm:225,right_mondo_mm:230,
  boot_sole_norm:"ISO_9523_TOURING",binding_accepted_norms:["ISO_5355_ADULT"],
  boot_sole_length_mm:280,ski_waist_mm:90,brake_width_mm:100});
 assert.equal(r.qualification,"DECLARED_INTERFACE_CONFLICT");
 assert.ok(r.findings.some(x=>x.code==="SKI_BOOT_BINDING_NORM"&&x.status==="INCOMPATIBLE"));
 assert.ok(r.findings.some(x=>x.code==="PROFESSIONAL_SKI_BINDING_RELEASE"));
 assert.equal(r.binding_release_verified,false);
});
test("numerically plausible brake widths cannot certify ski interfaces",()=>{
 const r=assessBoardSportFit({sport:"alpine_ski",boot_sole_norm:"ISO_5355_ADULT",
 binding_accepted_norms:["ISO_5355_ADULT"],boot_sole_length_mm:285,
 ski_waist_mm:95,brake_width_mm:100});
 assert.equal(r.qualification,"NOT_QUALIFIED");
 assert.equal(r.findings.find(x=>x.code==="SKI_BRAKE_AND_WAIST").status,"REVIEW_REQUIRED");
 assert.equal(r.checkout_eligible,false);
});
test("unknown and malformed rider inputs never become validated boot sizes",()=>{
 const r=assessBoardSportFit({sport:"alpine_ski",rider_height_cm:999,
 left_mondo_mm:"NaN",right_mondo_mm:"",rider_mass_kg:""}); 
 assert.deepEqual(r.rider,{height_cm:null,mass_kg:null,left_mondo_mm:null,right_mondo_mm:null});
 assert.ok(r.findings.some(x=>x.code==="INCOMPLETE_RIDER_INPUT"));
 assert.throws(()=>assessBoardSportFit({sport:"splitboard"}),/limited/);
});
