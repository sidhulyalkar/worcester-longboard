// Reconcile SELF-REPORTED receiving observations to a source-bound Build Passport.
// This is a review queue, not a stock count, a verified BOM, or an assembly release.
import {restoreEvidenceNotebook} from "./evidence_notebook.mjs";
const AUTHORITY={
 procurement_authorized:false,fabrication_authorized:false,
 charging_authorized:false,powered_operation_authorized:false,
 generic_builder_may_promote_x1_authority:false
};
const sorted=items=>[...new Set(items)].sort();
export function buildReceivingReconciliation(passport,rawNotebook,documentIndex){
 if(passport?.scope!=="NON_AUTHORITATIVE_BUILD_PASSPORT" ||
    typeof passport.study_identity_key!=="string" || !Array.isArray(passport.parts))
   throw new Error("Receiving reconciliation needs a Build Passport snapshot");
 if(documentIndex?.scope!=="PUBLIC_MANUFACTURER_REFERENCES_NOT_EXACT_VARIANT_INSTRUCTIONS" ||
    documentIndex.schema_version!==1 || !Array.isArray(documentIndex.entries))
   throw new Error("Receiving reconciliation needs a vetted public-reference catalog");
 const notebook=restoreEvidenceNotebook(passport,rawNotebook);
 const entries=new Map();
 for(const entry of documentIndex.entries){
   if(typeof entry.id!=="string" || entries.has(entry.id) || !Array.isArray(entry.component_ids) ||
     typeof entry.url!=="string" || !entry.url.startsWith("https://") ||
     entry.exact_revision_verified!==false)
     throw new Error("Invalid or duplicate public document reference");
   entries.set(entry.id,entry);
 }
 const audit=passport.assembly_inventory_audit;
 const possibleOverlaps=audit?.overlap_worklist||[];
 const donors=audit?.package_claims||[];
 const partIndex=new Map(passport.parts.map(x=>[x.component_id,x]));
 const rows=passport.parts.map(part=>{
   const receipts=notebook.records.filter(x=>
     x.kind==="RECEIVING_OBSERVATION"&&x.component_id===part.component_id);
   const last=receipts.length?receipts[receipts.length-1]:null;
   const revisions=sorted(receipts.map(x=>x.observed_revision));
   const counts=sorted(receipts.map(x=>String(x.quantity_received)));
   const conflicting=revisions.length>1||counts.length>1;
   const manualCandidates=notebook.records.filter(x=>
     x.kind==="MANUFACTURER_INSTRUCTIONS_CANDIDATE"&&x.component_id===part.component_id);
   const docs=[...entries.values()].filter(x=>x.component_ids.includes(part.component_id))
     .map(x=>({id:x.id,title:x.title,url:x.url,role:x.document_role,
       scope_note:x.scope_note,exact_revision_verified:false}));
   const overlap=possibleOverlaps.filter(x=>x.component_id===part.component_id)
     .map(x=>x.package_id).sort();
   const donor=donors.some(x=>x.package_id===part.component_id);
   const missing=[
     ...(!receipts.length?["RECEIVING_OBSERVATION"]:[]),
     ...(conflicting?["CONFLICTING_RECEIPT_HISTORY"]:[]),
     ...(donor?["DONOR_CONTENTS_AND_INCLUSIONS_INSPECTION"]:[]),
     ...(overlap.length?["POSSIBLE_DONOR_DOUBLE_COUNT"]:[]),
     ...(!docs.length?["MANUFACTURER_DOCUMENT_REFERENCE"]:[]),
     "INDEPENDENT_RECEIVED_REVISION_VERIFICATION",
     "EXACT_REVISION_APPLICABLE_MAKER_MANUAL",
     "VERIFIED_BOM_ASSEMBLY_QUANTITY",
     "VERIFIED_SUPPLIER_ORDER_UNIT",
     "INDEPENDENT_PHYSICAL_FIT_AND_SAFETY"
   ];
   return {
     component_id:part.component_id,label:part.label,
     variant_identity_key:part.variant_identity_key,
     catalog_sku_text:part.sku_text,
     recorded_receiving_count:receipts.length,
     last_observation: last?{
       observed_revision:last.observed_revision,
       quantity_received:last.quantity_received,
       observed_as_of:last.as_of,
       receipt_seq:last.seq,
       authority:"USER_REPORTED_NOT_VERIFIED"
     }:null,
     receipt_history_status:!receipts.length?"NO_RECEIVING_OBSERVATION":
       conflicting?"CONFLICTING_RECEIPT_HISTORY_REVIEW":
       "SELF_REPORTED_RECEIPT_NEEDS_INDEPENDENT_REVIEW",
     received_inventory_verified:false,
     physical_revision_verified:false,
     actual_assembly_quantity:null,
     actual_supplier_order_quantity:null,
     potential_overlap_package_ids:overlap,
     donor_content_evidence_status:donor?"UNVERIFIED_DONOR_CONTENTS":
       "NOT_A_SELECTED_DONOR_PACKAGE",
     manufacturer_reference_documents:docs,
     user_manual_candidate_count:manualCandidates.length,
     revision_matched_manufacturer_manual_verified:false,
     missing_evidence:missing
   };
 });
 const missingReceipt=rows.filter(x=>x.recorded_receiving_count===0).map(x=>x.component_id);
 const conflict=rows.filter(x=>x.receipt_history_status==="CONFLICTING_RECEIPT_HISTORY_REVIEW")
   .map(x=>x.component_id);
 const donorWork=rows.filter(x=>x.donor_content_evidence_status==="UNVERIFIED_DONOR_CONTENTS")
   .map(x=>x.component_id);
 return {
   schema_version:1,scope:"UNVERIFIED_RECEIVING_RECONCILIATION",
   candidate_id:passport.candidate_id,study_identity_key:passport.study_identity_key,
   document_index_reviewed_as_of:documentIndex.reviewed_as_of,
   evidence_record_count:notebook.records.length,
   rows,
   review_queue:{
     no_receiving_observation_ids:missingReceipt,
     conflicting_receipt_history_ids:conflict,
     donor_contents_uninspected_ids:donorWork,
     donor_overlap_questions:possibleOverlaps.map(x=>({
       package_id:x.package_id,component_id:x.component_id,
       question:x.review_question,physically_resolved:false
     })),
     retrofit_questions:(audit?.retrofit_worklist||[]).map(x=>({
       package_id:x.package_id,component_id:x.component_id,
       question:x.question,physically_resolved:false
     })),
     unresolved_interface_ids:passport.interface_claims.map(x=>x.id).sort()
   },
   confirmation:{
     order_lines_qualified:0,physical_part_revisions_qualified:0,
     manufacturer_manuals_revision_verified:0,received_contents_qualified:0,
     price_quotes_current_verified:0,
     physical_qualification:"NOT_QUALIFIED"
   },
   authority:{...AUTHORITY},
   disclaimer:"A user-reported count is not inventoried stock, a design quantity or an order count. Old or mismatched snapshots are rejected. Official manufacturer pages provide general documentation context only; no applicable exact revision or physical fit is established."
 };
}
