<script lang="ts">
  import type { V2CombinedDimension, V2CommunityDimension, V2DimensionValue } from "$lib/types/v2";
  import SourceTensionAxis from "./source-tension-axis.svelte";
  interface Props { name: string; article: V2DimensionValue; community: V2CommunityDimension | null; combined: V2CombinedDimension; divergence: number | null; }
  let { name, article, community, combined, divergence }: Props = $props();
  const confidenceLabel = (value: number) => value >= .75 ? "HIGH" : value >= .45 ? "MED" : "LOW";
</script>

<div class="v2-score-row">
  <header><strong>{name}</strong><span>COMBINED {combined.score === null ? "N/A" : `${combined.score >= 0 ? "+" : ""}${combined.score.toFixed(2)}`}</span><span>CONF {confidenceLabel(combined.confidence)} {combined.confidence.toFixed(2)}</span></header>
  <SourceTensionAxis article={article.score} community={community?.score ?? null} articleConfidence={article.confidence} communityConfidence={community?.confidence ?? 0} {divergence} />
  <div class="v2-score-row__diagnostics">
    <span>DIVERGENCE {divergence?.toFixed(2) ?? "N/A"}</span>
    <span>DISAGREEMENT {community?.disagreement?.toFixed(2) ?? "N/A"}</span>
    <span>POLARIZATION {community?.polarization.toFixed(2) ?? "N/A"}</span>
    <span>ESS {community?.effectiveSampleSize.toFixed(1) ?? "N/A"}</span>
  </div>
</div>
