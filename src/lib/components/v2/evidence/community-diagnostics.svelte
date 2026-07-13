<script lang="ts">
  import type { V2CommunityDimension } from "$lib/types/v2";
  interface Props { dimension: V2CommunityDimension; }
  let { dimension }: Props = $props();
  const adequacy = $derived(dimension.applicability === "not_addressed" ? "NONE" : dimension.effectiveSampleSize >= 12 && dimension.applicableBranchCount >= 6 ? "ROBUST" : dimension.effectiveSampleSize >= 6 ? "USABLE" : "THIN");
</script>

<div class="v2-diagnostics">
  <section><h4>Estimate</h4><dl><div><dt>Visibility weighted</dt><dd>{dimension.visibilityWeightedScore?.toFixed(3) ?? "N/A"}</dd></div><div><dt>Diversity balanced</dt><dd>{dimension.diversityBalancedScore?.toFixed(3) ?? "N/A"}</dd></div><div><dt>Ranking sensitivity</dt><dd>{dimension.rankingSensitivity?.toFixed(3) ?? "N/A"}</dd></div></dl></section>
  <section><h4>Distribution</h4><div class="v2-distribution" aria-label={`Positive ${dimension.positiveShare.toFixed(2)}, neutral ${dimension.neutralShare.toFixed(2)}, negative ${dimension.negativeShare.toFixed(2)}`}><i style={`width:${dimension.negativeShare * 100}%`}></i><i style={`width:${dimension.neutralShare * 100}%`}></i><i style={`width:${dimension.positiveShare * 100}%`}></i></div><dl><div><dt>Positive / neutral / negative</dt><dd>{dimension.positiveShare.toFixed(2)} / {dimension.neutralShare.toFixed(2)} / {dimension.negativeShare.toFixed(2)}</dd></div><div><dt>Disagreement</dt><dd>{dimension.disagreement?.toFixed(3) ?? "N/A"}</dd></div><div><dt>Polarization</dt><dd>{dimension.polarization.toFixed(3)}</dd></div></dl></section>
  <section><h4>Adequacy · {adequacy}</h4><dl><div><dt>Sample</dt><dd>ESS {dimension.effectiveSampleSize.toFixed(1)} / 12 target</dd></div><div><dt>Input</dt><dd>{dimension.applicableCommentCount} applicable</dd></div><div><dt>Spread</dt><dd>{dimension.applicableAuthorCount} authors / {dimension.applicableBranchCount} branches</dd></div><div><dt>Coverage / clarity</dt><dd>{dimension.dimensionCoverage.toFixed(2)} / {dimension.clarity.toFixed(2)}</dd></div></dl></section>
</div>
