import importlib.util
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "export_showcase_assets", ROOT / "tools" / "export_showcase_assets.py"
)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mod)


def test_convert_stl_records_hashes_and_no_authority(tmp_path):
    src_dir = tmp_path / "generated_chassis"
    src_dir.mkdir()
    src = src_dir / "cube.stl"
    trimesh.creation.box(extents=(10, 20, 30)).export(src)

    old_root = mod.ROOT
    mod.ROOT = tmp_path
    try:
        dst = tmp_path / "showcase" / "generated" / "chassis" / "cube.glb"
        record = mod.convert_stl(src, dst)
    finally:
        mod.ROOT = old_root

    assert dst.exists()
    assert dst.stat().st_size > 0
    assert len(record["source_sha256"]) == 64
    assert len(record["asset_sha256"]) == 64
    assert record["physical_authority"] is False
    assert record["powered_operation_authorized"] is False


def test_missing_source_directories_are_safe(tmp_path):
    assets = mod.export_sources(
        [tmp_path / "does-not-exist"],
        tmp_path / "showcase" / "generated",
    )
    assert assets == []
