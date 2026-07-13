<script lang="ts">
  import type { BotFeedItem } from "$lib/types/v2";
  interface Props { item: BotFeedItem; featured?: boolean; showImage: boolean; }
  let { item, featured = false, showImage }: Props = $props();
</script>

<article class="v2-bot-card" class:v2-bot-card--featured={featured} data-state={item.previewStatus}>
  {#if showImage && item.image}
    <a class="v2-bot-card__image" href={item.canonicalUrl} target="_blank" rel="noreferrer">
      <img src={item.image.url} alt={item.image.alt} width={item.image.width ?? 1200} height={item.image.height ?? 675} loading={featured ? "eager" : "lazy"} />
    </a>
  {/if}
  <div class="v2-bot-card__body">
    <div class="v2-bot-card__source">
      {#if item.faviconUrl}<img src={item.faviconUrl} alt="" width="16" height="16" />{/if}
      <span>{item.domain}</span><b>@{item.bot}</b><time datetime={item.postedAt}>{new Date(item.postedAt).toLocaleDateString("en", { month: "short", day: "2-digit" })}</time>
    </div>
    {#if item.previewStatus !== "complete"}<p class="v2-state-label">PREVIEW {item.previewStatus.toUpperCase()}</p>{/if}
    <h3><a href={item.canonicalUrl} target="_blank" rel="noreferrer">{item.title}</a></h3>
    {#if item.description}<p>{item.description}</p>{/if}
    <ul class="v2-tags" aria-label="Topics">{#each item.scopes as scope}<li>{scope}</li>{/each}</ul>
    <footer>
      <a href={item.canonicalUrl} target="_blank" rel="noreferrer">OPEN SOURCE ↗</a>
      <a href={item.botPostUrl} target="_blank" rel="noreferrer">OPEN BOT POST ↗</a>
      {#if item.matchedHnStoryId}<a href={`#hn-${item.matchedHnStoryId}`}>MATCHED HN ↓</a>{/if}
      {#if item.duplicateCount > 1}<span>{item.duplicateCount} BOT POSTS</span>{/if}
    </footer>
  </div>
</article>
