import {
  formatPrice,
  questionnaireDefaults,
} from "./engine.mjs";
import { generateBoardDesignSpace } from "./platform_engine.mjs";
import {validateExampleRides,profileForExample} from "./example_rides.mjs";
import {defaultComparisonIds,compareCandidates} from "./comparison.mjs";
import {assemblyGuide} from "./assembly_guide.mjs";
import {buildBuildPassport,proposePassportRevisionChange} from "./build_passport.mjs";
import {
  createRideConversation,restoreRideConversation,reconcileManualRideProfile,
  proposeRideConversationTurn,acceptRideConversationTurn,rejectRideConversationTurn,
  undoRideConversationTurn,exportRideConversation
} from "./conversation_state.mjs";
import { buildEvidenceExplorer } from "./evidence_explorer.mjs";
import {
  evaluateSwap,
  seedSwapSelection,
} from "./swap_engine.mjs";
import {
  visualStateFromCandidate,
  visualStateFromSwap,
} from "./visual_state.mjs";
import {
  downloadBoardPreviewSvg,
  renderBoardPreviewSvg,
} from "./preview_renderer.mjs";

const STORAGE_KEY = "worcester-board-builder-profile-v1";
const SESSION_KEY = "worcester-board-builder-conversation-v1";

const state = {
  bundle: null,
  profile: {},
  result: null,
  selectedId: null,
  advanced: false,
  renderQueued: false,
  swapBaselineId: null,
  swapSelection: null,
  swapResult: null,
  galleryView: "hero",
  vendorFilter: "all",
  originFilter: "all",
  activeExampleId: null,
  rideBriefReview: null,
  conversation: null,
  conversationStatus: "",
  sessionOutOfSync: false,
  originalConversationBeforeExamples: null,
  originalProfileBeforeExamples: null,
  passportCandidateId: null,
  passportRevisionReceipt: null,
  comparisonIds: [],
  comparisonInitialized: false,
};

const $ = selector => document.querySelector(selector);

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function fetchJson(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error("Failed to load " + path);
  return response.json();
}

async function loadBundle() {
  const [questionnaire, rules, catalog, architectures, compatibility, swapSlots, geometry, composer, catalogHealth, exampleRides] = await Promise.all([
    fetchJson("../configurator/questionnaire.v1.json"),
    fetchJson("../configurator/rules.v1.json"),
    fetchJson("../catalog/board_components.v1.json"),
    fetchJson("../configurator/architectures.v1.json"),
    fetchJson("../configurator/compatibility_rules.v1.json"),
    fetchJson("../configurator/swap_slots.v1.json"),
    fetchJson("../catalog/board_geometry.v1.json"),
    fetchJson("../configurator/composer.v1.json"),
    fetchJson("../catalog/catalog_health.v1.json"),
    fetchJson("../configurator/example_rides.v1.json"),
  ]);
  return { questionnaire, rules, catalog, architectures, compatibility, swapSlots, geometry, composer, catalogHealth, exampleRides };
}

function restoreProfile(questionnaire) {
  const defaults = questionnaireDefaults(questionnaire);
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaults;
    const stored = JSON.parse(raw);
    if (!stored || typeof stored !== "object" || Array.isArray(stored))
      throw new Error("Invalid saved profile object");
    const result = {...defaults}, rejected = [];
    for (const section of questionnaire.sections) {
      for (const field of section.fields) {
        if (!Object.prototype.hasOwnProperty.call(stored,field.id)) continue;
        const value = stored[field.id];
        const valid = value===null && !field.required ||
          (["number","range"].includes(field.type) && typeof value==="number" &&
            Number.isFinite(value) && value >= (field.min ?? -Infinity) &&
            value <= (field.max ?? Infinity)) ||
          (field.type==="select" && (field.options || []).some(row=>row[0]===value)) ||
          (field.type==="boolean" && typeof value==="boolean") ||
          (field.type==="text" && typeof value==="string");
        if (valid) result[field.id]=value;
        else rejected.push(field.label);
      }
    }
    if (rejected.length)
      state.conversationStatus = "Some invalid saved values were reset to defaults: " +
        rejected.join(", ") + ". Review them before proceeding.";
    return result;
  } catch {
    state.conversationStatus =
      "The saved questionnaire could not be read. Default planning values were loaded.";
    return defaults;
  }
}

function saveProfile() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.profile));
}

function fieldValue(field) {
  const value = state.profile[field.id];
  return value === undefined ? field.default : value;
}

function makeInput(field) {
  let input;
  const value = fieldValue(field);

  if (field.type === "select") {
    input = document.createElement("select");
    for (const [optionValue, optionLabel] of field.options || []) {
      const option = document.createElement("option");
      option.value = optionValue;
      option.textContent = optionLabel;
      input.appendChild(option);
    }
    input.value = value ?? "";
  } else if (field.type === "boolean") {
    input = document.createElement("input");
    input.type = "checkbox";
    input.checked = Boolean(value);
  } else if (field.type === "range") {
    input = document.createElement("input");
    input.type = "range";
    input.min = field.min;
    input.max = field.max;
    input.step = field.step || 1;
    input.value = value ?? field.default ?? field.min;
  } else if (field.type === "text") {
    input = document.createElement("textarea");
    input.value = value ?? "";
  } else {
    input = document.createElement("input");
    input.type = "number";
    input.min = field.min;
    input.max = field.max;
    input.step = field.step || 1;
    input.value = value ?? "";
    if (!field.required) input.placeholder = "Optional";
  }

  input.id = "field-" + field.id;
  input.dataset.fieldId = field.id;
  input.dataset.fieldType = field.type;
  input.setAttribute("aria-label", field.label);
  return input;
}

function typedValue(input) {
  if (input.dataset.fieldType === "boolean") return input.checked;
  if (input.dataset.fieldType === "number" || input.dataset.fieldType === "range") {
    return input.value === "" ? null : Number(input.value);
  }
  return input.value;
}


function saveConversation() {
  if (!state.conversation || state.sessionOutOfSync) return;
  localStorage.setItem(SESSION_KEY, JSON.stringify(exportRideConversation(state.conversation)));
}

function renderRideConversation() {
  const host = $("#ride-conversation-history");
  if (!host || !state.conversation) return;
  const labels = new Map(state.bundle.questionnaire.sections.flatMap(section =>
    section.fields.map(field => [field.id, field.label])));
  const latest = state.conversation.turns.slice(-6).reverse();
  host.innerHTML = latest.length ? latest.map(turn => {
    const changes = (turn.changed_fields || []).map(key=>labels.get(key) || key).join(", ");
    const title = turn.action === "ACCEPT" ? "Applied reviewed changes" :
      turn.action === "REJECT" ? "Discarded suggestions" :
      turn.action === "UNDO" ? "Restored earlier specifications" :
      "Edited questionnaire";
    return '<li class="conversation-turn"><strong>' + escapeHtml(title) +
      '</strong><span>' + escapeHtml(changes || turn.raw_text || "") +
      '</span><small>Revision ' + escapeHtml(turn.revision) + '</small></li>';
  }).join("") : '<li class="conversation-empty">No changes yet. Describe your ride or edit a specification.</li>';
  $("#ride-conversation-undo").disabled = !!state.conversation.pending ||
    !state.conversation.history.length || state.sessionOutOfSync;
  $("#ride-conversation-status").textContent = state.conversationStatus ||
    (state.sessionOutOfSync
      ? "Finish correcting questionnaire values before reviewing a new design change."
      : "Review proposed edits before they change your design.");
}

function clearPendingRideReview(reason = "") {
  if (state.conversation?.pending)
    state.conversation = rejectRideConversationTurn(state.conversation);
  state.rideBriefReview = null;
  state.conversationStatus = reason;
  renderRideBriefReview();
  saveConversation();
  renderRideConversation();
}

function reconcileQuestionnaire() {
  if (!state.conversation) return false;
  if (state.conversation.pending)
    clearPendingRideReview("Questionnaire edited. The earlier proposal was discarded.");
  try {
    state.conversation = reconcileManualRideProfile(
      state.conversation, state.profile, state.bundle.questionnaire);
    state.sessionOutOfSync = false;
    state.conversationStatus = "Manual specification changes recorded. You can undo them.";
    saveConversation();
    renderRideConversation();
    return true;
  } catch (error) {
    state.sessionOutOfSync = true;
    state.conversationStatus = "Finish correcting manual values before conversational review: " + error.message;
    renderRideConversation();
    return false;
  }
}

function onQuestionnaireInput() {
  state.sessionOutOfSync = true;
  if (state.conversation?.pending)
    clearPendingRideReview("Questionnaire edited; previous suggestions discarded.");
  else {
    state.conversationStatus = "Manual edit pending validation. Complete the field to continue.";
    renderRideConversation();
  }
}

