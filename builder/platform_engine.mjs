import { READINESS_RANK, generateCandidates } from "./engine.mjs";
import { composeCandidates } from "./composer.mjs";

function bomSignature(candidate) {
  return (candidate.bom || [])
    .map(row => row.component_id)
    .sort()
    .join("|");
}

function nonDominated(candidates) {
  const metrics = [
    "range",
    "carve",
    "stability",
    "durability",
    "portability",
    "cost",
    "low_maintenance",
  ];
  const frontier = new Set();
  for (const candidate of candidates) {
    let dominated = false;
    for (const other of candidates) {
      if (other === candidate) continue;
      const noWorse = metrics.every(
        metric => Number(other.traits?.[metric] ?? 0) >= Number(candidate.traits?.[metric] ?? 0)
      );
      const better = metrics.some(
        metric => Number(other.traits?.[metric] ?? 0) > Number(candidate.traits?.[metric] ?? 0)
      );
      if (noWorse && better) {
        dominated = true;
        break;
      }
    }
    if (!dominated) frontier.add(candidate.id);
  }
  return frontier;
}

export function generateBoardDesignSpace(profile, bundle) {
  const curated = generateCandidates(profile, bundle);
  for (const candidate of curated.candidates) {
    candidate.origin = "CURATED";
  }

  const synthesized = composeCandidates(
    curated.profile,
    curated.requirements,
    bundle
  );

  const curatedSignatures = new Set(curated.candidates.map(bomSignature));
  const uniqueSynthesized = synthesized.filter(
    candidate => !curatedSignatures.has(bomSignature(candidate))
  );

  const candidates = [...curated.candidates, ...uniqueSynthesized];
  candidates.sort(
    (a, b) =>
      b.fit_score - a.fit_score ||
      READINESS_RANK[a.readiness] - READINESS_RANK[b.readiness] ||
      a.label.localeCompare(b.label)
  );

  const frontier = nonDominated(candidates);
  for (const candidate of candidates) {
    candidate.trade_space_frontier = frontier.has(candidate.id);
  }

  return {
    ...curated,
    candidates,
    composition_summary: {
      schema_version: 1,
      curated_count: curated.candidates.length,
      synthesized_count: uniqueSynthesized.length,
      total_count: candidates.length,
      composer_enabled: Boolean(bundle.composer?.enabled),
      synthesized_candidate_cap: Number(
        bundle.composer?.max_synthesized_candidates || 0
      ),
    },
    authority: {
      ...curated.authority,
      generic_builder_may_promote_x1_authority: false,
      procurement_authorized: false,
      fabrication_authorized: false,
      powered_operation_authorized: false,
    },
  };
}
