"""Source-referenced snowboard mounting-family logic; no independent install authority."""
from __future__ import annotations

AUTH={
    "procurement_authorized":False,"fabrication_authorized":False,
    "charging_authorized":False,"powered_operation_authorized":False,
    "generic_builder_may_promote_x1_authority":False
}

def evaluate_snowboard_mount_reference(input):
    inp=input or {}
    board=inp.get("board_mount")
    binding=inp.get("binding_mount")
    disc=inp.get("disc_family")
    retention=inp.get("boot_retention")
    valid_board={"CHANNEL_M6_REFERENCE","2X4_REFERENCE","4X4_REFERENCE","3D_LEGACY_REFERENCE"}
    valid_binding={"REFLEX","EST","UNSPECIFIED"}
    valid_disc={None,"BURTON_REFLEX_COMBO","BURTON_3D_HINGE","UNSPECIFIED"}
    if board not in valid_board or binding not in valid_binding or disc not in valid_disc:
        return {
            "scope":"MAKER_MOUNTING_FAMILY_PLANNING_ONLY",
            "verdict":"UNKNOWN_REFERENCE",
            "reason":"Unrecognized or missing mounting/adapter family. Hold for an exact manufacturer reference.",
            "boot_fit":"NOT_VERIFIED","physical_fit_verified":False,
            "install_authorized":False,"authority":dict(AUTH)
        }
    verdict="UNKNOWN_REFERENCE"
    reason="Mounting variant/disc details are unresolved."
    if binding=="EST" and board!="CHANNEL_M6_REFERENCE":
        verdict="MANUFACTURER_REFERENCE_INCOMPATIBLE"
        reason="Burton EST has Channel-only mounting; non-Channel board reference conflicts."
    elif binding=="EST":
        verdict="CHANNEL_FAMILY_CANDIDATE_REVIEW"
        reason="Channel-only EST family matches this board reference, but physical hardware/revision must be checked."
    elif binding=="REFLEX":
        if board=="3D_LEGACY_REFERENCE" and disc!="BURTON_3D_HINGE":
            verdict="REQUIRED_SPECIAL_DISC_MISSING"
            reason="Burton Re:Flex on the legacy 3D pattern needs a 3D Hinge disc, not asserted included."
        elif board=="CHANNEL_M6_REFERENCE" and disc=="BURTON_REFLEX_COMBO":
            verdict="MAKER_FAMILY_REFERENCE_MATCH_REVIEW_REQUIRED"
            reason="Burton names the Combo Disc for Re:Flex and Channel; exact hardware, binding size and boot fit remain unverified."
        elif board=="4X4_REFERENCE" and disc=="BURTON_REFLEX_COMBO":
            verdict="MAKER_FAMILY_REFERENCE_MATCH_REVIEW_REQUIRED"
            reason="Burton names Re:Flex Combo Disc for 4x4; exact binding/fasteners/fit still require review."
        else:
            verdict="ADAPTER_AND_HARDWARE_REVIEW_REQUIRED"
            reason="Burton Re:Flex needs the correct mounting disc and exact hardware for this board family."
    return {
        "scope":"MAKER_MOUNTING_FAMILY_PLANNING_ONLY","verdict":verdict,"reason":reason,
        "boot_fit":"STEP_ON_BOOT_MODEL_SIZE_REQUIRED" if retention=="STEP_ON_ONLY"
                   else "BOOT_BINDING_FIT_NOT_VERIFIED",
        "physical_fit_verified":False,"install_authorized":False,"authority":dict(AUTH)
    }
