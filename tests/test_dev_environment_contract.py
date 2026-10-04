from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_python_version_hint_matches_ci():
    assert (ROOT / ".python-version").read_text().strip() == "3.12"
    workflow = (ROOT / ".github" / "workflows" / "validate.yml").read_text()
    assert "python-version: '3.12'" in workflow


def test_ci_consumes_shared_pinned_requirements():
    workflow = (ROOT / ".github" / "workflows" / "validate.yml").read_text()

    assert "python -m pip install -r requirements-dev.txt" in workflow
    assert "python tools/check_dev_environment.py --ci" in workflow
    assert "python -m pip install pytest trimesh numpy platformio cadquery" not in workflow


def test_local_helpers_are_ci_syntax_checked():
    workflow = (ROOT / ".github" / "workflows" / "validate.yml").read_text()

    assert "bash -n tools/bootstrap_dev_env.sh" in workflow
    assert "bash -n tools/validate_local_dev.sh" in workflow
