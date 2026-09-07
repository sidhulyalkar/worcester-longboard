#!/usr/bin/env python3
"""Reduce a locally stored rider mesh to coarse fit geometry.

The output is intentionally aggregate. It does not estimate mass distribution and
it does not modify steering parameters.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import trimesh

def extent(a, lo=0.5, hi=99.5):
    return float(np.percentile(a, hi)-np.percentile(a, lo))

def analyze(mesh_path: Path, scale_to_mm: float=1.0):
    mesh=trimesh.load_mesh(mesh_path, process=True)
    if isinstance(mesh,trimesh.Scene):
        mesh=trimesh.util.concatenate(tuple(mesh.geometry.values()))
    if not isinstance(mesh,trimesh.Trimesh) or len(mesh.vertices)<100:
        raise ValueError("Expected a usable triangle mesh")
    v=np.asarray(mesh.vertices,dtype=float)*scale_to_mm
    mins=np.percentile(v,0.5,axis=0); maxs=np.percentile(v,99.5,axis=0)
    cx=0.5*(mins[0]+maxs[0])
    x=v[:,0]-cx
    left=np.abs(x[x<0]); right=np.abs(x[x>=0])
    return {
      "schema_version":1,
      "units":"mm",
      "height_mm":extent(v[:,2]),
      "overall_width_mm":extent(v[:,0]),
      "overall_depth_mm":extent(v[:,1]),
      "left_extent_p95_mm":float(np.percentile(left,95)) if len(left) else 0.0,
      "right_extent_p95_mm":float(np.percentile(right,95)) if len(right) else 0.0,
      "mesh_vertices":int(len(v)),
      "watertight":bool(mesh.is_watertight),
      "note":"Geometric summary only; not a mass or force-distribution estimate."
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("mesh",type=Path)
    p.add_argument("--scale-to-mm",type=float,default=1.0)
    p.add_argument("--out",type=Path,default=Path("rider/private/mesh_geometry.json"))
    a=p.parse_args()
    result=analyze(a.mesh,a.scale_to_mm)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
if __name__=="__main__": main()
