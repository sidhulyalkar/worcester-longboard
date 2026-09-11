from __future__ import annotations

from dataclasses import dataclass, asdict
from statistics import mean, pstdev
from typing import Iterable, Mapping

SENSORS=("left_heel","left_forefoot","right_heel","right_forefoot")


@dataclass
class LoadSummary:
    samples: int
    mean_total_load: float
    left_fraction: float
    right_fraction: float
    left_forefoot_fraction: float | None
    right_forefoot_fraction: float | None
    left_right_std: float
    repeatability_ok: bool

    def to_dict(self):
        return asdict(self)


def summarize_trials(rows: Iterable[Mapping[str, float]], max_fraction_std: float = 0.04) -> LoadSummary:
    valid=[]
    left_fracs=[]
    for row in rows:
        vals={k: float(row[k]) for k in SENSORS}
        total=sum(vals.values())
        if total <= 1e-6:
            continue
        left=vals["left_heel"]+vals["left_forefoot"]
        valid.append(vals)
        left_fracs.append(left/total)
    if not valid:
        raise ValueError("No positive-load samples")

    means={k: mean([r[k] for r in valid]) for k in SENSORS}
    total=sum(means.values())
    left=means["left_heel"]+means["left_forefoot"]
    right=means["right_heel"]+means["right_forefoot"]
    lr_std=pstdev(left_fracs) if len(left_fracs)>1 else 0.0

    return LoadSummary(
        samples=len(valid),
        mean_total_load=total,
        left_fraction=left/total,
        right_fraction=right/total,
        left_forefoot_fraction=means["left_forefoot"]/left if left else None,
        right_forefoot_fraction=means["right_forefoot"]/right if right else None,
        left_right_std=lr_std,
        repeatability_ok=lr_std <= max_fraction_std,
    )
