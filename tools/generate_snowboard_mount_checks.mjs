#!/usr/bin/env node
import {evaluateSnowboardMountReference} from "../builder/snowboard_mount_reference.mjs";
const cases=[
 {board_mount:"CHANNEL_M6_REFERENCE",binding_mount:"REFLEX",disc_family:"BURTON_REFLEX_COMBO",boot_retention:"STRAP"},
 {board_mount:"CHANNEL_M6_REFERENCE",binding_mount:"REFLEX",disc_family:"BURTON_REFLEX_COMBO",boot_retention:"STEP_ON_ONLY"},
 {board_mount:"2X4_REFERENCE",binding_mount:"EST",disc_family:null},
 {board_mount:"3D_LEGACY_REFERENCE",binding_mount:"REFLEX",disc_family:"BURTON_REFLEX_COMBO"},
 {board_mount:"CHANNEL_M6_REFERENCE",binding_mount:"EST",disc_family:null},
 {board_mount:"4X4_REFERENCE",binding_mount:"REFLEX",disc_family:"BURTON_REFLEX_COMBO"},
 {board_mount:"3D_LEGACY_REFERENCE",binding_mount:"REFLEX",disc_family:"BURTON_3D_HINGE"},
 {board_mount:"UNKNOWN",binding_mount:"REFLEX",disc_family:"BURTON_REFLEX_COMBO"}
];
console.log(JSON.stringify(cases.map(x=>({input:x,output:evaluateSnowboardMountReference(x)}))));
