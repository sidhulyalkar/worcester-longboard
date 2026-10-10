// A deterministic draft interpreter. No changes are applied without user review.
const AUTHORITY = Object.freeze({
  procurement_authorized:false, fabrication_authorized:false,
  charging_authorized:false, powered_operation_authorized:false,
  generic_builder_may_promote_x1_authority:false
});
const TERRAIN = ["terrain_pavement","terrain_packed_dirt","terrain_loose_gravel",
  "terrain_roots_rocks","terrain_grass_brush"];
const FAMILIES = {
  trails:[10,45,30,10,5], rough:[5,20,30,40,5],
  mixed:[40,30,20,10,0], pavement:[80,10,5,5,0]
};
const fieldsFor = questionnaire => new Map(
  (questionnaire?.sections || []).flatMap(s=>s.fields || []).map(f=>[f.id,f])
);

export function parseRideBrief(raw,questionnaire) {
  const text = String(raw || "").toLowerCase().replace(/,/g,"").slice(0,2400);
  const fields=fieldsFor(questionnaire), proposals=[],warnings=[],questions=[];
  const used = new Set();
  function propose(id,label,patch,evidence,certainty,explanation) {
    for(const [key,value] of Object.entries(patch)) {
      const field=fields.get(key);
      if(!field || used.has(key)) {warnings.push("Duplicate or unsupported field: "+key);return;}
      if(typeof value==="number" && (!Number.isFinite(value) ||
        value<(field.min ?? -Infinity) || value>(field.max ?? Infinity))) {
        warnings.push(label+" is outside the supported questionnaire range for "+key+
          " ("+field.min+"–"+field.max+").");return;
      }
      if(field.type==="select" && !(field.options || []).some(o=>o[0]===value)){
        warnings.push("Unsupported option for "+key);return;
      }
    }
    Object.keys(patch).forEach(k=>used.add(k));
    proposals.push({id,label,patch,evidence,certainty,explanation});
  }
  if(!text.trim()) {
    return {schema_version:1,scope:"non_authoritative_ride_brief_review",proposals,
      warnings:["Describe your ride to start."],questions,authority:{...AUTHORITY}};
  }

  const feet=text.match(/\b([4-6])\s*(?:ft|feet|')\s*(\d{1,2})?\s*(?:inches|inch|in|")?/);
  const inches=text.match(/\b(?:height(?:\s+(?:of|is))?|i(?:'m| am))\s*(\d{2})\s*(?:inches|inch|in)\b/);
  if(feet) propose("height","Rider height",
    {height_in:Number(feet[1])*12+Number(feet[2]||0)},feet[0],"EXPLICIT",
    "Feet and inches converted to the questionnaire's inch units.");
  else if(inches)propose("height","Rider height",{height_in:Number(inches[1])},
    inches[0],"EXPLICIT","Height in inches.");

  const weight=text.match(/\b(?:weigh(?:ing)?\s*(?:about|around)?\s*|(?:i'm|i am)\s*|^)(\d{2,3})\s*(?:lbs?|pounds?)\b/);
  if(weight)propose("weight","Rider body weight",{weight_lb:Number(weight[1])},
    weight[0],"EXPLICIT","Carried load remains a separate field.");

  const money=text.match(/(?:\$|usd\s*)\s*(\d+(?:\.\d+)?)/) ||
    text.match(/\b(?:budget|spend|cost(?:ing)?)\s*(?:of|is|around|about|under|up to|at most)?\s*(\d{3,5})\s*(?:usd|dollars?)?\b/);
  if(money) propose("budget","Target parts budget",{budget_usd:Number(money[1])},
    money[0],"EXPLICIT","Planning target, not a complete or confirmed checkout price.");

  const range=text.match(/\b(\d+(?:\.\d+)?)\s*(?:miles?|mi)\s*(?:of\s*)?(?:range|on\s+a\s*charge)\b/) ||
    text.match(/\b(?:range|longest\s+ride|up\s+to)\s*(?:of|around|about|is)?\s*(\d+(?:\.\d+)?)\s*(?:miles?|mi)\b/);
  const typical=text.match(/\b(?:typical(?:ly)?|usually|daily|average)\s*(?:ride|rides|go|do)?\s*(?:around|about|of)?\s*(\d+(?:\.\d+)?)\s*(?:miles?|mi)\b/);
  if(range)propose("range","Longest desired ride",{longest_miles:Number(range[1])},
    range[0],"EXPLICIT","Distance target, not a guaranteed range.");
  if(typical)propose("typical","Typical ride",{typical_miles:Number(typical[1])},
    typical[0],"EXPLICIT","Daily or typical distance, not a range guarantee.");

  const no=/\b(?:non[-\s]?electric|unpowered|manual\s+(?:board|mountainboard)|no\s+(?:motor|electric|power)|without\s+(?:motor|electric))\b/.test(text);
  const yes=/\b(?:electric\s+(?:skateboard|mountainboard|board)|motorized|powered\s+(?:board|skateboard)|want\s+(?:an?\s+)?electric)\b/.test(text);
  if(no && yes) warnings.push("Both electric and unpowered preferences appear. Set propulsion manually.");
  else if(no || yes)propose("propulsion","Propulsion intent",
    {electric_propulsion:yes?"yes":"no"},yes?"Electric board":"Unpowered board","EXPLICIT",
    "Mission intent only; electrical and brake qualification remain separate.");

  if(/\b(?:snowboard(?:ing)?|snowboard[-\s]?feel|carv(?:e|ing|er))\b/.test(text))
    propose("carving","Carving preference",{snowboard_feel:90,priority_carve:90},
      "Snowboard or carving reference","INFERRED",
      "Suggested preference scores; no assumptions about riding experience.");

  const paved=/\b(?:pavement|paved|city\s+streets?|commut(?:e|ing))\b/.test(text);
  const rough=/\b(?:technical|rocky|roots?|rock\s+gardens?)\b/.test(text);
  const trail=/\b(?:dirt|gravel|forest|trail|off[-\s]?road|brush)\b/.test(text);
  let terrain=null,terrainName="";
  if(paved && trail){terrain=FAMILIES.mixed;terrainName="mixed pavement and trails";}
  else if(rough && trail){terrain=FAMILIES.rough;terrainName="technical trails";}
  else if(trail){terrain=FAMILIES.trails;terrainName="dirt and gravel trails";}
  else if(paved){terrain=FAMILIES.pavement;terrainName="paved routes";}
  if(terrain)propose("terrain","Suggested terrain percentages",
    Object.fromEntries(TERRAIN.map((key,i)=>[key,terrain[i]])),
    terrainName,"INFERRED","A proposed 100% split, not observed route data.");

  if(/\b(?:long\s+descents?|sustained\s+downhill)\b/.test(text))
    propose("hills","Hill profile",{hill_profile:"long_descents"},
      "Long descents","EXPLICIT","Terrain classification, not brake qualification.");
  else if(/\b(?:steep\s+hills?|steep\s+grades?)\b/.test(text))
    propose("hills","Hill profile",{hill_profile:"steep"},
      "Steep hills","EXPLICIT","Terrain classification, not brake qualification.");

  if(/\b(?:walking\s+(?:my|the|a)\s+dog|with\s+(?:my|the|a)\s+dog|dog\s+walks?)\b/.test(text))
    propose("dog","Stop-and-start rides",{stop_start:true},
      "Dog-accompanied riding","INFERRED",
      "Does not assume a safe dog handling method or speed.");
  if(/\b(?:never\s+(?:skated|ridden\s+a\s+(?:skateboard|longboard))|new\s+to\s+(?:skating|skateboarding|longboarding))\b/.test(text))
    propose("experience","Skating experience",{board_experience:"none"},
      "New rider wording","EXPLICIT","Only explicit absence of experience is used.");

  if(!proposals.length)questions.push("Add weight, budget, desired range or terrain.");
  if(!range&&!typical&&/\b\d+(?:\.\d+)?\s*(?:miles?|mi)\b/.test(text))
    questions.push("Is the mentioned distance a typical ride or your longest desired ride?");
  if(!no&&!yes)questions.push("Do you want electric, manual, or future-convertible propulsion?");
  if(!weight)questions.push("What body weight and carried load should the fit study use?");
  return {schema_version:1,scope:"non_authoritative_ride_brief_review",
    proposals,warnings,questions,authority:{...AUTHORITY}};
}

export function applyRideBriefReview(profile,review,acceptedIds,questionnaire){
  if(review?.scope!=="non_authoritative_ride_brief_review" ||
    review.schema_version!==1 || !Array.isArray(acceptedIds))
    throw new Error("Invalid ride-brief review");
  const fields=fieldsFor(questionnaire),next={...profile},seen=new Set();
  for(const proposal of review.proposals || []){
    if(!acceptedIds.includes(proposal.id))continue;
    if(seen.has(proposal.id))throw new Error("Duplicate proposal");
    seen.add(proposal.id);
    for(const [key,value] of Object.entries(proposal.patch || {})){
      const field=fields.get(key);
      if(!field)throw new Error("Unknown field "+key);
      if(typeof value==="number" && (!Number.isFinite(value) ||
        value<(field.min ?? -Infinity) || value>(field.max ?? Infinity)))
        throw new Error("Out-of-range value "+key);
      if(field.type==="select" && !(field.options || []).some(o=>o[0]===value))
        throw new Error("Invalid selection "+key);
      next[key]=value;
    }
  }
  if(TERRAIN.some(key=>next[key]!==profile[key]) &&
    TERRAIN.reduce((total,key)=>total+Number(next[key]||0),0)!==100)
    throw new Error("Terrain percentages must total 100");
  return next;
}
