#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fit.profile_schema import RiderProfile
from fit.stance_optimizer import recommend


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("profile", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    args=ap.parse_args()
    profile=RiderProfile.from_dict(json.loads(args.profile.read_text()))
    errors=profile.validate()
    result={
        "profile_valid": not errors,
        "validation_errors": errors,
        "system_mass_kg": profile.system_mass_kg,
        "measurement_gaps": profile.measurement_gaps(),
        "fit_rig": recommend(profile).to_dict(),
    }
    text=json.dumps(result, indent=2)+"\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    print(text, end="")

if __name__ == "__main__":
    main()
