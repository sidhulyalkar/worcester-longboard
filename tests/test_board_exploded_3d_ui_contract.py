"""Static accessibility/safety contracts for the optional assembly 3D explorer."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "builder/index.html").read_text()
APP = (ROOT / "builder/app.js").read_text()
CSS = (ROOT / "builder/styles.css").read_text()
VIEWER = (ROOT / "builder/exploded_3d_viewer.mjs").read_text()
MODEL = (ROOT / "builder/exploded_scene_model.mjs").read_text()

def test_opt_in_3d_keeps_svg_and_keyboard_tree():
    for tag in ('id="exploded-mode-2d"', 'id="exploded-mode-3d"',
                'id="exploded-visual"', 'id="exploded-visual-3d"',
                'id="exploded-tree"', 'id="exploded-camera-controls"'):
        assert tag in HTML
    assert 'aria-pressed="true"' in HTML
    assert "ensureExploded3D" in APP
    assert 'import("./exploded_3d_viewer.mjs")' in APP
    assert 'state.explodedDisplayMode==="3d"' in APP
    assert 'setExplodedMode("2d")' in APP
    assert "ResizeObserver" in VIEWER
    assert "onSelect(item.userData.partId)" in VIEWER
    assert "requestAnimationFrame" in VIEWER
    assert "@media print" in CSS and ".exploded-visual[hidden]" in CSS

def test_3d_never_implicitly_claims_dimensions_or_release():
    assert "ARBITRARY_VISUAL_UNITS" in MODEL
    assert "UNSCALED_SEMANTIC_PROXY_NOT_DIMENSIONAL_CAD" in MODEL
    assert "physical_release_authorized:false" in MODEL
    assert "exact_geometry_verified:false" in MODEL
    assert "planExplodedScene" in VIEWER

def test_sport_fit_intake_is_independent_research_not_checkout():
    for tag in ('id="sport-fit-lab"', 'id="fit-left"', 'id="fit-right"',
                'id="fit-sport"', 'id="fit-run"', 'id="fit-results"',
                'id="fit-export"'):
        assert tag in HTML
    assert "assessBoardSportFit" in APP
    assert "state.sportFitReport" in APP
    assert 'sport-fit-grid[hidden]' in CSS
    assert "This does not choose a safe binding" in HTML
