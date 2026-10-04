from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "showcase" / "index.html").read_text()
APP = (ROOT / "showcase" / "app.js").read_text()


def test_camera_toolbar_exposes_centered_engineering_views():
    for view in ("hero", "top", "side", "front", "rear"):
        assert f'data-camera-view="{view}"' in HTML

    assert 'data-camera-rotate="-1"' in HTML
    assert 'data-camera-rotate="1"' in HTML
    assert 'id="camera-center"' in HTML


def test_orbit_controls_keep_board_center_target():
    assert "controls.enablePan = false;" in APP
    assert "controls.target.copy(center);" in APP
    assert "visual.cameraCenter.copy(center);" in APP


def test_camera_fit_uses_both_horizontal_and_vertical_fov():
    assert "fitDistanceForBounds" in APP
    assert "tanVertical" in APP
    assert "tanHorizontal" in APP
    assert "camera.aspect" in APP


def test_top_view_has_dedicated_up_vector_for_screen_rotation():
    assert 'top: new THREE.Vector3(0, 0, 1)' in APP
    assert 'new THREE.Vector3(0, 1, 0).applyAxisAngle' in APP
    assert "visual.cameraQuarterTurns * Math.PI / 2" in APP


def test_configuration_changes_schedule_camera_reframe():
    assert APP.count("scheduleReframe();") >= 3
    assert 'window.addEventListener("resize", resize);' in APP
