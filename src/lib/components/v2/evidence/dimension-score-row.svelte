<script lang="ts">
  import type { V2CombinedDimension, V2CommunityDimension, V2DimensionValue } from "$lib/types/v2";
  import { adequacy, articleAdequacy, tension, type Adequacy, type Tension } from "$lib/v2/derive";
  import SourceTensionAxis from "./source-tension-axis.svelte";
  interface Props { name: string; article: V2DimensionValue; community: V2CommunityDimension | null; combined: V2CombinedDimension; divergence: number | null; }
  let { name, article, community, combined, divergence }: Props = $props();
  const rowAdequacy = $derived<Adequacy>(community ? adequacy(community) : articleAdequacy(article));
  const rowTension = $derived<Tension>(tension(article.score, community?.score ?? null, divergence));
  const combinedLabel = $derived(combined.score === null ? "N/A" : `${combined.score >= 0 ? "+" : ""}${combined.score.toFixed(2)}`);
</script>

<div class="v2-score-row">
  <header>
    <strong>{name}</strong>
    <span>COMBINED {combinedLabel}</span>
    <span class="v2-score-row__flag" data-tension={rowTension}>{rowTension}</span>
    <span class="v2-score-row__adequacy" data-adequacy={rowAdequacy}>{rowAdequacy}</span>
  </header>
  <SourceTensionAxis article={article.score} community={community?.score ?? null} articleConfidence={article.confidence} communityConfidence={community?.confidence ?? 0} />
</div>
