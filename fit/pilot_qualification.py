"""One-zone load-cell qualification for the unpowered X1 Fit Rig."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from statistics import fmean, pstdev
from fit.raw_log import CHANNELS, parse_text

G = 9.80665
LIMITS = {
    "min_duration_s": 5.0, "min_coverage": 0.98, "min_r2": 0.999,
    "max_residual_fs": 0.01, "max_hysteresis_fs": 0.015,
    "max_zero_return_fs": 0.005, "max_validation_error": 0.02,
    "max_noise_fs": 0.005, "min_loaded_gap_mm": 0.15,
    "min_unloaded_gap_mm": 0.30, "max_unloaded_gap_mm": 2.00,
}

def _sha(path: Path) -> str:
    h=hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest()

def _digest(obj: dict) -> str:
    b=json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    return hashlib.sha256(b).hexdigest()

def _plateau(path: Path, channel: str, kind: str, mass: float) -> dict:
    rows=parse_text(path.read_text(encoding="utf-8"))
    if not rows: raise ValueError(f"{path}: empty log")
    try: idx=CHANNELS.index(channel)
    except ValueError as e: raise ValueError(f"unknown channel {channel!r}") from e
    vals=[r.raw[idx] for r in rows if (r.load_valid_mask&(1<<idx)) and r.raw[idx] is not None]
    if not vals: raise ValueError(f"{path}: no valid {channel} samples")
    return {
        "kind":kind,"mass_kg":float(mass),"force_n":float(mass)*G,"path":str(path),
        "mean":fmean(vals),"std":pstdev(vals),"coverage":len(vals)/len(rows),
        "duration_s":max(0,(rows[-1].t_us-rows[0].t_us)/1e6),
        "monotonic":all(b.t_us>a.t_us for a,b in zip(rows,rows[1:])),"sha256":_sha(path),
    }

def _fit(points: list[dict]) -> dict:
    xs=[p["force_n"] for p in points]; ys=[p["mean"] for p in points]
    xb,yb=fmean(xs),fmean(ys); sxx=sum((x-xb)**2 for x in xs)
    if sxx<=0: raise ValueError("calibration points must span force")
    slope=sum((x-xb)*(y-yb) for x,y in zip(xs,ys))/sxx
    if abs(slope)<1e-12: raise ValueError("zero calibration slope")
    intercept=yb-slope*xb
    ssr=sum((y-(intercept+slope*x))**2 for x,y in zip(xs,ys)); sst=sum((y-yb)**2 for y in ys)
    return {"intercept":intercept,"counts_per_n":slope,"r2":1.0 if sst==0 else 1-ssr/sst}

def _force(raw: float, fit: dict) -> float:
    return (raw-fit["intercept"])/fit["counts_per_n"]

def qualify_manifest(path: Path) -> dict:
    path=Path(path).resolve(); m=json.loads(path.read_text()); base=path.parent
    if m.get("schema_version")!=1: raise ValueError("schema_version must be 1")
    limits=dict(LIMITS); limits.update(m.get("thresholds",{})); channel=m["channel"]
    obs=[_plateau(base/x["log"],channel,x["kind"],x["mass_kg"]) for x in m.get("observations",[])]
    val=[_plateau(base/x["log"],channel,"validation",x["mass_kg"]) for x in m.get("validation",[])]
    pre=[p for p in obs if p["kind"]=="zero_pre" and p["mass_kg"]==0]
    post=[p for p in obs if p["kind"]=="zero_post" and p["mass_kg"]==0]
    up=[p for p in obs if p["kind"]=="load_up" and p["mass_kg"]>0]
    down=[p for p in obs if p["kind"]=="load_down" and p["mass_kg"]>0]
    fails=[]; paired=sorted({p["mass_kg"] for p in up}&{p["mass_kg"] for p in down})
    if not pre: fails.append("missing zero_pre")
    if not post: fails.append("missing zero_post")
    if len({p["mass_kg"] for p in up})<3: fails.append("need >=3 ascending masses")
    if len(paired)<2: fails.append("need >=2 paired masses for hysteresis")
    if not val: fails.append("need independent validation mass")
    for p in obs+val:
        if p["duration_s"]<limits["min_duration_s"]: fails.append(f'{p["path"]}: short plateau')
        if p["coverage"]<limits["min_coverage"]: fails.append(f'{p["path"]}: low coverage')
        if not p["monotonic"]: fails.append(f'{p["path"]}: non-monotonic timestamps')
    metrics={k:None for k in ("r2","residual_fs","hysteresis_fs","zero_return_fs","validation_error","noise_fs")}
    fit=None; fs=max((p["force_n"] for p in up),default=0)
    if pre and up and fs>0:
        fit=_fit(pre[:1]+up); metrics["r2"]=fit["r2"]
        metrics["residual_fs"]=max(abs(_force(p["mean"],fit)-p["force_n"])/fs for p in pre[:1]+up)
        metrics["noise_fs"]=max((p["std"]/abs(fit["counts_per_n"]))/fs for p in obs+val)
        if paired:
            metrics["hysteresis_fs"]=max(abs(fmean(_force(p["mean"],fit) for p in up if p["mass_kg"]==x)-fmean(_force(p["mean"],fit) for p in down if p["mass_kg"]==x))/fs for x in paired)
        if post:
            metrics["zero_return_fs"]=abs(_force(fmean(p["mean"] for p in post),fit)-_force(fmean(p["mean"] for p in pre),fit))/fs
        if val:
            metrics["validation_error"]=max(abs(_force(p["mean"],fit)-p["force_n"])/p["force_n"] for p in val if p["force_n"]>0)
        checks=[("r2",">=","min_r2"),("residual_fs","<=","max_residual_fs"),("hysteresis_fs","<=","max_hysteresis_fs"),("zero_return_fs","<=","max_zero_return_fs"),("validation_error","<=","max_validation_error"),("noise_fs","<=","max_noise_fs")]
        for name,op,lim in checks:
            v=metrics[name]
            if v is None: fails.append(f"{name} unavailable")
            elif op==">=" and v<limits[lim]: fails.append(f"{name} below limit")
            elif op=="<=" and v>limits[lim]: fails.append(f"{name} above limit")
    mech=m.get("mechanical",{})
    for k in ("vendor_pattern_verified","fixed_loaded_orientation_verified","screw_stack_verified"):
        if mech.get(k) is not True: fails.append(f"mechanical.{k} must be true")
    ug,lg=mech.get("stop_gap_unloaded_mm"),mech.get("stop_gap_min_loaded_mm")
    if ug is None or not limits["min_unloaded_gap_mm"]<=float(ug)<=limits["max_unloaded_gap_mm"]: fails.append("unloaded stop gap invalid")
    if lg is None or float(lg)<limits["min_loaded_gap_mm"]: fails.append("loaded stop gap invalid")
    if ug is not None and lg is not None and float(lg)>float(ug): fails.append("loaded gap exceeds unloaded gap")
    sources={str(Path(p["path"]).resolve().relative_to(base)) : p["sha256"] for p in obs+val}
    report={"schema_version":1,"authority":"x1_one_zone_pilot","scope":"unpowered_fit_rig_only","channel":channel,"hx711_sps":m.get("hx711_sps"),"thresholds":limits,"metrics":metrics,"linear_fit":fit,"mechanical":mech,"source_fingerprints":sources,"manifest_sha256":_sha(path),"failures":sorted(set(fails)),"qualified_for_four_zone_duplication":not fails}
    report["authority_fingerprint_sha256"]=_digest(report); return report
