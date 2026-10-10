from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "builder" / "index.html").read_text()
APP = (ROOT / "builder" / "app.js").read_text()
TWIN = (ROOT / "showcase" / "app.js").read_text()


def test_builder_exposes_progressive_intake_trade_space_and_bom():
    assert 'id="questionnaire"' in HTML
    assert 'id="detail-mode"' in HTML
    assert 'id="requirements"' in HTML
    assert 'id="candidates"' in HTML
    assert 'id="bom-body"' in HTML
    assert "No automatic winner" in HTML


def test_builder_keeps_profile_local_until_explicit_export():
    assert "localStorage" in APP
    assert 'id="export-profile"' in HTML
    assert "Profile answers stay in this browser unless you explicitly export them." in HTML
    assert "fetch(" not in APP.split("async function loadBundle()", 1)[1].split("function restoreProfile", 1)[0].replace("fetchJson", "")


def test_vendor_links_are_source_links_not_generic_buy_buttons():
    assert "Vendor source" in APP
    assert "sourceEvidenceHtml" in APP
    assert "verified_as_of" in APP
    assert "not stock confirmation" in APP
    assert "hold_reason" in APP
    assert "POWER_GATED" in APP
    assert ">Buy<" not in HTML


def test_builder_candidate_deep_links_personalized_stance_into_twin():
    assert 'function twinUrl(candidate)' in APP
    assert 'params.set("stance_mm"' in APP
    assert 'new URLSearchParams(window.location.search)' in TWIN
    assert 'params.get("preset")' in TWIN
    assert 'params.get("candidate")' in TWIN
    assert 'params.get("stance_mm")' in TWIN
    assert 'setSnowdeckControls({ stance_mm: requestedStanceMm })' in TWIN


def test_builder_never_renders_authority_as_checkout_permission():
    assert "Planning tool, not a build permit." in HTML
    assert "cannot qualify structure" in HTML
    assert "generic_builder_may_promote_x1_authority: false" in (ROOT / "builder" / "engine.mjs").read_text()


def test_builder_can_export_selected_design_with_authority_boundary():
    assert 'id="export-design"' in HTML
    assert "function exportSelectedDesign()" in APP
    assert "selected_for_inspection" in APP
    assert "winner_selected: false" in APP


def test_swap_lab_is_visible_and_uses_explicit_non_authoritative_controls():
    assert 'id="swap-lab"' in HTML
    assert 'id="swap-controls"' in HTML
    assert 'id="reset-swaps"' in HTML
    assert 'id="export-custom-design"' in HTML
    assert 'id="open-custom-twin"' in HTML
    assert "Change one component and see what breaks." in HTML
    assert "evaluateSwap" in APP
    assert "seedSwapSelection" in APP


def test_swap_lab_deep_link_can_override_twin_geometry_and_layers():
    assert 'params.set("deck"' not in APP  # deck is included in URLSearchParams constructor
    assert 'deck: twin.deck_candidate_id' in APP
    assert 'topology: twin.topology_id' in APP
    assert 'params.set(layer, visible ? "1" : "0")' in APP
    assert 'params.get("deck")' in TWIN
    assert 'params.get("topology")' in TWIN
    assert 'setLayerVisibility(layerId, visible)' in TWIN


def test_custom_design_export_retains_authority_boundary():
    assert "function exportCustomDesign()" in APP
    assert "custom_study" in APP
    assert "does not create procurement, fabrication, charging or powered-operation authority" in APP


def test_generated_candidates_are_visual_first_and_share_view_controls():
    assert "03 / Visual build gallery" in HTML
    assert 'id="gallery-view-controls"' in HTML
    assert 'data-gallery-view="hero"' in HTML
    assert 'data-gallery-view="top"' in HTML
    assert 'data-gallery-view="side"' in HTML
    assert "renderCandidateVisual" in APP
    assert "renderBoardPreviewSvg" in APP
    assert "visualStateFromCandidate" in APP


def test_candidate_preview_and_twin_use_same_layer_state():
    assert "function candidateVisualState(candidate)" in APP
    assert "const visual = candidateVisualState(candidate);" in APP
    assert 'params.set(layer, visible ? "1" : "0")' in APP
    assert "visual.deck.id" in APP
    assert "visual.topology.id" in APP


def test_swap_lab_preview_regenerates_from_custom_design_state():
    assert 'id="swap-preview"' in HTML
    assert "function renderSwapPreview(candidate)" in APP
    assert "visualStateFromSwap" in APP
    assert "renderSwapPreview(candidate);" in APP


def test_visual_exports_are_svg_and_design_exports_include_visual_state():
    renderer = (ROOT / "builder" / "preview_renderer.mjs").read_text()
    assert "downloadBoardPreviewSvg" in APP
    assert 'data-download-preview="' in APP
    assert "visual_state: candidateVisualState(selected)" in APP
    assert "visual_state: visualStateFromSwap(" in APP
    assert 'type: "image/svg+xml;charset=utf-8"' in renderer


