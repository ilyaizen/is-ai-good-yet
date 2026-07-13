<script lang="ts">
  import type { V2StoryCard } from "$lib/types/v2";
  import { V2_DIMENSIONS } from "$lib/types/v2";
  import DimensionScoreRow from "./dimension-score-row.svelte";
  import CommunityDiagnostics from "./community-diagnostics.svelte";
  interface Props { story: V2StoryCard; visibleDimensions: Record<string, boolean>; }
  let { story, visibleDimensions }: Props = $props();
  const articleQuote = $derived(story.evidence[0] ?? null);
  const dissent = $derived(V2_DIMENSIONS.map((name) => story.community?.dimensions[name].dissent).find(Boolean) ?? null);
  const combinedLabel = $derived(story.combined.composite === null ? "N/A" : `${story.combined.composite >= 0 ? "+" : ""}${story.combined.composite.toFixed(2)}`);
</script>

<article id={`hn-${story.hnId}`} class="v2-story-card">
  <header class="v2-story-card__header">
    <div><p>{story.domain} · <time datetime={new Date(story.hnTimestamp * 1000).toISOString()}>{new Date(story.hnTimestamp * 1000).toLocaleDateString("en", { year: "numeric", month: "short", day: "2-digit" })}</time></p><h3><a href={story.url} target="_blank" rel="noreferrer">{story.title}</a></h3><ul class="v2-tags">{#each story.scopes as scope}<li>{scope}</li>{/each}</ul></div>
    <dl><div><dt>COMBINED</dt><dd>{combinedLabel}</dd></div><div><dt>HN</dt><dd>{story.hnScore} points · {story.hnComments} comments</dd></div><div><dt>SOURCES</dt><dd>{story.community ? "ARTICLE + COMMUNITY" : "ARTICLE ONLY"}</dd></div></dl>
  </header>
  <div class="v2-story-card__scores">
    {#each V2_DIMENSIONS as dimension}
      {#if visibleDimensions[dimension]}
        <DimensionScoreRow name={dimension.toUpperCase()} article={story.article.dimensions[dimension]} community={story.community?.dimensions[dimension] ?? null} combined={story.combined.dimensions[dimension]} divergence={story.sourceDivergence[dimension]} />
      {/if}
    {/each}
  </div>
  <div class="v2-evidence-quotes">
    <blockquote><span>ARTICLE EVIDENCE</span>{#if articleQuote}<p>“{articleQuote.quote}”</p><cite>{articleQuote.attribution.replace("_", " ")}</cite>{:else}<p>No exact article excerpt was exported.</p>{/if}</blockquote>
    <blockquote><span>{dissent?.excerpt ? "HN COMMENT · DISSENT" : dissent ? "COMMENT SUMMARY · DISSENT" : "COMMUNITY"}</span>{#if dissent}<p>{dissent.excerpt ? `“${dissent.excerpt}”` : dissent.summary}</p><cite><a href={`https://news.ycombinator.com/item?id=${dissent.commentId}`} target="_blank" rel="noreferrer">HN comment {dissent.commentId} ↗</a></cite>{:else}<p>{story.community?.summary ?? "Community analysis is not available for this story."}</p>{/if}</blockquote>
  </div>
  <details class="v2-story-details">
    <summary>FULL DIAGNOSTICS</summary>
    <div class="v2-story-details__body">
      {#if story.community}
        {#each V2_DIMENSIONS as dimension}
          {#if visibleDimensions[dimension]}<section><h3>{dimension}</h3><CommunityDiagnostics dimension={story.community.dimensions[dimension]} /></section>{/if}
        {/each}
      {:else}<p>Community diagnostics are not available. Combined values use article evidence only.</p>{/if}
    </div>
  </details>
</article>
