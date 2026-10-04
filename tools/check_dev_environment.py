#!/usr/bin/env python3
"""Diagnose the Worcester X1 local Python development environment."""
from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "requirements-dev.txt"

IMPORT_MODULES = {
    "pytest": "pytest",
    "trimesh": "trimesh",
    "numpy": "numpy",
    "platformio": "platformio",
    "cadquery": "cadquery",
    "cadquery-ocp": "OCP",
}


def parse_pinned_requirements(path: Path = REQUIREMENTS) -> dict[str, str]:
    pins: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "==" not in line:
            raise ValueError(f"development requirement must be exactly pinned: {line}")
        name, version = line.split("==", 1)
        pins[name.strip().lower()] = version.strip()
    return pins


def looks_like_conda_path(value: str | Path | None) -> bool:
    if not value:
        return False
    text = str(value).lower()
    markers = ("conda", "miniconda", "anaconda", "miniforge", "mambaforge", "micromamba")
    return any(marker in text for marker in markers)


def environment_shape(
    *,
    prefix: str | Path,
    base_prefix: str | Path,
    executable: str | Path,
    conda_prefix: str | None,
    repo_root: Path = ROOT,
) -> dict[str, Any]:
    prefix_path = Path(prefix).resolve()
    base_path = Path(base_prefix).resolve()
    expected_venv = (repo_root / ".venv").resolve()
    active_venv = prefix_path != base_path
    return {
        "active_venv": active_venv,
        "repo_local_venv": active_venv and prefix_path == expected_venv,
        "active_conda_environment": bool(conda_prefix),
        "conda_underlay": looks_like_conda_path(base_path),
        "prefix": str(prefix_path),
        "base_prefix": str(base_path),
        "executable": str(Path(executable).resolve()),
        "expected_repo_venv": str(expected_venv),
    }


def collect_report(*, ci: bool = False, import_packages: bool = True) -> dict[str, Any]:
    pins = parse_pinned_requirements()
    shape = environment_shape(
        prefix=sys.prefix,
        base_prefix=sys.base_prefix,
        executable=sys.executable,
        conda_prefix=os.environ.get("CONDA_PREFIX"),
    )

    errors: list[str] = []
    warnings: list[str] = []
    packages: dict[str, dict[str, Any]] = {}

    if sys.version_info[:2] != (3, 12):
        errors.append(
            f"Python 3.12 is required; running "
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )

    if not ci:
        if not shape["active_venv"]:
            errors.append("No virtual environment is active.")
        elif not shape["repo_local_venv"]:
            errors.append("The active virtual environment is not this repository's .venv.")

        if shape["active_conda_environment"]:
            errors.append(
                "A Conda environment is active underneath the project environment. "
                "Run 'deactivate' and 'conda deactivate' before activating .venv."
            )

        if shape["conda_underlay"]:
            errors.append(
                "This .venv was created from a Conda-family base interpreter. "
                "Recreate it with a standalone/Homebrew Python 3.12 interpreter."
            )

    for distribution, expected in pins.items():
        try:
            installed = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            errors.append(f"Missing dependency: {distribution}=={expected}")
            packages[distribution] = {"expected": expected, "installed": None}
            continue
        packages[distribution] = {"expected": expected, "installed": installed}
        if installed != expected:
            errors.append(
                f"Version mismatch for {distribution}: expected {expected}, found {installed}"
            )

    if import_packages:
        for distribution, module in IMPORT_MODULES.items():
            if distribution not in packages or packages[distribution]["installed"] is None:
                continue
            try:
                importlib.import_module(module)
                packages[distribution]["import_ok"] = True
            except BaseException as exc:
                packages[distribution]["import_ok"] = False
                packages[distribution]["import_error"] = f"{type(exc).__name__}: {exc}"
                errors.append(
                    f"Import failed for {module} ({distribution}): "
                    f"{type(exc).__name__}: {exc}"
                )

    if not ci and shape["active_venv"] and not shape["conda_underlay"]:
        warnings.append(
            "Environment isolation looks clean. Keep Conda base deactivated while working in this repo."
        )

    return {
        "ok": not errors,
        "mode": "ci" if ci else "local",
        "python": {
            "version": sys.version.split()[0],
            "executable": shape["executable"],
            "prefix": shape["prefix"],
            "base_prefix": shape["base_prefix"],
        },
        "environment": shape,
        "packages": packages,
        "errors": errors,
        "warnings": warnings,
    }


def render(report: dict[str, Any]) -> str:
    lines = [
        "Worcester X1 development environment",
        "=" * 36,
        f"Python:      {report['python']['version']}",
        f"Executable:  {report['python']['executable']}",
        f"Prefix:      {report['python']['prefix']}",
        f"Base prefix: {report['python']['base_prefix']}",
        "",
        "Environment:",
        f"  repo .venv active: {report['environment']['repo_local_venv']}",
        f"  Conda active:       {report['environment']['active_conda_environment']}",
        f"  Conda underlay:     {report['environment']['conda_underlay']}",
        "",
        "Pinned packages:",
    ]
    for name, info in report["packages"].items():
        installed = info.get("installed") or "MISSING"
        import_suffix = ""
        if "import_ok" in info:
            import_suffix = " | import OK" if info["import_ok"] else " | IMPORT FAILED"
        lines.append(
            f"  {name}: {installed} (expected {info['expected']}){import_suffix}"
        )

    if report["warnings"]:
        lines += ["", "Notes:"]
        lines.extend(f"  - {message}" for message in report["warnings"])

    if report["errors"]:
        lines += ["", "Problems:"]
        lines.extend(f"  - {message}" for message in report["errors"])

    lines += ["", "RESULT: " + ("PASS" if report["ok"] else "FAIL")]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Validate versions/imports without requiring a repo-local .venv.",
    )
    parser.add_argument(
        "--skip-imports",
        action="store_true",
        help="Check interpreter and installed versions without importing native packages.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args()

    report = collect_report(ci=args.ci, import_packages=not args.skip_imports)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render(report))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
