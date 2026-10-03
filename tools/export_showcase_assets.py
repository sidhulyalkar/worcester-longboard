#!/usr/bin/env python3
"""Convert generated X1 STL references into local browser-ready GLB assets.

This tool changes file format only. It never promotes physical authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = [
    ROOT / "cad" / "generated_chassis",
    ROOT / "cad" / "generated_fit",
    ROOT / "cad" / "generated_one_zone_pilot",
    ROOT / "cad" / "generated_snowdeck_study",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def convert_stl(src: Path, dst: Path) -> dict:
    loaded = trimesh.load(src, force="scene")
    if isinstance(loaded, trimesh.Trimesh):
        scene = trimesh.Scene(loaded)
    else:
        scene = loaded
    dst.parent.mkdir(parents=True, exist_ok=True)
    payload = scene.export(file_type="glb")
    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError(f"{src}: GLB export did not return bytes")
    dst.write_bytes(payload)
    return {
        "asset_id": src.stem,
        "source_group": src.parent.name.replace("generated_", ""),
        "source": str(src.relative_to(ROOT)),
        "source_sha256": sha256_file(src),
        "asset": str(dst.relative_to(ROOT)),
        "asset_sha256": sha256_file(dst),
        "physical_authority": False,
        "powered_operation_authorized": False,
    }


def export_sources(source_dirs: list[Path], out_dir: Path) -> list[dict]:
    assets = []
    for source_dir in source_dirs:
        if not source_dir.exists():
            continue
        group = source_dir.name.replace("generated_", "")
        for src in sorted(source_dir.glob("*.stl")):
            dst = out_dir / group / (src.stem + ".glb")
            assets.append(convert_stl(src, dst))
    return assets


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--source",
        action="append",
        type=Path,
        default=[],
        help="Generated CAD directory containing STL files. May be repeated.",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "showcase" / "generated",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    sources = args.source or DEFAULT_SOURCES
    assets = export_sources(sources, args.out_dir)
    manifest = {
        "schema_version": 1,
        "scope": "x1_showcase_format_conversion_only",
        "physical_authority": False,
        "fabrication_authority": False,
        "powered_operation_authorized": False,
        "assets": assets,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.out_dir / "assets.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(assets)} GLB assets and {manifest_path}")


if __name__ == "__main__":
    main()
