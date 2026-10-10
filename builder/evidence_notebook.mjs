// Local, user-entered evidence receipts for revision-specific Build Passports.
// Evidence here is testimony/document pointers, NOT independently verified fit,
// stock, install instructions, electrical safety, purchase or operation authority.
const AUTHORITY={
  procurement_authorized:false,fabrication_authorized:false,
  charging_authorized:false,powered_operation_authorized:false,
  generic_builder_may_promote_x1_authority:false
};
export const EVIDENCE_KINDS=[
  "SOURCE_REFERENCE","RECEIVING_OBSERVATION",
  "MANUFACTURER_INSTRUCTIONS_CANDIDATE","INTERFACE_MEASUREMENT_NOTE"
];
const KIND_SET=new Set(EVIDENCE_KINDS);
const strictText=(value,max=240)=>{
  if(value===null || value===undefined || value==="")return null;
  if(typeof value!=="string" || value.length>max || !value.trim())throw new Error("Invalid bounded evidence text");
  const trimmed=value.trim();
  if(/[\u0000-\u001f\u007f]/u.test(trimmed))throw new Error("Evidence contains control characters");
  return trimmed;
};
function safeUrl(value) {
  const v=strictText(value,600);
  if(!v)return null;
  let url;
  try{url=new URL(v);}catch{throw new Error("Evidence link must be a valid HTTPS URL");}
  if(url.protocol!=="https:" || !url.hostname || url.username || url.password)
    throw new Error("Evidence link must be an HTTPS URL without credentials");
  return v;
}
function dateStamp(value){
  const s=strictText(value,10);
  if(!s)return null;
  if(!/^\d{4}-\d{2}-\d{2}$/.test(s))throw new Error("Use a real YYYY-MM-DD evidence date");
  const parsed=new Date(s+"T00:00:00.000Z");
  if(Number.isNaN(parsed.valueOf()) || parsed.toISOString().slice(0,10)!==s)
    throw new Error("Use a real YYYY-MM-DD evidence date");
  return s;
}
function requirePassport(passport){
  if(passport?.scope!=="NON_AUTHORITATIVE_BUILD_PASSPORT" ||
     typeof passport.study_identity_key!=="string" ||
     !Array.isArray(passport.parts) || !Array.isArray(passport.interface_claims))
    throw new Error("Evidence notebook needs a complete Build Passport");
}
export function emptyEvidenceNotebook(passport){
  requirePassport(passport);
  return {
    schema_version:1,scope:"SELF_REPORTED_UNVERIFIED_EVIDENCE",
    candidate_id:passport.candidate_id,
    study_identity_key:passport.study_identity_key,
    records:[],
    authority:{...AUTHORITY}
  };
}
function assertNotebook(passport,book){
  requirePassport(passport);
  if(!book || book.schema_version!==1 ||
     book.scope!=="SELF_REPORTED_UNVERIFIED_EVIDENCE" ||
     book.candidate_id!==passport.candidate_id ||
     book.study_identity_key!==passport.study_identity_key ||
     !Array.isArray(book.records) || book.records.length>80)
    throw new Error("Evidence notebook belongs to a different Build Passport snapshot");
}
export function recordEvidence(notebook,passport,input){
  assertNotebook(passport,notebook);
  if(!input || typeof input!=="object" || !KIND_SET.has(input.kind))
    throw new Error("Select a supported evidence record kind");
  const kind=input.kind;
  const componentId=strictText(input.component_id,128);
  const part=passport.parts.find(p=>p.component_id===componentId);
  if(!part)throw new Error("Evidence component is not in this exact passport");
  const interfaceId=strictText(input.interface_id,240);
  if(interfaceId && !passport.interface_claims.some(x=>x.id===interfaceId &&
    x.component_ids.includes(componentId)))
    throw new Error("Interface claim does not include the selected component");
  if(kind==="INTERFACE_MEASUREMENT_NOTE" && !interfaceId)
    throw new Error("Measurement notes must name an affected interface claim");
  if(kind!=="INTERFACE_MEASUREMENT_NOTE" && interfaceId)
    throw new Error("Interface ID is only supported on measurement notes");
  const revision=strictText(input.observed_revision,120);
  const quantity=input.quantity_received==="" || input.quantity_received===null ||
    input.quantity_received===undefined ? null : input.quantity_received;
  if(quantity!==null && (!Number.isInteger(quantity)||quantity<1||quantity>500))
    throw new Error("Receiving count must be a positive integer at most 500");
  const url=safeUrl(input.evidence_url);
  const asOf=dateStamp(input.as_of);
  const note=strictText(input.note,500);
  if(!revision && quantity===null && !url && !note)
    throw new Error("Record a revision, quantity, HTTPS evidence link or observation");
  if(kind==="SOURCE_REFERENCE" && (!url || !asOf))
    throw new Error("Source reference requires an HTTPS link and date");
  if(kind==="MANUFACTURER_INSTRUCTIONS_CANDIDATE" && (!url || !asOf || !revision))
    throw new Error("Instruction candidate requires HTTPS link, date and exact marked revision");
  if(kind==="RECEIVING_OBSERVATION" && (!revision || quantity===null || !asOf))
    throw new Error("Receiving observation needs exact marked revision, received count and date");
  if(kind==="INTERFACE_MEASUREMENT_NOTE" && !note)
    throw new Error("Interface note must describe the measured question and missing evidence");
  if(kind!=="RECEIVING_OBSERVATION" && quantity!==null)
    throw new Error("Received count only applies to receiving observations");
  if(notebook.records.length>=80)throw new Error("Notebook limit reached; export before more entries");
  // Reconstruct the entire receipt rather than trusting any input status or authority.
  const record={
    seq:notebook.records.length+1,
    kind,component_id:componentId,interface_id:interfaceId,
    target_variant_identity_key:part.variant_identity_key,
    observed_revision:revision,quantity_received:quantity,
    evidence_url:url,as_of:asOf,note,
    review_status:"USER_RECORDED_NOT_INDEPENDENTLY_VERIFIED",
    usable_for_qualification:false
  };
  return {...emptyEvidenceNotebook(passport),records:[...notebook.records,record]};
}
export function restoreEvidenceNotebook(passport,raw){
  const empty=emptyEvidenceNotebook(passport);
  if(!raw)return empty;
  try{
    const input=typeof raw==="string"?JSON.parse(raw):raw;
    assertNotebook(passport,input);
    let restored=empty;
    for(const record of input.records){
      // Rebind to the current part and revalidate every field. Never trust saved
      // review_status, selected revision claims or authority fields.
      if(record.target_variant_identity_key!==passport.parts.find(
        x=>x.component_id===record.component_id)?.variant_identity_key)
        return empty;
      restored=recordEvidence(restored,passport,record);
    }
    return restored;
  }catch{return empty;}
}
export function evaluateEvidenceNotebook(passport,notebook){
  assertNotebook(passport,notebook);
  // A notebook object may be directly supplied by a caller, not just browser
  // storage. Reconstruct each record to strip forged status and reject staleness.
  const reviewed=restoreEvidenceNotebook(passport,notebook);
  const observed=new Set(),instructionCandidates=new Set(),sourceReferences=new Set();
  const invalidated=new Set(),measurementNotes=new Set();
  const partIndex=new Map(passport.parts.map(p=>[p.component_id,p]));
  for(const rec of reviewed.records){
    if(rec.kind==="RECEIVING_OBSERVATION"){
      observed.add(rec.component_id);
      const part=partIndex.get(rec.component_id);
      for(const claim of passport.interface_claims){
        if(claim.component_ids.includes(rec.component_id) || part.included_by_donor.length)
          invalidated.add(claim.id);
      }
    }
    if(rec.kind==="MANUFACTURER_INSTRUCTIONS_CANDIDATE")instructionCandidates.add(rec.component_id);
    if(rec.kind==="SOURCE_REFERENCE")sourceReferences.add(rec.component_id);
    if(rec.kind==="INTERFACE_MEASUREMENT_NOTE")measurementNotes.add(rec.interface_id);
  }
  const sorted=set=>[...set].sort();
  return {
    schema_version:1,scope:"USER_EVIDENCE_REVIEW_QUEUE",
    candidate_id:passport.candidate_id,
    evidence_count:reviewed.records.length,
    receiving_observed_part_ids:sorted(observed),
    source_reference_part_ids:sorted(sourceReferences),
    instruction_candidates_part_ids:sorted(instructionCandidates),
    noted_interface_ids:sorted(measurementNotes),
    invalidated_interface_ids:sorted(invalidated),
    still_unverified_part_ids:passport.parts.map(x=>x.component_id).filter(id=>!observed.has(id)),
    unresolved_interface_ids:passport.interface_claims
      .filter(x=>["UNKNOWN","MEASURE_FIRST"].includes(x.reference_state))
      .map(x=>x.id).sort(),
    manufacturer_manuals_independently_verified:0,
    assembly_quantities_authorized:0,
    stock_confirmed:0,
    physical_qualification:"NOT_QUALIFIED",
    authority:{...AUTHORITY},
    note:"All entries are user-provided observations or candidate links. Receiving counts are not order quantities; notes do not resolve interface claims. Independent revision-specific evidence and separate engineering approvals remain necessary."
  };
}