def test_visual_handoff_carries_catalog_wheel_study_into_twin():
    assert 'wheel: visual.wheel.study_id' in APP
    assert 'params.get("wheel")' in TWIN
    assert 'function wheelStudyGeometry(id)' in TWIN
    assert 'function applyWheelStudy(id)' in TWIN
    assert 'visual.componentCatalog.get(id)' in TWIN
    assert 'category === "wheel"' in TWIN
    assert 'requestedWheelId === "none"' in TWIN


def test_multivendor_gallery_exposes_family_filters_and_generic_geometry():
    assert 'id="vendor-filters"' in HTML
    assert 'id="catalog-coverage"' in HTML
    assert 'state.vendorFilter' in APP
    assert 'row.vendor_family' in APP
    assert '../catalog/board_geometry.v1.json' in APP
    assert '../catalog/board_geometry.v1.json' in TWIN
    assert '../catalog/board_components.v1.json' in TWIN


def test_visual_handoff_preserves_brake_and_drive_family_into_twin():
    assert 'drive_type: visual.visual_style.drive_type' in APP
    assert 'brake_family: visual.visual_style.brake_family' in APP
    assert 'params.get("drive_type")' in TWIN
    assert 'params.get("brake_family")' in TWIN
    assert 'function applyDriveVisualType(type)' in TWIN
    assert 'function applyBrakeVisualFamily(family)' in TWIN


def test_twin_has_distinct_procedural_deck_and_truck_family_geometry():
    assert 'lacroix_asymmetric_flex' in TWIN
    assert 'parallel_kingpin' in TWIN
    assert 'precision_bushing_spring' in TWIN
    assert 'function applyTruckVisualFamily(truck, family)' in TWIN
    assert 'function replaceMeshGeometry(mesh, geometry, state)' in TWIN


def test_catalog_composer_is_visible_as_distinct_candidate_origin():
    assert "generateBoardDesignSpace" in APP
    assert '"catalog composed"' in APP
    assert '"curated reference"' in APP
    assert "composition_summary" in APP
    assert "How this board was composed" in APP


def test_composed_candidate_detail_exposes_selection_and_compatibility_counts():
    assert "candidate.composition.selection" in APP
    assert "candidate.composition.compatibility_states" in APP
    assert "candidate.composition.rationale" in APP


def test_builder_loads_bounded_composer_contract():
    assert 'fetchJson("../configurator/composer.v1.json")' in APP
    assert "composer" in APP


def test_gallery_can_filter_curated_and_composed_candidates():
    assert 'id="origin-filters"' in HTML
    assert 'data-origin-filter="CURATED"' in HTML
    assert 'data-origin-filter="SYNTHESIZED"' in HTML
    assert "state.originFilter" in APP
    assert "row.origin === state.originFilter" in APP


def test_builder_loads_and_surfaces_catalog_source_health_separately():
    assert '../catalog/catalog_health.v1.json' in APP
    assert 'function sourceHealth(componentId)' in APP
    assert 'function sourceEvidenceHtml(componentId)' in APP
    assert 'not stock confirmation' in APP
    assert 'source_fresh' in APP
    assert 'refresh_due' in APP


def test_source_health_does_not_replace_compatibility_or_procurement_state():
    assert 'candidate.readiness' in APP
    assert 'row.procurement_state' in APP
    assert 'sourceHealthLabel' in APP
    assert 'POWER_GATED' in APP
    assert 'Vendor source' in APP
    assert '>Buy<' not in HTML


def test_evidence_explorer_ui_exposes_measurement_traceability_not_checkout():
    assert 'id="evidence-explorer"' in HTML
    assert 'id="swap-evidence-explorer"' in HTML
    assert 'function evidencePanelHtml(report' in APP
    assert 'function exportEvidenceWorklist()' in APP
    assert 'function swapEvidence(candidate, result)' in APP
    assert 'measurement_worklist' in APP
    assert 'source_maintenance' in APP
    assert 'Fit score is a planning preference' in APP
    assert 'Export worklist' in APP
    assert 'authority: e.authority' in APP
    assert '>Buy<' not in HTML

