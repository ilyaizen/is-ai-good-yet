<script lang="ts">
  interface Props {
    article: number | null;
    community: number | null;
    articleConfidence: number;
    communityConfidence: number;
    divergence: number | null;
  }
  let { article, community, articleConfidence, communityConfidence, divergence }: Props = $props();
  const position = (value: number | null) => value === null ? 50 : ((Math.max(-2, Math.min(2, value)) + 2) / 4) * 100;
  const conflict = $derived(article !== null && community !== null && article * community < 0);
  const level = $derived(divergence === null ? "SOURCE MISSING" : conflict ? "OPPOSING DIRECTIONS" : divergence >= 2 ? "SOURCE CONFLICT" : divergence >= 1 ? "SOURCES DIVERGE" : divergence >= 0.5 ? "MILD TENSION" : "ALIGNED");
</script>

<div class="v2-axis" data-conflict={conflict}>
  <div class="v2-axis__labels"><span>−2</span><span>0</span><span>+2</span></div>
  <div class="v2-axis__line">
    {#if article !== null}<i class="v2-axis__marker v2-axis__marker--article" style={`left:${position(article)}%;opacity:${Math.max(.28, articleConfidence)}`} aria-hidden="true"></i>{/if}
    {#if community !== null}<i class="v2-axis__marker v2-axis__marker--community" style={`left:${position(community)}%;opacity:${Math.max(.28, communityConfidence)}`} aria-hidden="true"></i>{/if}
    {#if article !== null && community !== null}<i class="v2-axis__connector" style={`left:${Math.min(position(article), position(community))}%;width:${Math.abs(position(article) - position(community))}%`} aria-hidden="true"></i>{/if}
  </div>
  <div class="v2-axis__values"><span>ARTICLE {article === null ? "N/A" : `${article >= 0 ? "+" : ""}${article.toFixed(2)}`}</span><b>{level}</b><span>COMMUNITY {community === null ? "N/A" : `${community >= 0 ? "+" : ""}${community.toFixed(2)}`}</span></div>
</div>
