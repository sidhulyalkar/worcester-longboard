#!/usr/bin/env python3
"""Ensure exact maker-family mount findings agree in Python/JavaScript."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from configurator.snowboard_mount_reference import evaluate_snowboard_mount_reference

def main():
    items=json.loads(subprocess.check_output(
        ["node","tools/generate_snowboard_mount_checks.mjs"],cwd=ROOT,text=True))
    for index,item in enumerate(items):
        got=evaluate_snowboard_mount_reference(item["input"])
        assert got==item["output"], f"Burton family adapter mismatch {index}: {got} != {item['output']}"
        assert not got["physical_fit_verified"] and not got["install_authorized"]
        assert all(value is False for value in got["authority"].values())
    assert any(x["output"]["verdict"]=="MANUFACTURER_REFERENCE_INCOMPATIBLE" for x in items)
    assert any(x["output"]["verdict"]=="REQUIRED_SPECIAL_DISC_MISSING" for x in items)
    print(json.dumps({"mounting_reference_cases":len(items),
        "js_python_parity":"PASS","physical_install_authorizations":0},indent=2))

if __name__=="__main__":
    main()