def test_example_rides_comparison_and_assembly_onboarding():
    assert 'id="example-rides"' in HTML
    assert 'id="restore-personal-profile"' in HTML
    assert 'Start with a terrain' in HTML
    assert 'configurator/example_rides.v1.json' in APP
    assert 'function loadExampleRide(id)' in APP
    assert 'function restorePersonalProfile()' in APP
    assert 'id="compare-section"' in HTML
    assert 'id="compare-a"' in HTML and 'id="compare-b"' in HTML
    assert 'id="compare-export"' in HTML
    assert 'data-compare="' in APP and 'aria-pressed="' in APP
    assert 'compareCandidates' in APP
    assert 'renderBoardPreviewSvg(x.visual,state.galleryView' in APP
    assert 'id="assembly-guide"' in HTML
    assert 'id="export-assembly-guide"' in HTML
    assert 'assemblyGuide(candidate)' in APP
    assert 'No live electrical commissioning steps are provided' in APP
    assert 'CPSC battery/charger safety' in HTML
    assert '>Buy<' not in HTML


def test_ride_brief_is_review_first_and_has_explicit_apply_discard_controls():
    assert 'id="ride-brief-input"' in HTML
    assert 'id="ride-brief-review-button"' in HTML
    assert 'id="ride-brief-review"' in HTML
    assert "proposeRideConversationTurn" in APP
    assert "acceptRideConversationTurn" in APP
    assert "rejectRideConversationTurn" in APP
    assert "data-ride-group" in APP
    assert 'p.certainty === "EXPLICIT" ? " checked" : ""' in APP
    assert 'id="ride-brief-discard"' in APP
    assert "state.profile = {...state.conversation.profile}" in APP
    assert 'state.selectedId = null' in APP
    assert "No preview is a fabrication drawing" in APP
    assert ">Buy<" not in HTML


def test_reviewed_multiturn_ux_reconciles_manual_edits_and_keeps_authority_outside_chat():
    assert 'id="ride-conversation-history"' in HTML
    assert 'id="ride-conversation-status"' in HTML
    assert 'id="ride-conversation-undo"' in HTML
    assert 'id="ride-conversation-export"' in HTML
    assert 'role="status"' in HTML
    assert 'import {' in APP and 'from "./conversation_state.mjs"' in APP
    assert 'function reconcileQuestionnaire()' in APP
    assert 'reconcileManualRideProfile(' in APP
    assert 'onQuestionnaireInput()' in APP
    assert 'function clearPendingRideReview(' in APP
    assert 'function undoLastConversationChange()' in APP
    assert 'restoreRideConversation(' in APP
    assert 'exportRideConversation(' in APP
    assert 'if (state.sessionOutOfSync) throw new Error' in APP
    assert 'No preview is a fabrication drawing' in APP
    assert '>Buy<' not in HTML

def test_user_actions_retain_prior_profile_when_switching_example_rides():
    assert 'state.originalConversationBeforeExamples=exportRideConversation(state.conversation)' in APP
    assert 'state.conversation=state.originalConversationBeforeExamples' in APP
    assert 'state.conversation=createRideConversation(state.profile,state.bundle.questionnaire)' in APP
    assert 'state.originalProfileBeforeExamples=null' in APP


def test_diversity_shortlist_does_not_imply_authorized_build():
    assert 'id="shortlist-cards"' in HTML
    assert 'id="shortlist-status"' in HTML
    assert "buildDiverseShortlist" in (ROOT / "builder" / "platform_engine.mjs").read_text()
    assert "function renderDiverseShortlist()" in APP
    assert 'data-shortlist-inspect=' in APP
    assert "Studies, not approved builds" in HTML
    assert "not mechanical qualification or purchasing approval" in APP



def test_feasibility_receipts_are_visible_but_never_approval():
    assert 'id="feasibility-panel"' in HTML
    assert 'id="feasibility-records"' in HTML
    assert 'id="export-feasibility"' in HTML
    assert "function renderFeasibilityPanel()" in APP
    assert "state.result.feasibility_report" in APP
    assert "NOT QUALIFIED" in APP
    assert "No checkout, fabrication, charging or powered operation authorized." in APP
    assert "feasibility_report" in (ROOT / "builder" / "platform_engine.mjs").read_text()



def test_build_passport_is_revision_aware_not_an_unqualified_checkout():
    assert 'id="build-passport-section"' in HTML
    assert 'id="build-passport"' in HTML
    assert 'id="export-build-passport"' in HTML
    assert 'id="print-build-passport"' in HTML
    assert "function renderBuildPassport(candidate)" in APP
    assert "buildBuildPassport(selected,state.bundle)" in APP
    assert "proposePassportRevisionChange" in APP
    assert "UNKNOWN" in APP
    assert "No procurement, fabrication, charging or powered-operation authority." in APP
    assert "MANUFACTURER_INSTRUCTIONS_NOT_INDEXED" in (ROOT / "builder" / "build_passport.mjs").read_text()
    assert "UNKNOWN_NOT_LIVE" in (ROOT / "builder" / "build_passport.mjs").read_text()
    assert "INVALIDATED_BY_REVISION_CHANGE" in (ROOT / "builder" / "build_passport.mjs").read_text()
    assert ">Buy<" not in HTML