function renderRideBriefReview() {
  const host = $("#ride-brief-review");
  const report = state.rideBriefReview;
  if (!report) { host.replaceChildren(); return; }
  const labels = new Map(state.bundle.questionnaire.sections.flatMap(s => s.fields.map(f => [f.id, f.label])));
  const describe = proposal => Object.entries(proposal.patch).map(([key,value]) =>
    escapeHtml(labels.get(key) || key) + ": " +
    '<span class="ride-brief-certainty">' + escapeHtml(String(state.profile[key] ?? "unspecified")) + '</span> → ' +
    "<strong>" + escapeHtml(String(value)) + "</strong>"
  ).join(" · ");
  const proposals = report.proposals.map(p =>
    '<label class="ride-brief-proposal">' +
    '<input type="checkbox" data-ride-group="' + escapeHtml(p.id) + '"' +
    (p.certainty === "EXPLICIT" ? " checked" : "") + '>' +
    '<span><strong>' + escapeHtml(p.label) + '</strong>' +
    '<small class="ride-brief-certainty">' + escapeHtml(p.certainty) +
    ' · ' + escapeHtml(p.evidence) + '</small>' +
    '<span class="ride-brief-values">' + describe(p) + '</span>' +
    '<small>' + escapeHtml(p.explanation) + '</small></span></label>'
  ).join("");
  const list = (rows,heading) => rows.length
    ? '<div class="ride-brief-followups"><strong>' + escapeHtml(heading) + '</strong><ul>' +
      rows.map(row => '<li>' + escapeHtml(row) + '</li>').join("") + '</ul></div>' : "";
  const question = report.next_question ? list([report.next_question],"Next useful question") : "";
  host.innerHTML = '<div class="ride-brief-review-head"><h3>Proposed profile changes (' +
    report.proposals.length + ')</h3><span>Explicit details preselected; inferred preferences off</span></div>' +
    proposals +
    list(report.warnings,"Needs attention") + question +
    '<div class="ride-brief-actions">' +
    '<button type="button" id="ride-brief-apply"' +
    (report.proposals.length ? '' : ' disabled') + '>Apply checked changes + regenerate</button>' +
    '<button type="button" id="ride-brief-discard">Discard suggestions</button></div>' +
    '<p class="privacy-note">No preview is a fabrication drawing, purchase release, battery instruction or ride permit.</p>';
  $("#ride-brief-discard").addEventListener("click", () =>
    clearPendingRideReview("Suggestions discarded. No specifications were changed."));
  const apply = $("#ride-brief-apply");
  if (apply) apply.addEventListener("click", () => {
    const ids = [...host.querySelectorAll("[data-ride-group]:checked")].map(el => el.dataset.rideGroup);
    if (!ids.length) {
      host.querySelector(".ride-brief-review-head span").textContent = "Select a suggestion first.";
      return;
    }
    try {
      if (state.sessionOutOfSync) throw new Error("Finish your manual questionnaire edits first.");
      state.conversation = acceptRideConversationTurn(
        state.conversation,ids,state.bundle.questionnaire);
      state.profile = {...state.conversation.profile};
      state.selectedId = null;
      state.comparisonIds = [];
      state.comparisonInitialized = false;
      state.activeExampleId = null;
      state.originalProfileBeforeExamples = null;
      state.originalConversationBeforeExamples = null;
      saveProfile();
      saveConversation();
      renderQuestionnaire();
      state.rideBriefReview = null;
      renderRideBriefReview();
      recompute();
      state.conversationStatus = "Applied " + ids.length +
        " reviewed group(s); the design space and BOM have regenerated.";
      renderRideConversation();
      $("#ride-brief-input").value = "";
    } catch(error) {
      host.querySelector(".ride-brief-review-head span").textContent = error.message;
    }
  });
}
function reviewRideBrief() {
  if (state.conversation?.pending) {
    state.conversationStatus = "Accept or discard the current review before proposing another change.";
    renderRideConversation();
    return;
  }
  if (!reconcileQuestionnaire()) return;
  try {
    state.conversation = proposeRideConversationTurn(
      state.conversation,$("#ride-brief-input").value,state.bundle.questionnaire);
    state.rideBriefReview = state.conversation.pending;
    state.conversationStatus = "Proposal awaiting review; existing specifications unchanged.";
    renderRideBriefReview();
    renderRideConversation();
  } catch(error) {
    state.conversationStatus = error.message;
    renderRideConversation();
  }
}

function undoLastConversationChange() {
  if (!reconcileQuestionnaire() || state.conversation.pending) return;
  try {
    state.conversation = undoRideConversationTurn(state.conversation);
    state.profile = {...state.conversation.profile};
    state.rideBriefReview = null;
    state.activeExampleId = null;
    state.originalProfileBeforeExamples = null;
    state.originalConversationBeforeExamples = null;
    state.selectedId = null;
    state.comparisonIds = [];
    state.comparisonInitialized = false;
    state.conversationStatus = "Restored previous specifications and regenerated candidate designs.";
    saveProfile(); saveConversation();
    renderQuestionnaire(); renderRideBriefReview(); renderRideConversation();
    recompute();
  } catch(error) {
    state.conversationStatus = error.message;
    renderRideConversation();
  }
}

function renderQuestionnaire() {
  const host = $("#questionnaire");
  host.innerHTML = "";

  for (const section of state.bundle.questionnaire.sections || []) {
    const sectionEl = document.createElement("section");
    sectionEl.className = "question-section";

    const header = document.createElement("header");
    const title = document.createElement("h3");
    title.textContent = section.label;
    const summary = document.createElement("p");
    summary.textContent = section.summary || "";
    header.append(title, summary);
    sectionEl.appendChild(header);

    const fields = document.createElement("div");
    fields.className = "fields";

    for (const field of section.fields || []) {
      const wrapper = document.createElement("div");
      wrapper.className = "field" + (!field.quick && !state.advanced ? " hidden-advanced" : "");
      if (field.type === "boolean") wrapper.classList.add("boolean-field");

      const head = document.createElement("div");
      head.className = "field-head";
      const label = document.createElement("label");
      label.htmlFor = "field-" + field.id;
      label.textContent = field.label;
      head.appendChild(label);

      let output = null;
      if (field.type === "range") {
        output = document.createElement("output");
        const suffix = field.unit ? " " + field.unit : "";
        output.textContent = String(fieldValue(field) ?? field.default ?? field.min) + suffix;
        head.appendChild(output);
      } else if (field.unit && field.type === "number") {
        const unit = document.createElement("span");
        unit.className = "unit";
        unit.textContent = field.unit;
        head.appendChild(unit);
      }

      const input = makeInput(field);
      input.addEventListener("input", () => {
        state.profile[field.id] = typedValue(input);
        if (output) {
          const suffix = field.unit ? " " + field.unit : "";
          output.textContent = input.value + suffix;
        }
        saveProfile();
        onQuestionnaireInput();
        scheduleRecompute();
      });
      input.addEventListener("change", () => {
        state.profile[field.id] = typedValue(input);
        saveProfile();
        reconcileQuestionnaire();
        scheduleRecompute();
      });

      wrapper.appendChild(head);
      wrapper.appendChild(input);

      if (field.type === "range" && (field.left_label || field.right_label)) {
        const labels = document.createElement("div");
        labels.className = "range-labels";
        const left = document.createElement("span");
        left.textContent = field.left_label || String(field.min);
        const right = document.createElement("span");
        right.textContent = field.right_label || String(field.max);
        labels.append(left, right);
        wrapper.appendChild(labels);
      }

      if (field.help) {
        const help = document.createElement("small");
        help.textContent = field.help;
        wrapper.appendChild(help);
      }
      fields.appendChild(wrapper);
    }

    sectionEl.appendChild(fields);
    host.appendChild(sectionEl);
  }
}

function wheelLabel(value) {
  return {
    eight_inch_pneumatic_reference: "8 in pneumatic reference",
    nine_inch_rollover_study: "9 in rollover study",
    pavement_efficiency_study: "Pavement efficiency study",
  }[value] || value;
}

function deckLabel(value) {
  return {
    compact: "Compact",
    balanced: "Balanced",
    long_stable: "Long / stable",
  }[value] || value;
}

function renderRequirements(requirements) {
  const cards = [
    ["Target mission range", requirements.target_range_mi + " mi", "Includes the planning ride-length margin."],
    ["Planning energy envelope", requirements.planning_installed_energy_wh + " Wh", "Comparative estimate only, not a battery selection."],
    ["Planning consumption", requirements.planning_energy_wh_per_mi + " Wh/mi", "Pre-telemetry model used only for trade studies."],
    ["Energy reserve", Math.round(requirements.energy_reserve_fraction * 100) + "%", "Model reserve for terrain / weather uncertainty."],
    ["Wheel strategy", wheelLabel(requirements.wheel_strategy), "Physical compatibility still controls."],
    ["Stance study", requirements.stance_study.min_mm + "–" + requirements.stance_study.max_mm + " mm", "Center " + requirements.stance_study.center_mm + " mm · " + requirements.stance_study.source],
    ["Brake requirement", requirements.independent_friction_brake_required ? "Independent friction brake" : "Not forced by mission", "Regenerative braking never substitutes for a required friction path."],
    ["Deck envelope", deckLabel(requirements.deck_envelope_preference), "Planning preference, not structural qualification."],
    ["Ingress priority", requirements.ingress_priority, "Driven by wet / contamination exposure."],
    ["Loaded rider mass", requirements.loaded_rider_mass_kg + " kg", "Body + stated typical carried load."],
  ];

  $("#requirements").innerHTML = cards.map(row =>
    '<div class="requirement-card"><span>' + escapeHtml(row[0]) + '</span><strong>' +
    escapeHtml(row[1]) + '</strong><small>' + escapeHtml(row[2]) + '</small></div>'
  ).join("");

  const notes = [
    ...(requirements.warnings || []).map(text => ({ text, kind: "warning" })),
    ...(requirements.assumptions || []).slice(0, 4).map(text => ({ text, kind: "" })),
  ];
  $("#requirement-notes").innerHTML = notes.map(note =>
    '<div class="note ' + note.kind + '">' + escapeHtml(note.text) + '</div>'
  ).join("");
}

function statusClass(readiness) {
  return {
    REFERENCE_COMPATIBLE: "reference",
    MEASURE_FIRST: "measure",
    BLOCKED: "blocked",
    INCOMPATIBLE: "incompatible",
  }[readiness] || "";
}

function readinessLabel(readiness) {
  return readiness.replaceAll("_", " ").toLowerCase();
}

function sourceHealth(componentId) {
  return (state.bundle?.catalogHealth?.component_health || [])
    .find(row => row.component_id === componentId) || null;
}

function sourceHealthLabel(row) {
  if (!row) return "health unavailable";
  return row.status.replaceAll("_", " ").toLowerCase();
}

function sourceEvidenceHtml(componentId) {
  const health = sourceHealth(componentId);
  if (!health) return '<small>source health unavailable</small>';
  const verified = health.verified_as_of
    ? " · verified " + health.verified_as_of
    : "";
  return '<small>evidence ' +
    escapeHtml(sourceHealthLabel(health)) +
    escapeHtml(verified) +
    ' · not stock confirmation</small>';
}

