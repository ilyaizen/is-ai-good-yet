<script lang="ts">
  interface Article {
    hn_id: number;
    hn_title: string;
    hn_comments: number;
    hn_score: number;
    hn_timestamp: number;
    sentiment_label: "positive" | "negative" | "neutral";
    url: string;
  }

  let { articles }: { articles: Article[] } = $props();
  const latest = $derived([...articles].sort((a, b) => b.hn_timestamp - a.hn_timestamp).slice(0, 6));
</script>

<section class="v2-panel" aria-labelledby="discussions-title">
  <header class="v2-panel__header"><h2 id="discussions-title">◌ LATEST DISCUSSIONS</h2><a href="#methodology">METHODOLOGY →</a></header>
  <ol class="v2-discussions">
    {#each latest as article}
      <li>
        <span class="v2-trend" data-tone={article.sentiment_label}>{article.sentiment_label === "negative" ? "↓" : article.sentiment_label === "neutral" ? "—" : "↑"}</span>
        <a href={article.url} target="_blank" rel="noreferrer">{article.hn_title}</a>
        <span><b>{article.hn_score}</b> pts<br />{article.hn_comments} comments</span>
      </li>
    {/each}
  </ol>
</section>
