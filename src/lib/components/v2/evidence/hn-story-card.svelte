<script lang="ts">
  import type { V2StoryCard } from "$lib/types/v2";
  import { V2_DIMENSIONS } from "$lib/types/v2";
  import { direction } from "$lib/v2/derive";
  import DimensionScoreRow from "./dimension-score-row.svelte";
  interface Props { story: V2StoryCard; visibleDimensions: Record<string, boolean>; }
  let { story, visibleDimensions }: Props = $props();
  const articleQuote = $derived(story.evidence[0] ?? null);
  const dissent = $derived(V2_DIMENSIONS.map((name) => story.community?.dimensions[name].dissent).find(Boolean) ?? null);
  const composite = $derived(story.combined.composite);
  const combinedVerdict = $derived(composite === null ? "N/A" : (direction(composite) ?? "MIXED"));
  const combinedLabel = $derived(composite === null ? "N/A" : `${composite >= 0 ? "+" : ""}${composite.toFixed(2)}`);
  // Source coverage state — never coerce a missing source into a zero verdict.
  const sourceState = $derived(
    story.community && story.community.analyzedCommentCount > 0
      ? "ARTICLE + COMMUNITY"
      : story.article.dimensions.capability.applicability !== "not_addressed" ||
          story.article.dimensions.trajectory.applicability !== "not_addressed" ||
          story.article.dimensions.impact.applicability !== "not_addressed"
        ? "ARTICLE ONLY"
        : "NOT YET ANALYZED"
  );
  const visibleDims = $derived(V2_DIMENSIONS.filter((dimension) => visibleDimensions[dimension]));
</script>

<article id={`hn-${story.hnId}`} class="v2-story-card">
  <header class="v2-story-card__header">
    <div>
      <p>{story.domain} · <time datetime={new Date(story.hnTimestamp * 1000).toISOString()}>{new Date(story.hnTimestamp * 1000).toLocaleDateString("en", { year: "numeric", month: "short", day: "2-digit" })}</time></p>
      <h3><a href={story.url} target="_blank" rel="noreferrer">{story.title}</a></h3>
      <ul class="v2-tags">{#each story.scopes as scope}<li>{scope}</li>{/each}</ul>
    </div>
    <dl>
      <div><dt>COMBINED</dt><dd><b data-direction={combinedVerdict.toLowerCase()}>{combinedVerdict}</b> {combinedLabel}</dd></div>
      <div><dt>HN</dt><dd>{story.hnScore} points · {story.hnComments} comments</dd></div>
      <div><dt>SOURCES</dt><dd>{sourceState}</dd></div>
    </dl>
  </header>
  <div class="v2-story-card__scores">
    {#each visibleDims as dimension}
      <DimensionScoreRow name={dimension.toUpperCase()} article={story.article.dimensions[dimension]} community={story.community?.dimensions[dimension] ?? null} combined={story.combined.dimensions[dimension]} divergence={story.sourceDivergence[dimension]} />
    {/each}
  </div>
  <div class="v2-evidence-quotes">
    <blockquote>
      <span>ARTICLE EVIDENCE</span>
      {#if articleQuote}
        <p>“{articleQuote.quote}”</p>
        <cite>{articleQuote.attribution.replace("_", " ")}</cite>
      {:else}
        <p>No exact article excerpt was exported.</p>
      {/if}
    </blockquote>
    <blockquote>
      <span>{dissent?.excerpt ? "HN COMMENT · DISSENT" : dissent ? "COMMENT SUMMARY · DISSENT" : "COMMUNITY"}</span>
      {#if dissent}
        <p>{dissent.excerpt ? `“${dissent.excerpt}”` : dissent.summary}</p>
        <cite><a href={`https://news.ycombinator.com/item?id=${dissent.commentId}`} target="_blank" rel="noreferrer">HN comment {dissent.commentId} ↗</a></cite>
      {:else if story.community?.summary}
        <p>{story.community.summary}</p>
      {:else}
        <p>Community analysis is not available for this story.</p>
      {/if}
    </blockquote>
  </div>
  {#if story.community}
    <details class="v2-story-details">
      <summary>COMMENT DISTRIBUTION</summary>
      <div class="v2-story-details__body">
        {#each visibleDims as dimension}
          {@const share = story.community?.dimensions[dimension]}
          {#if share && share.applicability !== "not_addressed"}
            <section>
              <h3>{dimension}</h3>
              <div class="v2-distribution" aria-label={`${dimension}: positive ${Math.round(share.positiveShare * 100)}%, neutral ${Math.round(share.neutralShare * 100)}%, negative ${Math.round(share.negativeShare * 100)}%`}>
                <i style={`width:${share.negativeShare * 100}%`}></i>
                <i style={`width:${share.neutralShare * 100}%`}></i>
                <i style={`width:${share.positiveShare * 100}%`}></i>
              </div>
              <small>+{Math.round(share.positiveShare * 100)}% · ={Math.round(share.neutralShare * 100)}% · −{Math.round(share.negativeShare * 100)}%</small>
            </section>
          {/if}
        {/each}
        <a class="v2-story-details__thread" href={`https://news.ycombinator.com/item?id=${story.hnId}`} target="_blank" rel="noreferrer">Open HN thread ↗</a>
      </div>
    </details>
  {/if}
</article>
