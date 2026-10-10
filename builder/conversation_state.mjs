// Non-authoritative, deterministic, review-first multi-turn state for Board Builder.
// No model call, network request, checkout action or physical authority is possible here.
import {parseRideBrief,applyRideBriefReview} from "./ride_brief.mjs";

const AUTHORITY = Object.freeze({
  procurement_authorized:false,
  fabrication_authorized:false,
  charging_authorized:false,
  powered_operation_authorized:false,
  generic_builder_may_promote_x1_authority:false
});
const SCOPE = "non_authoritative_ride_conversation";
const REVIEW_SCOPE = "non_authoritative_ride_brief_review";
const own = (obj,key) => Object.prototype.hasOwnProperty.call(obj,key);
const clone = value => JSON.parse(JSON.stringify(value));
const fieldsFor = questionnaire => new Map(
  (questionnaire?.sections || []).flatMap(s=>s.fields || []).map(f=>[f.id,f])
);

function requireState(state) {
  if (!state || state.schema_version!==1 || state.scope!==SCOPE ||
      !Array.isArray(state.turns) || !Array.isArray(state.history) ||
      !state.profile || typeof state.profile!=="object" ||
      Object.values(state.authority || {}).length!==Object.keys(AUTHORITY).length ||
      Object.keys(AUTHORITY).some(k=>state.authority[k]!==false))
    throw new Error("Invalid non-authoritative conversation state");
}

export function createRideConversation(profile,questionnaire) {
  const fields=fieldsFor(questionnaire);
  if(!fields.size || !profile || typeof profile!=="object" || Array.isArray(profile))
    throw new Error("Invalid questionnaire or rider profile");
  for(const key of Object.keys(profile)) {
    if(!fields.has(key))throw new Error("Unknown initial profile key "+key);
  }
  const values=clone(profile),provenance={};
  for(const key of Object.keys(values))
    provenance[key]={source:"PROFILE_BASELINE",revision:0};
  return {
    schema_version:1,scope:SCOPE,revision:0,profile:values,
    provenance,turns:[],history:[],pending:null,authority:{...AUTHORITY}
  };
}

function relativeReview(text,profile,questionnaire) {
  const fields=fieldsFor(questionnaire),out=[];
  const add=(id,label,key,value,reason)=>{
    const field=fields.get(key);
    if(!field || value===profile[key] || typeof value==="number" &&
      (value<field.min || value>field.max))return;
    out.push({
      id,label,patch:{[key]:value},evidence:text,certainty:"INFERRED",
      explanation:reason+" Review before applying. This is a preference, not a predicted board performance."
    });
  };
  if(/\b(?:cheaper|less expensive|lower (?:the )?cost|reduce (?:the )?budget)\b/.test(text)){
    const previous=Number(profile.budget_usd);
    if(Number.isFinite(previous)) {
      const target=Math.max(400,Math.floor(previous*0.9/50)*50);
      add("delta-budget","Lower parts budget","budget_usd",target,
        "Propose a lower planning target; real component and assembly costs remain unknown.");
    }
  }
  if(/\b(?:lighter|lower (?:the )?weight|less heavy|easier to carry)\b/.test(text)){
    const previous=Number(profile.max_board_weight_lb);
    if(Number.isFinite(previous))
      add("delta-weight","Lighter board target","max_board_weight_lb",
        Math.max(15,previous-5),
        "Tighten maximum acceptable board mass; does not assert any candidate meets it.");
  }
  if(/\b(?:less maintenance|low maintenance|lower maintenance|easier to maintain)\b/.test(text))
    add("delta-maintenance","Low maintenance preference","maintenance_tolerance",
      "low","Prefer simpler servicing; not a maintenance or reliability guarantee.");
  if(/\b(?:more snowboard[-\s]?like|more carving|carve more|stronger carve)\b/.test(text)){
    const previous=Number(profile.snowboard_feel);
    if(Number.isFinite(previous))
      add("delta-carve","Increase carve preference","snowboard_feel",
        Math.min(100,Math.ceil((previous+10)/5)*5),
        "Increase an existing soft preference; does not imply measured turning dynamics.");
  }
  return out;
}