// Evidence is an inspection view, not an independent qualification verdict.
function evidencePanelHtml(report, allowExport = false) {
  const tasks = new Map(report.measurement_worklist.map(t => [t.id, t]));
  const open = report.interfaces.filter(f => ["UNKNOWN", "MEASURE_FIRST"].includes(f.state));
  const conflict = report.interfaces.filter(f => f.state === "INCOMPATIBLE");
  const reference = report.interfaces.filter(f => !["UNKNOWN", "MEASURE_FIRST", "INCOMPATIBLE"].includes(f.state));
  const safeLink = row => row.source_url && /^https?:\/\//i.test(row.source_url)
    ? '<a href="' + escapeHtml(row.source_url) + '" rel="noopener noreferrer" target="_blank">Source</a>'
    : "No vendor link";
  const source = row => '<span>' + escapeHtml(row.label) + ' · ' +
    escapeHtml(row.health_status.replaceAll("_", " ").toLowerCase()) +
    (row.verified_as_of ? ' · checked ' + escapeHtml(row.verified_as_of) : '') +
    ' · ' + safeLink(row) + '</span>';
  const findingHtml = f => {
    const task = tasks.get(f.id);
    return '<article class="evidence-row"><div class="evidence-row-top"><strong>' +
      escapeHtml(f.a_label) + ' ↔ ' + escapeHtml(f.b_label) + '</strong>' +
      '<span class="badge ' + statusClass(f.state === "UNKNOWN" ? "MEASURE_FIRST" : f.state) + '">' +
      escapeHtml(f.state.replaceAll("_", " ").toLowerCase()) + '</span></div>' +
      '<p>' + escapeHtml(f.reason) + '</p>' +
      '<small>' + escapeHtml(f.id) + ' · ' +
      escapeHtml(f.evidence_kind === "CONSERVATIVE_CATEGORY_FALLBACK"
        ? "No explicit pair rule; conservative fallback" : "Explicit catalog reference rule") +
      '</small>' +
      (task ? '<p class="evidence-task"><strong>Measure next:</strong> ' +
        escapeHtml(task.question) + '<small>' + escapeHtml(task.evidence_required) + '</small></p>' : '') +
      '<div class="evidence-sources">' + f.sources.map(source).join('') + '</div></article>';
  };
  const group = (label, rows, expanded) => '<details class="evidence-group"' +
    (expanded ? ' open' : '') + '><summary>' + escapeHtml(label) +
    ' <span>' + rows.length + '</span></summary><div class="evidence-rows">' +
    (rows.length ? rows.map(findingHtml).join('') :
      '<p>No recorded findings in this category. This is not a mechanical qualification.</p>') +
    '</div></details>';
  const list = (items, fn) => items.length
    ? '<ul>' + items.map(x => '<li>' + fn(x) + '</li>').join('') + '</ul>'
    : '<p>No entries recorded in this category.</p>';
  const s = report.summary;
  return '<header class="evidence-header"><div><h3>Compatibility evidence</h3>' +
    '<p>Interface-by-interface explanations and exact-revision measurement work.</p></div>' +
    (allowExport ? '<button type="button" id="export-evidence">Export worklist</button>' : '') +
    '</header><div class="evidence-metrics">' +
      '<span><strong>' + s.open_interfaces + '</strong> open interfaces</span>' +
      '<span><strong>' + s.incompatible_interfaces + '</strong> known conflicts</span>' +
      '<span><strong>' + s.source_refresh_or_integrity_issues + '</strong> source follow-ups</span>' +
      '<span><strong>' + s.unpriced_items + '</strong> unpriced items</span></div>' +
    '<p class="evidence-boundary">' +
      escapeHtml(s.physical_basis === "EXPANDED_COMPONENT_GRAPH"
        ? "Expanded physical interface graph, not assembly qualification."
        : "Curated reference BOM only: absent pair findings never establish complete compatibility.") +
      ' Fit score is a planning preference, never a safety rating.</p>' +
    (report.hard_blockers.length ? '<div class="evidence-blocker"><strong>Hard blockers</strong>' +
      list(report.hard_blockers, escapeHtml) + '</div>' : '') +
    group("Unresolved: exact measurements or revision evidence required", open, true) +
    (conflict.length ? group("Incompatible: do not substitute or fabricate", conflict, true) : '') +
    group("Reference-rule findings", reference, false) +
    '<details class="evidence-group"><summary>Source health, cost gaps and other uncertainties <span>' +
    (report.source_maintenance.length + report.other_uncertainties.length) +
    '</span></summary><div class="evidence-supplement">' +
    '<h4>Refresh / missing provenance</h4>' + list(report.source_maintenance, source) +
    '<h4>Additional planning uncertainties</h4>' + list(report.other_uncertainties, escapeHtml) +
    '<p>Unpriced IDs: ' + escapeHtml(report.unpriced_component_ids.join(", ") || "none") +
    '. USD values are known-price subtotals only; stock, tax and shipping are excluded.</p>' +
    '</div></details><p class="evidence-boundary">' +
    escapeHtml(report.qualification_note) + '</p>';
}

function swapEvidence(candidate, result) {
  return buildEvidenceExplorer({
    ...result, id: candidate.id + ":edited", origin: "SWAP_STUDY",
    composition: {physical_interface_ids: result.compatibility_interface_ids},
  }, state.bundle.catalog, state.bundle.catalogHealth);
}

function exportEvidenceWorklist() {
  const candidate = state.result?.candidates.find(x => x.id === state.selectedId);
  if (!candidate?.evidence) return;
  const e = candidate.evidence;
  downloadJson("worcester-worklist-" + candidate.id + ".json", {
    schema_version: 1, scope: e.scope, candidate_id: e.candidate_id,
    readiness: e.readiness, checkout_state: e.checkout_state,
    interfaces: e.interfaces, measurement_worklist: e.measurement_worklist,
    source_evidence: e.source_evidence, source_maintenance: e.source_maintenance,
    other_uncertainties: e.other_uncertainties, hard_blockers: e.hard_blockers,
    unpriced_component_ids: e.unpriced_component_ids,
    price_basis: e.price_basis, score_basis: e.score_basis,
    authority: e.authority, note: e.qualification_note,
  });
}

function partialCost(candidate) {
  const c = candidate.cost;
  const unpriced = (c.unpriced_component_ids || []).length;
  if (unpriced && c.known_min_usd === 0 && c.known_max_usd === 0) {
    return "USD subtotal incomplete";
  }
  if (c.known_min_usd === c.known_max_usd) return "USD " + c.known_min_usd.toFixed(0);
  return "USD " + c.known_min_usd.toFixed(0) + "–" + c.known_max_usd.toFixed(0);
}

function twinUrl(candidate) {
  const spec = candidate.personalized_spec || {};
  const visual = candidateVisualState(candidate);
  const params = new URLSearchParams({
    preset: candidate.visual_preset,
    candidate: candidate.id,
    deck: visual.deck.id,
    topology: visual.topology.id,
    wheel: visual.wheel.study_id,
    drive_type: visual.visual_style.drive_type,
    brake_family: visual.visual_style.brake_family,
  });
  if (Number.isFinite(Number(spec.stance_center_mm))) {
    params.set("stance_mm", String(spec.stance_center_mm));
  }
  for (const [layer, visible] of Object.entries(visual.layers)) {
    params.set(layer, visible ? "1" : "0");
  }
  return "../showcase/?" + params.toString();
}

function candidateSpecHtml(candidate) {
  const spec = candidate.personalized_spec || {};
  const energy = spec.selected_energy_class
    ? spec.selected_energy_class
        .replace("BATTERY-", "")
        .replace("-CLASS", "")
        .replaceAll("-", " ")
        .toLowerCase()
    : "no pack selected";
  const wheel = wheelLabel(spec.wheel_strategy || "");
  return (
    '<div class="candidate-spec">' +
      '<span>' + escapeHtml(spec.target_range_mi + " mi target") + '</span>' +
      '<span>' + escapeHtml("stance " + spec.stance_center_mm + " mm") + '</span>' +
      '<span>' + escapeHtml(wheel) + '</span>' +
      '<span>' + escapeHtml(energy) + '</span>' +
    '</div>'
  );
}

function candidateVisualState(candidate) {
  return visualStateFromCandidate(candidate, state.bundle.geometry, state.bundle.catalog);
}

function renderCandidateVisual(candidate) {
  const visual = candidateVisualState(candidate);
  const svg = renderBoardPreviewSvg(
    visual,
    state.galleryView,
    { width: 720, height: 360, compact: true }
  );
  const wheel = visual.wheel.visible
    ? Math.round(visual.wheel.diameter_mm) + " mm wheels"
    : "fit bench";
  const stance = visual.stance_mm ? Math.round(visual.stance_mm) + " mm stance" : "stance TBD";
  return (
    '<div class="candidate-visual" data-candidate-visual="' + escapeHtml(candidate.id) + '">' +
      svg +
      '<div class="candidate-visual-meta">' +
        '<span>' + escapeHtml(visual.vendor_family) + '</span>' +
        '<span>' + escapeHtml(visual.deck.id.replaceAll("_", " ")) + '</span>' +
        '<span>' + escapeHtml(wheel) + '</span>' +
        '<span>' + escapeHtml(stance) + '</span>' +
      '</div>' +
      '<div class="candidate-preview-actions">' +
        '<button type="button" data-download-preview="' + escapeHtml(candidate.id) + '">SVG</button>' +
      '</div>' +
    '</div>'
  );
}

function setGalleryView(view) {
  if (!["hero", "top", "side"].includes(view)) return;
  state.galleryView = view;
  document.querySelectorAll("[data-gallery-view]").forEach(button => {
    button.classList.toggle("active", button.dataset.galleryView === view);
  });
  if (state.result) {
    renderCandidates(state.result.candidates);
    renderDiverseShortlist();
    renderComparison();
    const candidate = state.result.candidates.find(row => row.id === state.selectedId);
    if (candidate && state.swapResult) renderSwapPreview(candidate);
  }
}

function renderVendorFilters(candidates) {
  const host = $("#vendor-filters");
  if (!host) return;
  const families = [...new Set(candidates.map(row => row.vendor_family || "Unspecified"))]
    .sort((a, b) => a.localeCompare(b));
  if (
    state.vendorFilter !== "all" &&
    !families.includes(state.vendorFilter)
  ) {
    state.vendorFilter = "all";
  }

  const options = [["all", "All"], ...families.map(value => [value, value])];
  host.innerHTML = "";
  for (const [value, label] of options) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.vendorFilter = value;
    button.textContent = label;
    button.classList.toggle("active", state.vendorFilter === value);
    button.addEventListener("click", () => {
      state.vendorFilter = value;
      renderVendorFilters(state.result.candidates);
      renderCandidates(state.result.candidates);
    });
    host.appendChild(button);
  }

  const visible = candidates.filter(row =>
    (state.vendorFilter === "all" || row.vendor_family === state.vendorFilter) &&
    (state.originFilter === "all" || row.origin === state.originFilter)
  ).length;
  const vendors = new Set(
    candidates.flatMap(row =>
      (row.bom || []).map(item => item.manufacturer).filter(Boolean)
    )
  );
  const sourced = state.bundle.catalog.components.filter(
    item => item.source?.url
  ).length;
  const health = state.bundle.catalogHealth;
  const healthSummary = health?.summary || {};
  const summary = state.result?.composition_summary;
  const originText = summary
    ? summary.curated_count + " curated + " + summary.synthesized_count + " composed"
    : candidates.length + " generated";
  $("#catalog-coverage").textContent =
    visible + " shown · " + originText + " · " +
    vendors.size + " named manufacturers · " + sourced +
    " source-linked parts · evidence " +
    (healthSummary.source_fresh ?? "?") + " fresh / " +
    (healthSummary.refresh_due ?? "?") + " refresh due · audited " +
    (health?.as_of || "unknown") + " · not stock status";
}

