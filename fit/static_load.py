#!/usr/bin/env python3
"""Summarize a four-zone stance calibration without prescribing steering changes."""
SENSORS=("left_heel","left_forefoot","right_heel","right_forefoot")

def summarize(rows):
    valid=[]
    for r in rows:
        vals={k:float(r[k]) for k in SENSORS}
        total=sum(vals.values())
        if total>1e-6: valid.append(vals)
    if not valid: raise ValueError("No positive-load samples")
    means={k:sum(r[k] for r in valid)/len(valid) for k in SENSORS}
    total=sum(means.values())
    left=means["left_heel"]+means["left_forefoot"]
    right=means["right_heel"]+means["right_forefoot"]
    return {
      "samples":len(valid),
      "left_load_fraction":left/total,
      "right_load_fraction":right/total,
      "left_forefoot_fraction":means["left_forefoot"]/left if left else None,
      "right_forefoot_fraction":means["right_forefoot"]/right if right else None,
      "sensor_means":means
    }
