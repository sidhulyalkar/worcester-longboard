from pathlib import Path

from tools.check_dev_environment import (
    environment_shape,
    looks_like_conda_path,
    parse_pinned_requirements,
)


def test_requirements_are_exactly_pinned():
    pins = parse_pinned_requirements()

    assert pins["pytest"] == "9.1.1"
    assert pins["trimesh"] == "5.1.1"
    assert pins["numpy"] == "2.5.3"
    assert pins["platformio"] == "6.2.0"
    assert pins["cadquery"] == "2.8.0"
    assert pins["cadquery-ocp"] == "7.9.3.1.1"
    assert pins["cadquery-ocp-proxy"] == "7.9.3.1.1"


def test_conda_path_detection_handles_common_distributions():
    assert looks_like_conda_path("/opt/miniconda3")
    assert looks_like_conda_path("/Users/example/miniforge3")
    assert looks_like_conda_path("/Users/example/mambaforge")
    assert not looks_like_conda_path("/opt/homebrew/opt/python@3.12")


def test_environment_shape_accepts_repo_local_non_conda_venv(tmp_path: Path):
    root = tmp_path / "repo"
    prefix = root / ".venv"
    shape = environment_shape(
        prefix=prefix,
        base_prefix="/opt/homebrew/Frameworks/Python.framework/Versions/3.12",
        executable=prefix / "bin" / "python",
        conda_prefix=None,
        repo_root=root,
    )

    assert shape["active_venv"] is True
    assert shape["repo_local_venv"] is True
    assert shape["active_conda_environment"] is False
    assert shape["conda_underlay"] is False


def test_environment_shape_flags_conda_underlay_even_when_repo_venv_is_active(
    tmp_path: Path,
):
    root = tmp_path / "repo"
    prefix = root / ".venv"
    shape = environment_shape(
        prefix=prefix,
        base_prefix="/opt/miniconda3",
        executable=prefix / "bin" / "python",
        conda_prefix=None,
        repo_root=root,
    )

    assert shape["repo_local_venv"] is True
    assert shape["active_conda_environment"] is False
    assert shape["conda_underlay"] is True


def test_environment_shape_flags_active_conda_layer(tmp_path: Path):
    root = tmp_path / "repo"
    prefix = root / ".venv"
    shape = environment_shape(
        prefix=prefix,
        base_prefix="/opt/homebrew/Frameworks/Python.framework/Versions/3.12",
        executable=prefix / "bin" / "python",
        conda_prefix="/opt/miniconda3",
        repo_root=root,
    )

    assert shape["active_conda_environment"] is True