function traitsHtml(candidate) {
  const labels = {
    range: "Range",
    carve: "Carve",
    stability: "Stability",
    durability: "Durability",
    portability: "Portability",
    low_maintenance: "Low maint.",
  };
  return Object.entries(labels).map(([key, label]) =>
    '<div class="trait"><span>' + label + '</span><div class="bar"><i style="width:' +
    Math.round(candidate.traits[key] * 100) + '%"></i></div></div>'
  ).join("");
}

function renderExampleRides() {
  const host = $("#example-rides");
  host.innerHTML = "";
  for (const scenario of state.bundle.exampleRides.scenarios) {
    const reference = state.result.candidates.find(c => c.id === scenario.reference_candidate_id);
    const card = document.createElement("article");
    card.className = "example-card" + (scenario.id === state.activeExampleId ? " active" : "");
    const art = reference ? renderBoardPreviewSvg(candidateVisualState(reference),
      "hero", {width:480,height:230,compact:true}) :
      '<p class="example-status">Reference preview unavailable</p>';
    card.innerHTML = '<span class="example-tag">' + escapeHtml(scenario.eyebrow) + '</span>' +
      art + '<h3>' + escapeHtml(scenario.title) + '</h3>' +
      '<p>' + escapeHtml(scenario.terrain) + ' · ' + escapeHtml(scenario.rider) + '</p>' +
      '<p class="example-status">Illustrated catalog reference: ' +
      escapeHtml(reference?.label || scenario.reference_candidate_id) +
      '. Not a priced kit or qualified assembly.</p>' +
      '<div class="example-footer"><strong>Budget goal USD ' +
      Number(scenario.budget_usd).toLocaleString("en-US") +
      '</strong><button type="button" data-load-example="' + escapeHtml(scenario.id) +
      '">Load ride brief</button></div>';
    card.querySelector("[data-load-example]").addEventListener("click",()=>loadExampleRide(scenario.id));
    host.appendChild(card);
  }
  $("#restore-personal-profile").hidden = !state.originalProfileBeforeExamples;
  $("#example-status").textContent = state.activeExampleId ?
    "Example loaded into the local questionnaire. Refine it below; this is a planning study." :
    "Load a ride brief to explore budget, rider skill and terrain trade-offs."; 
}
function loadExampleRide(id) {
  const scenario=state.bundle.exampleRides.scenarios.find(x=>x.id===id);
  if(!scenario)return;
  if (!reconcileQuestionnaire()) {
    $("#example-status").textContent =
      "Complete or correct the current questionnaire before switching examples.";
    return;
  }
  if(!state.originalProfileBeforeExamples) {
    state.originalProfileBeforeExamples=structuredClone(state.profile);
    state.originalConversationBeforeExamples=exportRideConversation(state.conversation);
  }
  state.profile=profileForExample(scenario,questionnaireDefaults(state.bundle.questionnaire));
  state.conversation=createRideConversation(state.profile,state.bundle.questionnaire);
  state.rideBriefReview=null;state.sessionOutOfSync=false;
  state.conversationStatus="Example loaded. Previous personal conversation saved for restoration.";
  renderRideBriefReview();renderRideConversation();
  state.activeExampleId=id;
  state.selectedId=scenario.reference_candidate_id;
  state.comparisonIds=[scenario.reference_candidate_id,
    scenario.reference_candidate_id==="brake_first_trail_core"?"trampa_hydraulic_freeride":"brake_first_trail_core"];
  state.comparisonInitialized=true;
  state.vendorFilter="all";state.originFilter="all";
  document.querySelectorAll("[data-origin-filter]").forEach(el=>{
    el.classList.toggle("active",el.dataset.originFilter==="all");
  });
  renderQuestionnaire();recompute();
  $(".results-head").scrollIntoView({behavior:"smooth",block:"start"});
}
function restorePersonalProfile() {
  if(!state.originalProfileBeforeExamples)return;
  state.profile=state.originalProfileBeforeExamples;
  state.conversation=state.originalConversationBeforeExamples ||
    createRideConversation(state.profile,state.bundle.questionnaire);
  state.originalConversationBeforeExamples=null;
  state.rideBriefReview=null;state.sessionOutOfSync=false;
  state.conversationStatus="Restored your prior personal specification and conversation.";
  state.originalProfileBeforeExamples=null;state.activeExampleId=null;
  renderRideBriefReview();renderRideConversation();
  state.selectedId=null;state.comparisonIds=[];state.comparisonInitialized=false;
  renderQuestionnaire();recompute();
}
function renderDiverseShortlist() {
  const host = $("#shortlist-cards");
  const status = $("#shortlist-status");
  if (!host || !status) return;
  const shortlist=state.result?.diverse_shortlist;
  if (!shortlist) {host.replaceChildren();status.textContent="No shortlist computed.";return;}
  const byId=new Map(state.result.candidates.map(candidate=>[candidate.id,candidate]));
  const labels={deck:"deck",truck:"truck geometry",wheel:"wheels",brake:"braking",drive:"drive"};
  host.innerHTML=shortlist.studies.map((study,index)=>{
    const candidate=byId.get(study.id);
    if(!candidate)return "";
    const svg=renderBoardPreviewSvg(candidateVisualState(candidate),
      state.galleryView,{width:460,height:224,compact:true});
    const physical=study.differing_axes_from_first.map(axis=>labels[axis] || axis);
    const difference=index===0?"Baseline concept":
      "Different "+physical.join(", ");
    const unresolved=study.open_interfaces+" open interface"+
      (study.open_interfaces===1?"":"s");
    return '<article class="shortlist-card">' +
      '<div class="shortlist-visual">'+svg+'</div>'+
      '<div class="shortlist-card-body">'+
      '<span class="shortlist-number">Design direction '+(index+1)+'</span>'+
      '<h3>'+escapeHtml(candidate.label)+'</h3>'+
      '<p>'+escapeHtml(difference)+'</p>'+
      '<div class="shortlist-facts"><span>'+escapeHtml(candidate.readiness.replaceAll("_"," ").toLowerCase())+'</span>'+
      '<span>'+escapeHtml(unresolved)+'</span>'+
      '<span>'+study.unpriced_component_count+' unpriced items</span></div>'+
      '<button type="button" data-shortlist-inspect="'+escapeHtml(candidate.id)+'">Inspect design and BOM</button>'+
      '</div></article>';
  }).join("");
  status.textContent=shortlist.studies.length+" of "+shortlist.target_count+
    " mechanically different planning studies selected from "+shortlist.considered_count+
    " concepts. "+(shortlist.shortage_reason || "")+
    " Fit rankings, source evidence and visuals are not mechanical qualification or purchasing approval.";
  const exclusions=$("#shortlist-exclusions");
  if(exclusions) {
    const reasonLabels={
      HARD_MECHANICAL_OR_MISSION_BLOCKER:"Explicit mechanical or mission blocker",
      INCOMPATIBLE_INTERFACE:"Incompatible part interfaces",
      KNOWN_COMPONENT_COST_EXCEEDS_HARD_BUDGET:"Known component costs exceed budget ceiling",
      NOT_SELECTED_OR_INSUFFICIENT_MECHANICAL_DIVERSITY:"Other studies or mechanically similar alternatives",
      DUPLICATE_ID:"Duplicate catalog identifier",
      INVALID_PLANNING_CANDIDATE:"Invalid planning record"
    };
    const counts=new Map();
    for(const entry of shortlist.excluded)
      counts.set(entry.reason,(counts.get(entry.reason)||0)+1);
    const lines=[...counts].map(([reason,count])=>
      '<li>'+escapeHtml(reasonLabels[reason] || reason)+': '+count+'</li>').join("");
    exclusions.innerHTML=lines ?
      '<details><summary>Why other designs are not in these three directions ('+
      shortlist.excluded.length+')</summary><ul>'+lines+'</ul>'+
      '<p>Exclusion from this three-direction shortlist is not an overall safety finding. '+
      'Review each candidate’s full mechanical evidence and unresolved worklist below.</p></details>' : "";
  }
  host.querySelectorAll("[data-shortlist-inspect]").forEach(button=>{
    button.addEventListener("click",()=>{
      const id=button.dataset.shortlistInspect;
      const candidate=byId.get(id);
      if(!candidate)return;
      state.selectedId=id;
      state.vendorFilter="all";state.originFilter="all";
      document.querySelectorAll("[data-origin-filter]").forEach(el=>
        el.classList.toggle("active",el.dataset.originFilter==="all"));
      state.swapBaselineId=null;state.swapSelection=null;state.swapResult=null;
      renderVendorFilters(state.result.candidates);
      renderCandidates(state.result.candidates);
      renderBom(candidate);
      $("#bom-section").scrollIntoView({behavior:"smooth",block:"start"});
    });
  });
}

function renderFeasibilityPanel(){
  const host=$("#feasibility-records");
  const report=state.result?.feasibility_report;
  if(!host || !report)return;
  const byId=new Map(state.result.candidates.map(row=>[row.id,row]));
  const label={
    BLOCKED:"Blocked design study",
    UNRESOLVED_STUDY:"Evidence required",
    PLANNING_STUDY:"Planning study only"
  };
  const formatUsd=value=>typeof value==="number" && Number.isFinite(value)
    ? "$"+value.toLocaleString("en-US",{maximumFractionDigits:0}) : "unknown";
  host.innerHTML=report.records.map(record=>{
    const candidate=byId.get(record.candidate_id);
    if(!candidate)return "";
    const money=record.cost;
    const unknown=record.mechanical.unresolved_interfaces;
    const blockers=record.mechanical.explicit_blockers.length;
    const status=label[record.result] || record.result;
    const actions=record.next_steps.map(step=>"<li>"+escapeHtml(step)+"</li>").join("");
    const reasons=record.mechanical.explicit_blockers.map(step=>"<li>"+escapeHtml(step)+"</li>").join("");
    const costText="Known parts min: "+formatUsd(money.known_minimum_parts_usd)+
      " · hard budget: "+formatUsd(money.stated_hard_budget_usd)+
      " · "+money.unpriced_component_count+" unpriced items · all-in total unknown";
    return '<details class="feasibility-record">'+
      '<summary><strong>'+escapeHtml(candidate.label)+'</strong>'+
      '<span>'+escapeHtml(status)+'</span>'+
      '<small>'+unknown+' open interfaces · '+blockers+' explicit blockers</small></summary>'+
      '<p class="feasibility-cost">'+escapeHtml(costText)+'</p>'+
      (record.shortlist_exclusion_explanation?
        '<p>Shortlist status: '+escapeHtml(record.shortlist_exclusion_explanation)+'.</p>' : "")+
      (reasons?'<strong>Documented blockers</strong><ul>'+reasons+'</ul>' : "")+
      '<strong>Next evidence and integration tasks</strong><ul>'+actions+'</ul>'+
      '<p class="privacy-note">NOT QUALIFIED · No checkout, fabrication, charging or powered operation authorized.</p>'+
      '<button type="button" data-feasibility-inspect="'+escapeHtml(record.candidate_id)+'">Inspect detailed evidence and BOM</button>'+
      '</details>';
  }).join("");
  host.querySelectorAll("[data-feasibility-inspect]").forEach(button=>{
    button.addEventListener("click",()=>{
      const candidate=byId.get(button.dataset.feasibilityInspect);
      if(!candidate)return;
      state.selectedId=candidate.id;
      state.vendorFilter="all";state.originFilter="all";
      document.querySelectorAll("[data-origin-filter]").forEach(el=>
        el.classList.toggle("active",el.dataset.originFilter==="all"));
      state.swapBaselineId=null;state.swapSelection=null;state.swapResult=null;
      renderVendorFilters(state.result.candidates);
      renderCandidates(state.result.candidates);
      renderBom(candidate);
      $("#bom-section").scrollIntoView({behavior:"smooth",block:"start"});
    });
  });
}

