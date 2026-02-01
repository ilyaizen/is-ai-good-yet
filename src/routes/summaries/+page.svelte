<script lang="ts">
  import type { PageData } from "./$types"
  import { Button } from "$lib/components/ui/button"
  import { ArrowLeft, Download } from "lucide-svelte"

  let { data }: { data: PageData } = $props()

  function getSentimentClass(score: number): string {
    if (score > 0.2) return "sentiment-positive"
    if (score < -0.2) return "sentiment-negative"
    return "sentiment-neutral"
  }

  function formatScore(score: number): string {
    return score >= 0 ? `+${score.toFixed(2)}` : score.toFixed(2)
  }

  function downloadJSON(data: string[], filename: string) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  function exportSummaries() {
    const positive = data.summaries.filter((s) => s.sentiment_score > 0.2).map((s) => s.summary)
    const neutral = data.summaries
      .filter((s) => s.sentiment_score >= -0.2 && s.sentiment_score <= 0.2)
      .map((s) => s.summary)
    const negative = data.summaries.filter((s) => s.sentiment_score < -0.2).map((s) => s.summary)

    downloadJSON(positive, "positive.json")
    downloadJSON(neutral, "neutral.json")
    downloadJSON(negative, "negative.json")
  }
</script>

<svelte:head>
  <title>Article Summaries - Is AI Good Yet?</title>
</svelte:head>

<div class="page-container">
  <div class="page-padding">
    <section class="hero-section">
      <div class="hero-content">
        <h1>Article <span class="highlight">Summaries</span></h1>
        <p class="subtitle">
          {data.summaries.length} opinion articles from sentiment analysis
        </p>
        <div class="cta-buttons">
          <Button href="/pipeline-admin" variant="outline" size="xl" class="btn-secondary-glow">
            <ArrowLeft size={18} />
            Back to Pipeline
          </Button>
          <Button onclick={exportSummaries} variant="outline" size="xl" class="btn-secondary-glow">
            <Download size={18} />
            Export Summaries
          </Button>
        </div>
      </div>
    </section>

    <section class="summaries-section">
      {#each data.summaries as entry (entry.hn_id)}
        <article class="summary-card">
          <header class="summary-header">
            <a href="/details/{entry.hn_id}" class="title-link">
              {entry.hn_title}
            </a>
            <div class="summary-meta">
              <span class="theme-badge">{entry.topic}</span>
              <span class={getSentimentClass(entry.sentiment_score)}>
                {formatScore(entry.sentiment_score)}
              </span>
            </div>
          </header>
          <p class="summary-text">{entry.summary}</p>
        </article>
      {/each}
    </section>
  </div>
</div>

<style>
  .page-padding {
    padding-top: 2rem;
    padding-bottom: 4rem;
  }

  .hero-section {
    padding-top: 2rem;
    padding-bottom: 2rem;
  }

  .hero-content {
    display: flex;
    flex-direction: column;
    width: 100%;
  }

  .hero-content h1 {
    font-family: var(--font-mono);
    color: var(--table-text);
    font-size: 1.75rem;
    margin-bottom: 0.5rem;
  }

  @media (min-width: 640px) {
    .hero-content h1 {
      font-size: 2rem;
    }
  }

  .subtitle {
    font-size: 1rem;
    margin-bottom: 1.5rem;
    color: var(--table-secondary-text);
  }

  .cta-buttons {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
  }

  :global(.btn-secondary-glow) {
    background: transparent !important;
    color: var(--color-accent) !important;
    border: 1px solid var(--color-accent) !important;
    font-family: var(--font-mono);
  }

  :global(.btn-secondary-glow:hover) {
    background: color-mix(in srgb, var(--color-accent) 10%, transparent) !important;
    transform: translateY(-2px);
  }

  .summaries-section {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .summary-card {
    background: var(--table-bg);
    border: 1px solid var(--table-border);
    border-radius: 0.5rem;
    padding: 1rem 1.25rem;
  }

  .summary-header {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }

  @media (min-width: 640px) {
    .summary-header {
      flex-direction: row;
      justify-content: space-between;
      align-items: flex-start;
    }
  }

  .title-link {
    font-family: var(--font-mono);
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--color-accent);
    text-decoration: none;
    line-height: 1.3;
  }

  .title-link:hover {
    text-decoration: underline;
  }

  .summary-meta {
    display: flex;
    gap: 0.75rem;
    align-items: center;
    flex-shrink: 0;
  }

  .theme-badge {
    font-family: var(--font-mono);
    font-size: 0.7rem;
    text-transform: uppercase;
    padding: 0.2rem 0.5rem;
    background: color-mix(in srgb, var(--color-accent) 15%, transparent);
    color: var(--color-accent);
    border-radius: 0.25rem;
  }

  .sentiment-positive {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    color: #16a34a;
    font-weight: 600;
  }

  .sentiment-negative {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    color: #dc2626;
    font-weight: 600;
  }

  .sentiment-neutral {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    color: #ca8a04;
    font-weight: 600;
  }

  .summary-text {
    font-size: 0.9rem;
    line-height: 1.6;
    color: var(--table-secondary-text);
    margin: 0;
  }
</style>
