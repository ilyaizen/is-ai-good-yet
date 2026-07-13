<script lang="ts">
  import type { V2StoryCard } from "$lib/types/v2";
  import HnStoryCard from "./hn-story-card.svelte";
  interface Props { stories: V2StoryCard[]; visibleDimensions: Record<string, boolean>; }
  let { stories, visibleDimensions }: Props = $props();
</script>

<section id="evidence" class="v2-section v2-section--evidence" aria-labelledby="evidence-title">
  <header class="v2-section__header"><div><p>SECONDARY · ANALYTICAL</p><h2 id="evidence-title">HN evidence</h2></div><span>ARTICLE ≠ COMMUNITY · TENSION PRESERVED</span></header>
  {#if stories.length}
    <div class="v2-story-list">{#each stories as story (story.hnId)}<HnStoryCard {story} {visibleDimensions} />{/each}</div>
  {:else}
    <div class="v2-empty" role="status"><strong>NO ACCEPTED V2 ANALYSES</strong><p>The route does not fall back to V1. Publish a validated V2 generation to populate evidence cards.</p></div>
  {/if}
</section>