function renderCandidates(candidates) {
  const host = $("#candidates");
  host.innerHTML = "";

  const visibleCandidates = candidates.filter(row =>
    (state.vendorFilter === "all" || row.vendor_family === state.vendorFilter) &&
    (state.originFilter === "all" || row.origin === state.originFilter)
  );

  for (const candidate of visibleCandidates) {
    const card = document.createElement("article");
    card.className = "candidate" + (candidate.id === state.selectedId ? " selected" : "");

    const issueText = candidate.blockers.length
      ? '<div class="alert-mini red">' + candidate.blockers.length + ' blocker' + (candidate.blockers.length === 1 ? "" : "s") + '</div>'
      : candidate.unknowns.length
        ? '<div class="alert-mini">' + candidate.unknowns.length + ' unresolved item' + (candidate.unknowns.length === 1 ? "" : "s") + '</div>'
        : "";

    card.innerHTML =
      renderCandidateVisual(candidate) +
      '<div class="candidate-top">' +
        '<div><h3>' + escapeHtml(candidate.label) + '</h3><p>' + escapeHtml(candidate.description) + '</p></div>' +
        '<div class="fit-score"><strong>' + Math.round(candidate.fit_score * 100) + '%</strong><span>profile fit</span></div>' +
      '</div>' +
      '<div class="badges">' +
        '<span class="badge origin-chip ' + (candidate.origin === "SYNTHESIZED" ? "composed" : "curated") + '">' +
          escapeHtml(candidate.origin === "SYNTHESIZED" ? "catalog composed" : "curated reference") +
        '</span>' +
        '<span class="badge vendor-chip">' + escapeHtml(candidate.vendor_family || "Unspecified") + '</span>' +
        '<span class="badge ' + statusClass(candidate.readiness) + '">' + escapeHtml(readinessLabel(candidate.readiness)) + '</span>' +
        (candidate.trade_space_frontier ? '<span class="badge frontier">trade-space frontier</span>' : '') +
        '<span class="badge">' + escapeHtml(candidate.checkout_state.replaceAll("_", " ").toLowerCase()) + '</span>' +
      '</div>' +
      '<div class="traits">' + traitsHtml(candidate) + '</div>' +
      candidateSpecHtml(candidate) +
      issueText +
      '<p class="evidence-preview">' + escapeHtml(candidate.evidence.summary.open_interfaces + " interfaces to resolve · " + candidate.evidence.summary.source_refresh_or_integrity_issues + " source follow-ups") + '</p>' +
      '<div class="candidate-footer">' +
        '<div class="cost"><strong>' + partialCost(candidate) + '</strong><small>known USD subtotal · ' +
          candidate.cost.unpriced_component_ids.length + ' unpriced/source-native item' +
          (candidate.cost.unpriced_component_ids.length === 1 ? '' : 's') +
          ' · shipping/tax excluded</small></div>' +
        '<div class="candidate-actions">' +
          '<button type="button" data-compare="' + escapeHtml(candidate.id) +
             '" aria-pressed="' + state.comparisonIds.includes(candidate.id) + '">' +
             (state.comparisonIds.includes(candidate.id) ? "✓ Comparing" : "Compare") + '</button>' +
          '<button type="button" data-inspect="' + escapeHtml(candidate.id) + '">Inspect evidence + BOM</button>' +
          '<a href="' + escapeHtml(twinUrl(candidate)) + '">3D</a>' +
        '</div>' +
      '</div>';

    card.querySelector("[data-download-preview]").addEventListener("click", event => {
      event.stopPropagation();
      downloadBoardPreviewSvg(candidateVisualState(candidate), state.galleryView);
    });

    card.querySelector("[data-compare]").addEventListener("click", () => {
      toggleComparison(candidate.id);
    });
    card.querySelector("[data-inspect]").addEventListener("click", () => {
      state.selectedId = candidate.id;
      state.swapBaselineId = null;
      state.swapSelection = null;
      state.swapResult = null;
      renderCandidates(state.result.candidates);
      renderBom(candidate);
      $("#bom-section").scrollIntoView({ behavior: "smooth", block: "start" });
    });
    host.appendChild(card);
  }
}

function toggleComparison(id) {
  const ids = [...state.comparisonIds];
  if (ids.includes(id)) {
    state.comparisonIds = ids.filter(x => x !== id);
  } else {
    state.comparisonIds = ids.length < 2 ? [...ids,id] : [ids[1],id];
  }
  state.comparisonInitialized = true;
  renderCandidates(state.result.candidates);
  renderComparison();
}

function comparisonReport() {
  const ids = state.comparisonIds;
  if (ids.length !== 2 || ids[0] === ids[1]) return null;
  const left = state.result.candidates.find(c=>c.id === ids[0]);
  const right = state.result.candidates.find(c=>c.id === ids[1]);
  return left && right ? compareCandidates(
    left,right,state.bundle.geometry,state.bundle.catalog) : null;
}
function renderComparison() {
  const candidates = state.result.candidates;
  for (const [i,key] of ["compare-a","compare-b"].entries()) {
    const select = $("#" + key);
    select.replaceChildren();
    const empty = document.createElement("option");
    empty.value = ""; empty.textContent = "Choose design " + (i ? "B" : "A");
    select.appendChild(empty);
    for (const c of candidates) {
      const opt=document.createElement("option");
      opt.value=c.id; opt.textContent=c.label + " · " + c.vendor_family;
      select.appendChild(opt);
    }
    select.value=state.comparisonIds[i] || "";
  }
  const host=$("#compare-results"),report=comparisonReport();
  if (!report) {
    host.innerHTML='<p class="compare-warning">Choose two distinct designs from the gallery or selectors. Neither candidate receives purchase, build or ride permission.</p>';
    $("#compare-export").disabled=true; return;
  }
  $("#compare-export").disabled=false;
  const n=v=>v == null ? "unknown" : String(v);
  const fmt=v=>v==null ? "not recorded" : String(v) + " mm";
  const usd=v=>"$" + Number(v).toLocaleString("en-US",{maximumFractionDigits:0});
  const line=(k,v)=>'<dt>'+escapeHtml(k)+'</dt><dd>'+escapeHtml(v)+'</dd>';
  const image=x=>renderBoardPreviewSvg(x.visual,state.galleryView,{width:640,height:320,compact:true});
  const card=(x,index)=>{
    const g=x.geometry,c=x.cost,e=x.evidence;
    const issues=e.worklist.slice(0,5);
    const sourceIssues=(e.sources||[]).filter(s=>["REFRESH_DUE","STALE","MISSING_PROVENANCE","HEALTH_UNAVAILABLE"].includes(s.health_status)).slice(0,3);
    return '<article class="compare-card"><span class="example-tag">DESIGN '+(index===0?"A":"B")+' · '+
      escapeHtml(x.origin)+'</span><h3>'+escapeHtml(x.label)+'</h3>' +
      '<div class="compare-viz">'+image(x)+'</div>' +
      '<p class="compare-sub">'+escapeHtml(x.vendor_family)+' · '+
      Math.round(x.fit_score*100)+'% profile preference fit, not a safety score</p>' +
      '<dl>'+line('Readiness',x.readiness)+line('Checkout',x.checkout_state)+
      line('Deck / length',g.deck_id+' · '+fmt(g.deck_length_mm))+
      line('Truck width',g.truck_id+' · '+fmt(g.truck_width_mm))+
      line('Wheels',g.wheel_id+' · '+fmt(g.wheel_diameter_mm))+
      line('Brake / drive',g.brake+' / '+g.drive)+
      line('Geometry basis',g.visual_geometry_state||g.topology_evidence_state||"reference")+
      line('Known USD subtotal',usd(c.known_min_usd)+'–'+usd(c.known_max_usd))+
      line('Unpriced components',c.unpriced_component_ids.length+'; total cost unknown')+
      line('Unresolved / incompatible',e.open_interfaces+' / '+e.incompatible_interfaces)+
      line('Source follow-ups',e.source_followups)+
      line('Assembly pathway',x.assembly.complexity.replaceAll('_',' ').toLowerCase())+
      '</dl><div class="compare-evidence"><strong>Measurement tasks</strong>' +
      (issues.length?'<ul>'+issues.map(t=>'<li>'+escapeHtml(t.question)+'</li>').join('')+'</ul>':
        '<p>No listed measurement tasks. Missing documentation may still exist.</p>')+
      (e.worklist.length>issues.length?'<small>+'+(e.worklist.length-issues.length)+' more in the evidence explorer</small>':'')+
      '<strong>Source maintenance</strong>' +
      (sourceIssues.length?'<ul>'+sourceIssues.map(s=>'<li>'+escapeHtml(s.component_id+' · '+s.health_status.replaceAll('_',' ').toLowerCase())+'</li>').join('')+'</ul>':
        '<p>No flagged source-maintenance items in the dated snapshot; not stock confirmation.</p>')+
      '</div></article>';
  };
  host.innerHTML=(report.mechanically_distinct?'':'<p class="compare-warning">These have the same recorded deck, truck, wheel, brake and drive geometry; choose a mechanically different alternative for a useful comparison.</p>')+
    '<div class="compare-grid">'+report.candidates.map(card).join('')+'</div>' +
    '<p class="compare-legend">'+escapeHtml(report.comparison_note)+
    ' Costs omit shipping, tax, tools, professional work and tests. Different geometry is not proven compatible.</p>';
}

