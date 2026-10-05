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
    assert "source_as_of" in APP
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


def test_visual_handoff_carries_wheel_study_into_twin():
    assert 'wheel: visual.wheel.study_id' in APP
    assert 'params.get("wheel")' in TWIN
    assert 'function applyWheelStudy(id)' in TWIN
    assert '"TIRE-T2-9"' in TWIN
    assert '"none"' in TWIN