export function proposeRideConversationTurn(state,raw,questionnaire) {
  requireState(state);
  if(state.pending)throw new Error("Accept or reject the previous review first");
  const text=String(raw || "").trim();
  if(text.length>2400)throw new Error("Ride turn exceeds 2400 characters");
  const base=parseRideBrief(text,questionnaire);
  const proposals=[...base.proposals],taken=new Set(proposals.flatMap(p=>Object.keys(p.patch)));
  const warnings=[...base.warnings];
  for(const suggestion of relativeReview(text.toLowerCase(),state.profile,questionnaire)){
    const colliding=Object.keys(suggestion.patch).some(key=>taken.has(key));
    if(colliding){
      warnings.push("Overlapping direct and relative instruction for "+Object.keys(suggestion.patch).join(", ")+
        "; only the direct wording was proposed.");
      continue;
    }
    proposals.push(suggestion);
    Object.keys(suggestion.patch).forEach(key=>taken.add(key));
  }
  const review={
    schema_version:1,scope:REVIEW_SCOPE,turn_number:state.turns.length+1,
    based_on_revision:state.revision,raw_text:text,
    proposals,warnings,questions:base.questions,
    next_question:base.questions[0] || null,authority:{...AUTHORITY}
  };
  const next=clone(state);
  next.pending=review;
  return next;
}

export function acceptRideConversationTurn(state,acceptedIds,questionnaire) {
  requireState(state);
  if(!state.pending || state.pending.based_on_revision!==state.revision)
    throw new Error("Missing or stale review");
  if(!Array.isArray(acceptedIds) || !acceptedIds.length)
    throw new Error("Choose at least one proposed change or reject the review");
  const updated=applyRideBriefReview(state.profile,state.pending,acceptedIds,questionnaire);
  const next=clone(state),before=clone(next.profile),beforeProvenance=clone(next.provenance);
  next.history.push({profile:before,provenance:beforeProvenance,revision:next.revision});
  next.revision+=1;
  next.profile=updated;
  const selected=next.pending.proposals.filter(p=>acceptedIds.includes(p.id));
  for(const proposal of selected){
    for(const key of Object.keys(proposal.patch)){
      if(!Object.is(before[key],updated[key]))
        next.provenance[key]={
          source:"USER_ACCEPTED",certainty:proposal.certainty,
          proposal_id:proposal.id,turn_number:next.pending.turn_number,
          revision:next.revision
        };
    }
  }
  next.turns.push({
    action:"ACCEPT",revision:next.revision,
    raw_text:next.pending.raw_text,
    accepted_ids:[...acceptedIds],
    rejected_ids:next.pending.proposals.filter(p=>!acceptedIds.includes(p.id)).map(p=>p.id),
    changed_fields:Object.keys(updated).filter(key=>!Object.is(before[key],updated[key])),
    warnings:next.pending.warnings,question:next.pending.next_question
  });
  next.pending=null;
  return next;
}

export function rejectRideConversationTurn(state) {
  requireState(state);
  if(!state.pending)throw new Error("No pending review");
  const next=clone(state);
  next.turns.push({
    action:"REJECT",revision:next.revision,raw_text:next.pending.raw_text,
    rejected_ids:next.pending.proposals.map(p=>p.id)
  });
  next.pending=null;
  return next;
}

export function undoRideConversationTurn(state) {
  requireState(state);
  if(state.pending)throw new Error("Reject the pending review before undo");
  if(!state.history.length)throw new Error("No accepted change to undo");
  const next=clone(state),previous=next.history.pop();
  next.profile=previous.profile;
  next.provenance=previous.provenance;
  next.revision+=1;
  next.turns.push({action:"UNDO",revision:next.revision,
    restored_from_revision:previous.revision});
  return next;
}

export function recordManualRideField(state,key,value,questionnaire) {
  requireState(state);
  if(state.pending)throw new Error("Resolve pending review before manual edits");
  if(!fieldsFor(questionnaire).has(key))throw new Error("Unknown manual field "+key);
  const review={schema_version:1,scope:REVIEW_SCOPE,
    proposals:[{id:"manual",patch:{[key]:value}}]};
  const updated=applyRideBriefReview(state.profile,review,["manual"],questionnaire);
  const next=clone(state);
  if(Object.is(next.profile[key],updated[key]))return next;
  next.history.push({profile:clone(next.profile),
    provenance:clone(next.provenance),revision:next.revision});
  next.revision+=1;
  next.profile=updated;
  next.provenance[key]={source:"MANUAL",revision:next.revision};
  next.turns.push({action:"MANUAL",revision:next.revision,changed_fields:[key]});
  return next;
}

export function exportRideConversation(state) {
  requireState(state);
  return clone(state);
}