function setComparisonSlot(index,id) {
  const ids=[state.comparisonIds[0]||null,state.comparisonIds[1]||null];
  ids[index]=id||null;
  if (ids[0] && ids[0]===ids[1]) ids[1-index]=null;
  state.comparisonIds=ids.filter(Boolean);
  // Keep A/B positions stable when only one side is selected.
  if (ids[0] && !ids[1]) state.comparisonIds=[ids[0]];
  else if (!ids[0] && ids[1]) state.comparisonIds=[null,ids[1]];
  else if(ids[0]&&ids[1])state.comparisonIds=ids;
  state.comparisonInitialized=true;
  renderCandidates(state.result.candidates);
  renderComparison();
}
function exportComparison() {
  const report=comparisonReport();
  if (!report)return;
  downloadJson("worcester-board-comparison.json",{
    ...report,source_snapshot_as_of:state.bundle.catalog.as_of,
    note:"Two design studies only. Neither is purchase, assembly, charging or powered-operation authorized."
  });
}

function renderAssemblyGuide(candidate) {
  const host=$("#assembly-guide");
  if(!candidate) {host.innerHTML='<p>Select a design to inspect assembly effort.</p>';return;}
  const guide=assemblyGuide(candidate);
  host.innerHTML='<div class="assembly-overview"><span>Selected: '+escapeHtml(candidate.label)+'</span>'+
    '<span>'+escapeHtml(guide.complexity.replaceAll("_"," ").toLowerCase())+'</span>'+
    '<span>'+guide.unresolved_interfaces+' open mechanical interfaces</span>'+
    '<span>'+guide.unpriced_components+' unpriced study parts</span></div>'+
    '<p class="compare-legend">This is a planning roadmap, not a self-assembly permit. All generated candidates remain unreleased. No live electrical commissioning steps are provided.</p>'+
    '<div class="assembly-steps">'+guide.stages.map((s,i)=>
      '<article class="assembly-step"><div><h3>'+(i+1)+'. '+escapeHtml(s.label)+'</h3>'+
      '<p>'+escapeHtml(s.description)+'</p>'+
      '<small>Skills: '+escapeHtml(s.skill)+'</small>'+
      '<small>Evidence needed: '+escapeHtml(s.deliverable)+'</small></div>'+
      '<strong class="assembly-status">'+escapeHtml(s.status.replaceAll('_',' '))+'</strong></article>'
    ).join('')+'</div>'+
    '<p class="compare-legend">Additional budget categories: '+escapeHtml(guide.budget_exclusions.join(' · '))+
    '. An independent safety reviewer must use the separately qualified physical design, not this UI export.</p>';
}
function exportAssemblyGuide() {
  const candidate=state.result?.candidates.find(c=>c.id===state.selectedId);
  if(!candidate)return;
  downloadJson("worcester-assembly-planning-"+candidate.id+".json",{
    schema_version:1,candidate_id:candidate.id,assembly:assemblyGuide(candidate),
    measurement_worklist:candidate.evidence.measurement_worklist,
    authority:candidate.evidence.authority,
    note:"Inspection and learning only; no purchasing, fabrication, charging, commissioning or ride authority."
  });
}

function currentBuildPassport(candidate=null) {
  const selected=candidate || state.result?.candidates.find(x=>x.id===state.selectedId);
  if(!selected)return null;
  if(state.passportCandidateId!==selected.id) {
    state.passportCandidateId=selected.id;
    state.passportRevisionReceipt=null;
  }
  return state.passportRevisionReceipt || buildBuildPassport(selected,state.bundle);
}
function renderBuildPassport(candidate){
  const host=$("#build-passport");
  const passport=currentBuildPassport(candidate);
  $("#export-build-passport").disabled=!passport;
  $("#print-build-passport").disabled=!passport;
  if(!passport){host.textContent="Select a board to inspect its sourcing and assembly evidence.";return;}
  const cost=passport.sourcing;
  const usd=v=>typeof v==="number" ? "$"+v.toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2}) : "Unknown";
  const quote=(part)=>part.price.min_usd===null
    ? (part.price.max_usd===null?"Unpriced":"Up to "+usd(part.price.max_usd)+" (ceiling)")
    : usd(part.price.min_usd)+(part.price.max_usd!==part.price.min_usd
      ? " to "+usd(part.price.max_usd):"");
  const seller=(part)=>{
    const src=part.supplier;
    const url=src.source_url;
    const safeUrl=typeof url==="string" && /^https?:\/\//i.test(url) ? url : null;
    const sourceLink=safeUrl?'<a href="'+escapeHtml(safeUrl)+
      '" rel="noopener noreferrer" target="_blank">Supplier reference</a>':
      '<span>No vendor URL</span>';
    return sourceLink+
      '<small>'+escapeHtml(src.name || src.source_kind)+' · '+
      escapeHtml(src.verified_as_of || src.catalog_as_of || "undated")+
      ' · '+escapeHtml(src.source_health)+'</small>';
  };
  const table=passport.parts.map(part=>
    '<tr><td><strong>'+escapeHtml(part.label)+'</strong><small>'+
    escapeHtml(part.component_id)+' · '+escapeHtml(part.manufacturer || "Unspecified maker")+
    '</small></td><td>'+escapeHtml(part.sku_text || "SKU not established")+
    '<small>'+escapeHtml(part.proposed_revision?"Proposed "+part.proposed_revision+" (unverified)":
    "Exact received revision not verified")+'</small></td>'+
    '<td>Unknown build count<small>Catalog price factor: '+
      escapeHtml(part.price.pricing_reference_qty ?? "?")+'</small></td>'+
    '<td>'+escapeHtml(quote(part))+'<small>'+
      escapeHtml(part.price.price_basis.replaceAll("_"," ").toLowerCase())+
      '</small></td>'+
    '<td>'+seller(part)+'<small>Stock unknown · '+
      escapeHtml(part.procurement_state)+'</small></td></tr>').join("");
  const open=passport.unresolved.measurement_worklist;
  const printed=passport.change_receipt;
  const stages=passport.assembly.stages.map(stage=>
    '<li><strong>'+escapeHtml(stage.label)+'</strong> · '+
    escapeHtml(stage.status.replaceAll("_"," "))+
    '<span>'+escapeHtml(stage.skills_and_work)+'</span></li>').join("");
  host.innerHTML='<div class="passport-overview">'+
    '<div><small>Reference USD snapshot</small><strong>'+usd(cost.sourced_usd_snapshot.min)+
    ' to '+usd(cost.sourced_usd_snapshot.max)+'</strong></div>'+
    '<div><small>Unsourced planning estimates</small><strong>'+usd(cost.unsourced_planning_usd_estimate.min)+
    ' to '+usd(cost.unsourced_planning_usd_estimate.max)+'</strong></div>'+
    '<div><small>Unknowns</small><strong>'+cost.unpriced_ids.length+
    ' unpriced · '+cost.ceiling_only_ids.length+' ceiling-only prices · '+open.length+' interface checks</strong></div></div>'+
    '<p class="passport-warning">All-in price UNKNOWN. Quote quantities, exact revisions, vendor stock, '+
    'manufacturer manuals and independent physical qualification are not confirmed. '+escapeHtml(passport.disclaimer)+'</p>'+
    '<div class="table-wrap"><table class="passport-table"><thead><tr>'+
    '<th>Catalog component</th><th>SKU / revision</th><th>Assembly quantity</th><th>Price snapshot</th><th>Supplier</th>'+
    '</tr></thead><tbody>'+table+'</tbody></table></div>'+
    '<div class="passport-dual">'+
    '<div><h3>Receiving and interface evidence</h3>'+
    '<p>'+passport.unresolved.unverified_revision_part_ids.length+' unverified revisions · '+
      passport.unresolved.missing_manual_part_ids.length+' missing manufacturer instruction links · '+
      passport.unresolved.source_refresh_ids.length+' source health follow-ups</p>'+
    '<ol>'+open.slice(0,8).map(item=>'<li>'+escapeHtml(item.question)+
      '<small>'+escapeHtml(item.component_ids.join(" + "))+'</small></li>').join("")+'</ol>'+
    (open.length>8?'<p>+'+(open.length-8)+' more checks in JSON export and evidence explorer.</p>':'')+
    '</div><div><h3>Assembly learning stages</h3><ol>'+stages+'</ol>'+
    '<p>Electrical, battery and commissioning stages remain independently gated.</p></div></div>'+
    '<div class="passport-revision-tool"><h3>What if the supplier sends a different revision?</h3>'+
    '<p>Re-evaluate affected claims before considering a substitute. This is a local what-if check; it changes no catalog facts or purchase permission.</p>'+
    '<div class="passport-revision-row"><label>Component<select id="passport-component">'+
    passport.parts.map(p=>'<option value="'+escapeHtml(p.component_id)+'">'+escapeHtml(p.label)+'</option>').join("")+
    '</select></label><label>Proposed revision<input id="passport-revision" type="text" maxlength="120" placeholder="Revision as marked on supplier part"></label>'+
    '<button type="button" id="passport-check-revision">Show invalidated claims</button>'+
    '<button type="button" id="passport-reset-revision">Reset what-if</button></div>'+
    '<p id="passport-revision-status" role="status">'+
    (printed?'Unverified revision '+escapeHtml(printed.proposed_revision)+' for '+
      escapeHtml(printed.component_id)+' invalidates '+printed.invalidated_interface_ids.length+
      ' catalog interface claims. Revalidate before any physical use.':
      'Changing a part revision invalidates relevant catalog interface evidence.')+'</p></div>'+
    '<p class="passport-footer">Planning handoff only. No procurement, fabrication, charging or powered-operation authority. '+
    'Manufacturer documentation and actual receiving inspection must govern any separately qualified build.</p>';
  $("#passport-check-revision").addEventListener("click",()=>{
    const id=$("#passport-component").value,revision=$("#passport-revision").value;
    try{
      // Always start from the catalog snapshot, never accumulate speculative revisions.
      state.passportRevisionReceipt=proposePassportRevisionChange(
        buildBuildPassport(candidate,state.bundle),id,revision);
      renderBuildPassport(candidate);
    }catch(error) {
      $("#passport-revision-status").textContent=error.message;
    }
  });
  $("#passport-reset-revision").addEventListener("click",()=>{
    state.passportRevisionReceipt=null;
    renderBuildPassport(candidate);
  });
}

