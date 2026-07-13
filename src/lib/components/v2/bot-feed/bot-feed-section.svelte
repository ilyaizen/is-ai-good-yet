<script lang="ts">
  import type { BotFeedItem } from "$lib/types/v2";
  import BotFeedCard from "./bot-feed-card.svelte";
  interface Props { items: BotFeedItem[]; showImages: boolean; }
  let { items, showImages }: Props = $props();
</script>

<section id="feed" class="v2-section" aria-labelledby="feed-title">
  <header class="v2-section__header"><div><p>PRIMARY STREAM</p><h2 id="feed-title">AI signal feed</h2></div><span>NEWEST FIRST · BOT CURATED</span></header>
  {#if items.length}
    <div class="v2-bot-grid">{#each items as item, index (item.id)}<BotFeedCard {item} featured={index === 0} showImage={showImages} />{/each}</div>
  {:else}
    <div class="v2-empty" role="status"><strong>NO BOT SIGNALS IN THIS GENERATION</strong><p>The normalized feed contract is live. The source adapter has not published records yet.</p></div>
  {/if}
</section>
