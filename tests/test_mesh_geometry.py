from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tempfile
import trimesh
from fit.mesh_geometry import analyze

def test_ellipsoid_mesh_geometry():
    mesh=trimesh.creation.icosphere(subdivisions=3, radius=1.0)
    mesh.apply_scale([100,50,500])
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/"ellipsoid.ply"; mesh.export(p)
        out=analyze(p,1.0)
        assert 900 < out["height_mm"] <= 1000
        assert 180 < out["overall_width_mm"] <= 200