function renderBom(candidate) {
  if (!candidate) return;

  $("#bom-title").textContent = candidate.label;
  const twin = $("#open-twin");
  twin.classList.remove("disabled");
  twin.href = twinUrl(candidate);

  const cost = candidate.cost;
  $("#bom-summary").innerHTML =
    '<span class="summary-pill">Known subtotal: <strong>' + escapeHtml(partialCost(candidate)) + '</strong></span>' +
    '<span class="summary-pill">Readiness: <strong>' + escapeHtml(readinessLabel(candidate.readiness)) + '</strong></span>' +
    '<span class="summary-pill">Checkout: <strong>' + escapeHtml(candidate.checkout_state.replaceAll("_", " ").toLowerCase()) + '</strong></span>' +
    '<span class="summary-pill">Unpriced study items: <strong>' + cost.unpriced_component_ids.length + '</strong></span>';

  $("#bom-body").innerHTML = candidate.bom.map(row => {
    const source = row.source_url
      ? '<a class="source-link" href="' + escapeHtml(row.source_url) + '" target="_blank" rel="noreferrer">Vendor source</a>' +
        sourceEvidenceHtml(row.component_id)
      : '<span>Reference / TBD</span>' + sourceEvidenceHtml(row.component_id);

    const hold = row.hold_reason ? '<small>' + escapeHtml(row.hold_reason) + '</small>' : "";
    return '<tr>' +
      '<td>' + escapeHtml(row.category.replaceAll("_", " ")) + '</td>' +
      '<td><strong>' + escapeHtml(row.label) + '</strong><small>' +
        escapeHtml([row.manufacturer, row.sku].filter(Boolean).join(" · ") || row.component_id) + '</small></td>' +
      '<td><span class="badge ' + (row.procurement_state === "POWER_GATED" ? "blocked" : row.procurement_state === "HOLD_MEASURE" ? "measure" : "") + '">' +
        escapeHtml(row.procurement_state.replaceAll("_", " ").toLowerCase()) + '</span>' + hold + '</td>' +
      '<td>' + escapeHtml(row.price ? formatPrice(row.price) : (row.source_native_price || "Unpriced")) +
        (row.source_native_price && !row.price ? '<small>native source snapshot</small>' : '') + '</td>' +
      '<td>' + source + '</td>' +
    '</tr>';
  }).join("");

  const blocks = candidate.blockers.length
    ? '<div class="detail-box"><h3>Blockers</h3><ul>' + candidate.blockers.map(x => '<li>' + escapeHtml(x) + '</li>').join("") + '</ul></div>'
    : '<div class="detail-box"><h3>Blockers</h3><ul><li>No architecture-level blocker is asserted by the current reference data. Physical gates still apply.</li></ul></div>';

  const unknowns = '<div class="detail-box"><h3>Measure / resolve next</h3><ul>' +
    candidate.unknowns.map(x => '<li>' + escapeHtml(x) + '</li>').join("") + '</ul></div>';

  const why = '<div class="detail-box"><h3>Why it fits</h3><ul>' +
    candidate.explanations.map(x => '<li>' + escapeHtml(x) + '</li>').join("") + '</ul></div>';

  const composition = candidate.origin === "SYNTHESIZED" && candidate.composition
    ? '<div class="detail-box composition-detail"><h3>How this board was composed</h3>' +
      '<p>' + escapeHtml(candidate.composition.rationale) + '</p>' +
      '<ul>' +
        Object.entries(candidate.composition.selection || {}).map(([slot, value]) =>
          '<li><strong>' + escapeHtml(slot.replaceAll("_", " ")) + ':</strong> ' +
          escapeHtml(String(value ?? "none")) + '</li>'
        ).join("") +
      '</ul>' +
      '<p class="composition-states">' +
        Object.entries(candidate.composition.compatibility_states || {})
          .filter(([, count]) => Number(count) > 0)
          .map(([status, count]) =>
            escapeHtml(status.replaceAll("_", " ").toLowerCase()) + ': ' + Number(count)
          ).join(' · ') +
      '</p></div>'
    : '<div class="detail-box"><h3>Candidate origin</h3><p>Curated reference architecture retained as a stable comparison and regression anchor.</p></div>';

  const compatibility = '<div class="detail-box"><h3>Compatibility evidence</h3><ul>' +
    (candidate.compatibility_findings.length
      ? candidate.compatibility_findings.map(x => '<li><strong>' + escapeHtml(x.state.replaceAll("_", " ").toLowerCase()) + ':</strong> ' + escapeHtml(x.reason) + '</li>').join("")
      : '<li>No explicit selected-pair rule fired for this candidate.</li>') +
    '</ul></div>';

  $("#candidate-detail").innerHTML = composition + blocks + unknowns + why;
  const explorer = $("#evidence-explorer");
  explorer.innerHTML = evidencePanelHtml(candidate.evidence, true);
  explorer.querySelector("#export-evidence").addEventListener("click", exportEvidenceWorklist);
  renderSwapLab(candidate, state.swapBaselineId !== candidate.id);
  renderAssemblyGuide(candidate);
  renderBuildPassport(candidate);
}


function signedUsd(value) {
  const number = Number(value || 0);
  if (Math.abs(number) < 0.005) return "USD 0";
  return (number > 0 ? "+USD " : "−USD ") + Math.abs(number).toFixed(0);
}

function customTwinUrl(candidate, swapResult) {
  const twin = swapResult.twin_state || {};
  const visual = visualStateFromSwap(
    candidate,
    swapResult,
    state.bundle.geometry,
    state.bundle.catalog
  );
  const params = new URLSearchParams({
    preset: candidate.visual_preset,
    candidate: "custom:" + candidate.id,
    deck: twin.deck_candidate_id || candidate.deck_candidate_id,
    topology: twin.topology_id || candidate.topology_id,
    wheel: visual.wheel.study_id,
    drive_type: visual.visual_style.drive_type,
    brake_family: visual.visual_style.brake_family,
  });
  if (Number.isFinite(Number(twin.stance_mm))) {
    params.set("stance_mm", String(twin.stance_mm));
  }
  for (const [layer, visible] of Object.entries(twin.layers || {})) {
    params.set(layer, visible ? "1" : "0");
  }
  return "../showcase/?" + params.toString();
}

function renderSwapBom(rows) {
  const body = $("#swap-bom-body");
  if (!body) return;
  body.innerHTML = rows.map(row => {
    const source = row.source_url
      ? '<a class="source-link" href="' + escapeHtml(row.source_url) + '" target="_blank" rel="noreferrer">Vendor source</a>' +
        sourceEvidenceHtml(row.component_id)
      : '<span>Reference / TBD</span>' + sourceEvidenceHtml(row.component_id);
    const hold = row.hold_reason
      ? '<small>' + escapeHtml(row.hold_reason) + '</small>'
      : "";
    const stateClass =
      row.procurement_state === "POWER_GATED"
        ? "blocked"
        : row.procurement_state === "HOLD_MEASURE"
          ? "measure"
          : "";
    return '<tr>' +
      '<td>' + escapeHtml(row.category.replaceAll("_", " ")) + '</td>' +
      '<td><strong>' + escapeHtml(row.label) + '</strong><small>' +
        escapeHtml([row.manufacturer, row.sku].filter(Boolean).join(" · ") || row.component_id) +
      '</small></td>' +
      '<td><span class="badge ' + stateClass + '">' +
        escapeHtml(row.procurement_state.replaceAll("_", " ").toLowerCase()) +
      '</span>' + hold + '</td>' +
      '<td>' + escapeHtml(row.price ? formatPrice(row.price) : (row.source_native_price || "Unpriced")) +
        (row.source_native_price && !row.price ? '<small>native source snapshot</small>' : '') + '</td>' +
      '<td>' + source + '</td>' +
    '</tr>';
  }).join("");
}

function renderSwapFindings(result) {
  const host = $("#swap-findings");
  if (!host) return;

  const blockers = result.blockers.length
    ? result.blockers.map(text => '<li>' + escapeHtml(text) + '</li>').join("")
    : '<li>No custom-design hard blocker is asserted by the current rules. Physical gates still apply.</li>';

  const unknowns = result.unknowns.length
    ? result.unknowns.map(text => '<li>' + escapeHtml(text) + '</li>').join("")
    : '<li>No additional custom-design measurement hold is asserted.</li>';

  const compatibility = result.compatibility_findings.length
    ? result.compatibility_findings.map(finding =>
        '<li><strong>' + escapeHtml(finding.state.replaceAll("_", " ").toLowerCase()) +
        ':</strong> ' + escapeHtml(finding.reason) + '</li>'
      ).join("")
    : '<li>No selected component pair triggered an explicit compatibility rule.</li>';

  const changes = result.changes.length
    ? result.changes.map(change =>
        '<li><strong>' + escapeHtml(change.slot.replaceAll("_", " ")) + ':</strong> ' +
        escapeHtml(String(change.from ?? "none")) + ' → ' +
        escapeHtml(String(change.to ?? "none")) + '</li>'
      ).join("")
    : '<li>Edited design matches the generated baseline.</li>';

  host.innerHTML =
    '<div class="detail-box"><h3>Changes from baseline</h3><ul>' + changes + '</ul></div>' +
    '<div class="detail-box"><h3>Blockers</h3><ul>' + blockers + '</ul></div>' +
    '<div class="detail-box"><h3>Measure / resolve next</h3><ul>' + unknowns + '</ul></div>' +
    '<div class="detail-box"><h3>Compatibility evidence</h3><ul>' + compatibility + '</ul></div>';
}

function renderSwapPreview(candidate) {
  const host = $("#swap-preview");
  if (!host || !state.swapResult) return;
  const visual = visualStateFromSwap(
    candidate,
    state.swapResult,
    state.bundle.geometry,
    state.bundle.catalog
  );
  host.innerHTML = renderBoardPreviewSvg(
    visual,
    state.galleryView,
    { width: 720, height: 360, compact: false }
  );
}

function renderSwapResult(candidate) {
  const result = state.swapResult;
  if (!result) return;

  renderSwapPreview(candidate);

  $("#swap-summary").innerHTML =
    '<span class="summary-pill">Edited subtotal: <strong>' +
      escapeHtml(partialCost(result)) + '</strong></span>' +
    '<span class="summary-pill">Readiness: <strong>' +
      escapeHtml(readinessLabel(result.readiness)) + '</strong></span>' +
    '<span class="summary-pill">Checkout: <strong>' +
      escapeHtml(result.checkout_state.replaceAll("_", " ").toLowerCase()) + '</strong></span>' +
    '<span class="summary-pill">Changes: <strong>' +
      result.changes.length + '</strong></span>';

  const delta = result.cost_delta_vs_baseline;
  $("#swap-delta").innerHTML =
    '<div><span>Known-price delta low</span><strong>' +
      escapeHtml(signedUsd(delta.known_min_usd)) + '</strong></div>' +
    '<div><span>Known-price delta high</span><strong>' +
      escapeHtml(signedUsd(delta.known_max_usd)) + '</strong></div>' +
    '<div><span>Unpriced study items</span><strong>' +
      result.cost.unpriced_component_ids.length + '</strong></div>';

  renderSwapFindings(result);
  $("#swap-evidence-explorer").innerHTML = evidencePanelHtml(swapEvidence(candidate, result));
  renderSwapBom(result.bom);

  const twin = $("#open-custom-twin");
  twin.classList.remove("disabled");
  twin.href = customTwinUrl(candidate, result);
}

