import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import {fileURLToPath} from "node:url";
import {
  createRideConversation,proposeRideConversationTurn,
  acceptRideConversationTurn,rejectRideConversationTurn,
  undoRideConversationTurn,recordManualRideField,exportRideConversation
} from "../../builder/conversation_state.mjs";

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const questionnaire=JSON.parse(fs.readFileSync(path.join(root,"configurator/questionnaire.v1.json"),"utf8"));
const defaults=Object.fromEntries(questionnaire.sections.flatMap(s=>s.fields.map(f=>[f.id,f.default])));
const init=()=>createRideConversation(defaults,questionnaire);
const locked=state=>assert.ok(Object.values(state.authority).every(v=>v===false));

test("multi-turn revisions retain known facts and never mutate profile before acceptance",()=>{
  const initial=init();
  const review=proposeRideConversationTurn(initial,"I weigh 175 lb and want a $1200 board",questionnaire);
  assert.equal(review.profile.weight_lb,defaults.weight_lb);
  assert.equal(review.pending.proposals.find(p=>p.id==="weight").patch.weight_lb,175);
  const first=acceptRideConversationTurn(review,["weight","budget"],questionnaire);
  assert.equal(first.profile.weight_lb,175);
  assert.equal(first.profile.budget_usd,1200);
  assert.equal(initial.profile.weight_lb,defaults.weight_lb);
  const next=proposeRideConversationTurn(first,"make it less expensive and lower maintenance",questionnaire);
  assert.ok(next.pending.proposals.some(p=>p.id==="delta-budget"));
  assert.ok(next.pending.proposals.some(p=>p.id==="delta-maintenance"));
  assert.equal(next.profile.budget_usd,1200);
  const accepted=acceptRideConversationTurn(next,["delta-budget","delta-maintenance"],questionnaire);
  assert.ok(accepted.profile.budget_usd<1200);
  assert.equal(accepted.profile.maintenance_tolerance,"low");
  assert.equal(accepted.profile.weight_lb,175);
  assert.equal(accepted.provenance.weight_lb.source,"USER_ACCEPTED");
  assert.equal(accepted.provenance.budget_usd.revision,2);
  assert.equal(accepted.turns.length,2);
  locked(accepted);
});

test("undo restores exact previous values and provenance without reversing unrelated state",()=>{
  let state=init();
  state=acceptRideConversationTurn(
    proposeRideConversationTurn(state,"I weigh 180 lb",questionnaire),["weight"],questionnaire);
  const before=exportRideConversation(state);
  state=acceptRideConversationTurn(
    proposeRideConversationTurn(state,"make it lighter",questionnaire),["delta-weight"],questionnaire);
  const undone=undoRideConversationTurn(state);
  assert.deepEqual(undone.profile,before.profile);
  assert.deepEqual(undone.provenance,before.provenance);
  assert.equal(undone.revision,3);
  assert.equal(undone.turns.at(-1).action,"UNDO");
  locked(undone);
});

test("ambiguous mileage is never set; only one next question is exposed",()=>{
  const state=proposeRideConversationTurn(init(),"Somewhere around 16 miles, unsure about power",questionnaire);
  assert.equal(state.pending.proposals.find(p=>p.id==="range"),undefined);
  assert.ok(state.pending.next_question.includes("typical ride"));
  assert.equal(state.pending.questions.length>=1,true);
  const rejected=rejectRideConversationTurn(state);
  assert.deepEqual(rejected.profile,defaults);
  assert.equal(rejected.turns[0].action,"REJECT");
});

test("stale, unknown or duplicate acceptance and hostile field access fail closed",()=>{
  const pending=proposeRideConversationTurn(init(),"I weigh 175 lb",questionnaire);
  assert.throws(()=>proposeRideConversationTurn(pending,"make it cheaper",questionnaire),/previous review/);
  assert.throws(()=>acceptRideConversationTurn(pending,["bogus"],questionnaire),/unknown or duplicate/);
  assert.throws(()=>acceptRideConversationTurn(pending,["weight","weight"],questionnaire),/unknown or duplicate/);
  assert.throws(()=>recordManualRideField(init(),"powered_operation_authorized",true,questionnaire),/Unknown manual/);
  assert.throws(()=>createRideConversation({...defaults,powered_operation_authorized:true},questionnaire),/Unknown initial/);
  locked(pending);
});

test("manual values are tracked, scoped, reviewable and never silently lost",()=>{
  let state=init();
  state=recordManualRideField(state,"weight_lb",155,questionnaire);
  const review=proposeRideConversationTurn(state,"make it lighter",questionnaire);
  const accepted=acceptRideConversationTurn(review,["delta-weight"],questionnaire);
  assert.equal(accepted.profile.weight_lb,155);
  assert.equal(accepted.provenance.weight_lb.source,"MANUAL");
  assert.ok(accepted.turns.some(t=>t.action==="MANUAL"));
  assert.deepEqual(exportRideConversation(accepted),accepted);
});

test("contradictory budget and distance edits fail without mutating accepted state",()=>{
  const original=init();
  const tooHigh=proposeRideConversationTurn(original,"I want a $3000 board",questionnaire);
  assert.throws(()=>acceptRideConversationTurn(tooHigh,["budget"],questionnaire),/maximum budget/);
  assert.deepEqual(tooHigh.profile,defaults);
  const tooShort=proposeRideConversationTurn(original,"want 5 miles of range",questionnaire);
  assert.throws(()=>acceptRideConversationTurn(tooShort,["range"],questionnaire),/Typical ride exceeds/);
});

test("relative request cannot override explicit same-field request",()=>{
  const state=proposeRideConversationTurn(init(),"I want a $1200 board but make it cheaper",questionnaire);
  assert.equal(state.pending.proposals.filter(p=>Object.keys(p.patch).includes("budget_usd")).length,1);
  assert.ok(state.pending.warnings.some(w=>w.includes("Overlapping")));
});

test("too-long inputs and empty undo are rejected",()=>{
  assert.throws(()=>proposeRideConversationTurn(init(),"x".repeat(2401),questionnaire),/exceeds/);
  assert.throws(()=>undoRideConversationTurn(init()),/No accepted/);
});


test("relative carving edits never lower an already high preference",()=>{
  let base={...defaults,snowboard_feel:95};
  const initial=createRideConversation(base,questionnaire);
  const turn=proposeRideConversationTurn(initial,"make it more snowboard-like",questionnaire);
  assert.equal(turn.pending.proposals.find(p=>p.id==="carving"),undefined);
  assert.equal(turn.pending.proposals.find(p=>p.id==="delta-carve").patch.snowboard_feel,100);
  const accepted=acceptRideConversationTurn(turn,["delta-carve"],questionnaire);
  assert.equal(accepted.profile.snowboard_feel,100);
});

test("manual patch and baseline validation reject type confusion",()=>{
  assert.throws(()=>recordManualRideField(init(),"weight_lb","very light",questionnaire),/Invalid numeric/);
  assert.throws(()=>recordManualRideField(init(),"stop_start","true",questionnaire),/Invalid boolean/);
  assert.throws(()=>recordManualRideField(init(),"maintenance_tolerance","automatic",questionnaire),/Invalid selection/);
  assert.throws(()=>createRideConversation({...defaults,weight_lb:"175"},questionnaire),/Invalid numeric/);
  assert.throws(()=>createRideConversation({...defaults,fit_notes:5},questionnaire),/Invalid text/);
});
