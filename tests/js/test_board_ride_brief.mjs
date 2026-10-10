import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import {fileURLToPath} from "node:url";
import {parseRideBrief,applyRideBriefReview} from "../../builder/ride_brief.mjs";

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const questionnaire=JSON.parse(fs.readFileSync(path.join(root,"configurator/questionnaire.v1.json"),"utf8"));
const defaults=Object.fromEntries(questionnaire.sections.flatMap(s=>s.fields.map(f=>[f.id,f.default])));
const get=(report,id)=>report.proposals.find(p=>p.id===id);
const assertLocked=report=>assert.ok(Object.values(report.authority).every(x=>x===false));

test("magic-moment description maps explicit values and proposes reviewable preferences",()=>{
  const report=parseRideBrief("I'm 175 lb, snowboard a lot, live near dirt trails, want around 20 miles of range, and I'd like to spend around $1,200.",questionnaire);
  assert.equal(get(report,"weight").patch.weight_lb,175);
  assert.equal(get(report,"budget").patch.budget_usd,1200);
  assert.equal(get(report,"range").patch.longest_miles,20);
  assert.equal(get(report,"carving").certainty,"INFERRED");
  assert.equal(get(report,"terrain").certainty,"INFERRED");
  assert.equal(Object.values(get(report,"terrain").patch).reduce((x,y)=>x+y,0),100);
  assert.ok(report.questions.some(q=>q.includes("electric")));
  assertLocked(report);
});

test("only user-selected groups change a copy; original input is unchanged",()=>{
  const old={...defaults};
  const report=parseRideBrief("I'm 175lbs, on dirt and gravel, with $1000 to spend and love carving",questionnaire);
  const next=applyRideBriefReview(old,report,["weight","budget"],questionnaire);
  assert.equal(next.weight_lb,175);
  assert.equal(next.budget_usd,1000);
  assert.equal(next.terrain_pavement,defaults.terrain_pavement);
  assert.equal(next.snowboard_feel,defaults.snowboard_feel);
  assert.deepEqual(old,defaults);
  assertLocked(report);
});

test("explicit feet and inches, unpowered intent, rough terrain and dog stops",()=>{
  const report=parseRideBrief("I'm 5'2, weigh 110 lb, want a manual board for rocky dirt trails and walking my dog.",questionnaire);
  assert.equal(get(report,"height").patch.height_in,62);
  assert.equal(get(report,"weight").patch.weight_lb,110);
  assert.equal(get(report,"propulsion").patch.electric_propulsion,"no");
  assert.equal(get(report,"dog").patch.stop_start,true);
  assert.equal(get(report,"terrain").patch.terrain_roots_rocks,40);
  const next=applyRideBriefReview(defaults,report,report.proposals.map(p=>p.id),questionnaire);
  assert.equal(next.terrain_pavement+next.terrain_packed_dirt+next.terrain_loose_gravel+next.terrain_roots_rocks+next.terrain_grass_brush,100);
});

test("ambiguous mileage is a question, not a fabricated ride target",()=>{
  const report=parseRideBrief("Maybe 16 miles, sometime around the park",questionnaire);
  assert.equal(get(report,"range"),undefined);
  assert.equal(get(report,"typical"),undefined);
  assert.ok(report.questions.some(q=>q.includes("typical ride")));
});

test("unsupported budgets are warnings and cannot be applied",()=>{
  const report=parseRideBrief("I weigh 170 lb and have a $9000 parts budget",questionnaire);
  assert.equal(get(report,"budget"),undefined);
  assert.ok(report.warnings.some(w=>w.includes("budget_usd")));
  assert.equal(applyRideBriefReview(defaults,report,["budget","weight"],questionnaire).weight_lb,170);
  assertLocked(report);
});

test("conflicting electric and manual intent is never guessed",()=>{
  const report=parseRideBrief("I want an electric board but also no motor",questionnaire);
  assert.equal(get(report,"propulsion"),undefined);
  assert.ok(report.warnings.some(w=>w.includes("Both electric")));
});

test("malformed and unauthorized review payloads fail closed",()=>{
  const review=parseRideBrief("want $1200 and 20 miles of range",questionnaire);
  assert.throws(()=>applyRideBriefReview(defaults,{...review,scope:"approved_build"},["budget"],questionnaire));
  assert.throws(()=>applyRideBriefReview(defaults,{...review,proposals:[{id:"bad",patch:{powered_operation_authorized:true}}]},["bad"],questionnaire));
  assert.throws(()=>applyRideBriefReview(defaults,{...review,proposals:[{id:"bad",patch:{weight_lb:10000}}]},["bad"],questionnaire));
});

test("empty text is safe, unmodified and explicitly unactionable",()=>{
  const report=parseRideBrief("",questionnaire);
  assert.equal(report.proposals.length,0);
  assert.ok(report.warnings.length);
  assert.deepEqual(applyRideBriefReview(defaults,report,[],questionnaire),defaults);
  assertLocked(report);
});