function evaluateCurrentSwap(candidate) {
  if (!candidate || !state.swapSelection) return;
  state.swapResult = evaluateSwap(
    candidate,
    state.result.requirements,
    state.swapSelection,
    state.bundle,
    state.bundle.swapSlots
  );
  renderSwapResult(candidate);
}

function renderSwapControls(candidate) {
  const host = $("#swap-controls");
  if (!host) return;
  const baseline = seedSwapSelection(candidate);
  host.innerHTML = "";

  for (const slot of state.bundle.swapSlots.slots || []) {
    const wrapper = document.createElement("div");
    wrapper.className = "swap-control";

    const label = document.createElement("label");
    label.htmlFor = "swap-" + slot.id;
    label.textContent = slot.label;

    const select = document.createElement("select");
    select.id = "swap-" + slot.id;
    select.dataset.swapSlot = slot.id;

    for (const optionRow of slot.options || []) {
      const option = document.createElement("option");
      option.value = optionRow.value === null ? "__none__" : String(optionRow.value);
      option.textContent =
        optionRow.label +
        (baseline[slot.id] === optionRow.value ? " · baseline" : "");
      select.appendChild(option);
    }

    const selected = state.swapSelection[slot.id];
    select.value = selected === null ? "__none__" : String(selected);
    select.addEventListener("change", () => {
      state.swapSelection[slot.id] =
        select.value === "__none__" ? null : select.value;
      evaluateCurrentSwap(candidate);
    });

    wrapper.append(label, select);
    host.appendChild(wrapper);
  }
}

function renderSwapLab(candidate, forceReset = false) {
  if (!candidate) return;
  if (forceReset || state.swapBaselineId !== candidate.id || !state.swapSelection) {
    state.swapBaselineId = candidate.id;
    state.swapSelection = seedSwapSelection(candidate);
  }
  renderSwapControls(candidate);
  evaluateCurrentSwap(candidate);
}

function resetSwaps() {
  const candidate = state.result?.candidates.find(row => row.id === state.selectedId);
  if (!candidate) return;
  state.swapSelection = seedSwapSelection(candidate);
  renderSwapControls(candidate);
  evaluateCurrentSwap(candidate);
}

function exportCustomDesign() {
  const candidate = state.result?.candidates.find(row => row.id === state.selectedId);
  if (!candidate || !state.swapResult) return;
  downloadJson("worcester-custom-board-" + candidate.id + ".json", {
    schema_version: 1,
    profile: state.result.profile,
    requirements: state.result.requirements,
    baseline_candidate: candidate,
    custom_study: state.swapResult,
    evidence: swapEvidence(candidate, state.swapResult),
    visual_state: visualStateFromSwap(
      candidate,
      state.swapResult,
      state.bundle.geometry,
      state.bundle.catalog
    ),
    winner_selected: false,
    source_snapshot_as_of: state.bundle.catalog.as_of,
    note:
      "Exported Swap Lab design study. It does not create procurement, fabrication, charging or powered-operation authority.",
  });
}

function recompute() {
  if (!state.bundle) return;
  let nextResult;
  try {
    nextResult = generateBoardDesignSpace(state.profile, state.bundle);
  } catch (error) {
    // During number/terrain editing the profile may be temporarily incomplete.
    // Never present a stale design gallery as newly computed or imply a release.
    $("#recompute-status").textContent =
      "Check inputs · last successful design preview remains unchanged";
    state.conversationStatus = "Complete or correct the rider specifications: " + error.message;
    renderRideConversation();
    return;
  }
  state.result = nextResult;
  state.passportCandidateId=null;
  state.passportRevisionReceipt=null;
  state.swapBaselineId = null;
  state.swapSelection = null;
  state.swapResult = null;

  if (!state.selectedId || !state.result.candidates.some(x => x.id === state.selectedId)) {
    state.selectedId = state.result.candidates[0]?.id || null;
  }

  const candidateIds=new Set(state.result.candidates.map(x=>x.id));
  state.comparisonIds=state.comparisonIds.filter(id=>!id||candidateIds.has(id));
  if (!state.comparisonInitialized) {
    state.comparisonIds=defaultComparisonIds(state.result.candidates);
    state.comparisonInitialized=true;
  }
  renderRequirements(state.result.requirements);
  renderDiverseShortlist();
  renderFeasibilityPanel();
  renderVendorFilters(state.result.candidates);
  renderExampleRides();
  renderCandidates(state.result.candidates);
  renderComparison();
  renderBom(state.result.candidates.find(x => x.id === state.selectedId));
  $("#recompute-status").textContent =
    "Live · " + state.result.candidates.length + " candidates · " +
    (state.result.composition_summary?.synthesized_count || 0) + " composed · " +
    new Set(state.result.candidates.map(row => row.vendor_family || "Unspecified")).size +
    " families";
}

function scheduleRecompute() {
  if (state.renderQueued) return;
  state.renderQueued = true;
  requestAnimationFrame(() => {
    state.renderQueued = false;
    if (state.sessionOutOfSync) {
      $("#recompute-status").textContent =
        "Editing · designs update after specification validation";
      return;
    }
    recompute();
  });
}

function downloadJson(filename, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2) + "\n"], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function exportProfile() {
  downloadJson("worcester-board-profile.json", {
    schema_version: 1,
    profile: state.result?.profile || state.profile,
    requirements: state.result?.requirements || null,
    winner_selected: false,
    note: "Exported planning profile. This file does not create build authority.",
  });
}

function exportSelectedDesign() {
  const selected = state.result?.candidates.find(row => row.id === state.selectedId);
  if (!selected) return;
  downloadJson("worcester-board-design-" + selected.id + ".json", {
    schema_version: 1,
    profile: state.result.profile,
    requirements: state.result.requirements,
    selected_for_inspection: selected,
    visual_state: candidateVisualState(selected),
    winner_selected: false,
    authority: state.result.authority,
    source_snapshot_as_of: state.bundle.catalog.as_of,
    note:
      "Exported planning design. Selection is for inspection only and does not create procurement, fabrication, charging or powered-operation authority.",
  });
}

async function main() {
  try {
    state.bundle = await loadBundle();
    validateExampleRides(state.bundle.exampleRides,state.bundle.questionnaire,state.bundle.architectures);
    state.profile = restoreProfile(state.bundle.questionnaire);
    state.conversation = restoreRideConversation(
      localStorage.getItem(SESSION_KEY),state.profile,state.bundle.questionnaire);
    renderRideConversation();
    renderQuestionnaire();
    recompute();

    $("#ride-brief-review-button").addEventListener("click", reviewRideBrief);
    $("#ride-brief-clear-button").addEventListener("click", () => {
      $("#ride-brief-input").value = "";
      clearPendingRideReview("Draft cleared. Any pending suggestion was discarded.");
    });
    $("#ride-conversation-undo").addEventListener("click",undoLastConversationChange);
    $("#ride-conversation-export").addEventListener("click",() =>
      downloadJson("worcester-ride-conversation.json",exportRideConversation(state.conversation)));
    $("#ride-brief-input").addEventListener("keydown", event => {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") reviewRideBrief();
    });

    $("#detail-mode").addEventListener("click", () => {
      state.advanced = !state.advanced;
      $("#detail-mode").textContent = state.advanced ? "Hide advanced" : "Show advanced";
      renderQuestionnaire();
    });

    $("#reset-profile").addEventListener("click", () => {
      state.profile = questionnaireDefaults(state.bundle.questionnaire);
      state.conversation = createRideConversation(state.profile,state.bundle.questionnaire);
      state.rideBriefReview=null;state.sessionOutOfSync=false;
      state.originalProfileBeforeExamples=null;state.originalConversationBeforeExamples=null;
      state.activeExampleId=null;
      state.conversationStatus="Specifications and conversation reset.";
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(SESSION_KEY);
      renderRideBriefReview();renderRideConversation();
      state.selectedId = null;
      renderQuestionnaire();
      recompute();
    });

    $("#export-feasibility").addEventListener("click",()=>{
      if(state.result?.feasibility_report)
        downloadJson("worcester-feasibility-receipts.json",state.result.feasibility_report);
    });
    $("#export-build-passport").addEventListener("click",()=>{
      const passport=currentBuildPassport();
      if(passport)downloadJson("worcester-build-passport-"+passport.candidate_id+".json",passport);
    });
    $("#print-build-passport").addEventListener("click",()=>{
      if(!currentBuildPassport())return;
      document.body.classList.add("printing-build-passport");
      window.print();
    });
    window.addEventListener("afterprint",()=>document.body.classList.remove("printing-build-passport"));
    $("#export-profile").addEventListener("click", exportProfile);
    $("#export-design").addEventListener("click", exportSelectedDesign);
    $("#reset-swaps").addEventListener("click", resetSwaps);
    $("#export-custom-design").addEventListener("click", exportCustomDesign);
    $("#restore-personal-profile").addEventListener("click",restorePersonalProfile);
    $("#compare-reset").addEventListener("click",()=>{
      state.comparisonIds=defaultComparisonIds(state.result.candidates);
      state.comparisonInitialized=true;
      renderCandidates(state.result.candidates);renderComparison();
    });
    $("#compare-export").addEventListener("click",exportComparison);
    $("#export-assembly-guide").addEventListener("click",exportAssemblyGuide);
    $("#compare-a").addEventListener("change",e=>setComparisonSlot(0,e.target.value));
    $("#compare-b").addEventListener("change",e=>setComparisonSlot(1,e.target.value));
    document.querySelectorAll("[data-gallery-view]").forEach(button => {
      button.addEventListener("click", () => setGalleryView(button.dataset.galleryView));
    });
    document.querySelectorAll("[data-origin-filter]").forEach(button => {
      button.addEventListener("click", () => {
        state.originFilter = button.dataset.originFilter;
        document.querySelectorAll("[data-origin-filter]").forEach(row => {
          row.classList.toggle("active", row.dataset.originFilter === state.originFilter);
        });
        renderVendorFilters(state.result.candidates);
        renderCandidates(state.result.candidates);
      });
    });
  } catch (error) {
    console.error(error);
    $("#questionnaire").innerHTML = '<div class="note warning">Board Builder failed to load: ' + escapeHtml(error.message) + '</div>';
    $("#recompute-status").textContent = "Load failed";
  }
}

main();
