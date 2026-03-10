<script lang="ts">
  import * as Sheet from "$lib/components/ui/sheet"
  import { MessageSquare, User, ExternalLink, Clock, Brain, Quote, Loader2, ChevronDown } from "@lucide/svelte"
  import type { ArticleDetailsResponse } from "$lib/types/article-details"

  let {
    hnId = $bindable<number | null>(null),
    open = $bindable(false),
  }: {
    hnId: number | null
    open: boolean
  } = $props()

  let loading = $state(false)
  let error = $state<string | null>(null)
  let data = $state<ArticleDetailsResponse | null>(null)
  let contentExpanded = $state(false)

  // Fetch article details when hnId changes and sheet is open
  $effect(() => {
    if (open && hnId !== null) {
      fetchArticleDetails(hnId)
    }
  })

  // Reset state when sheet closes
  $effect(() => {
    if (!open) {
      data = null
      error = null
      contentExpanded = false
    }
  })

  async function fetchArticleDetails(id: number) {
    loading = true
    error = null
    try {
      const response = await fetch(`/api/article-details/${id}`)
      if (!response.ok) {
        throw new Error(`Failed to fetch article: ${response.statusText}`)
      }
      data = await response.json()
      if (data?.error) {
        error = data.error
      }
    } catch (e) {
      error = e instanceof Error ? e.message : String(e)
    } finally {
      loading = false
    }
  }

  // Formatting helpers
  function formatDate(dateStr: string | number | null | undefined): string {
    if (dateStr === null || dateStr === undefined) return "N/A"
    try {
      const date = new Date(typeof dateStr === "number" ? dateStr * 1000 : dateStr)
      return date.toISOString().split("T")[0]
    } catch {
      return String(dateStr)
    }
  }

  function formatTimeAgo(dateStr: string | number | null | undefined): string {
    if (dateStr === null || dateStr === undefined) return "N/A"
    try {
      const date = new Date(typeof dateStr === "number" ? dateStr * 1000 : dateStr)
      const now = new Date()
      const diffMs = now.getTime() - date.getTime()
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
      if (diffDays < 1) return "today"
      if (diffDays < 7) return `${diffDays}d ago`
      if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`
      if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`
      return `${Math.floor(diffDays / 365)}y ago`
    } catch {
      return String(dateStr)
    }
  }

  function getUtilityBadgeClass(utility: string): string {
    switch (utility) {
      case "magic":
      case "tool":
        return "badge-positive"
      case "toil":
      case "hazard":
        return "badge-negative"
      default:
        return "badge-mixed"
    }
  }

  function getTrajectoryBadgeClass(trajectory: string): string {
    switch (trajectory) {
      case "optimistic":
        return "badge-positive"
      case "pessimistic":
        return "badge-negative"
      default:
        return "badge-mixed"
    }
  }

  function formatSentimentScore(score: number | null): string {
    if (score === null) return "N/A"
    return score >= 0 ? `+${score.toFixed(2)}` : score.toFixed(2)
  }

  function getSentimentClass(score: number | null): string {
    if (score === null) return ""
    if (score > 0.2) return "sentiment-positive"
    if (score < -0.2) return "sentiment-negative"
    return "sentiment-neutral"
  }

  function getDomain(url: string): string {
    try {
      const urlObj = new URL(url)
      return urlObj.hostname.replace(/^www\./, "")
    } catch {
      return url
    }
  }
</script>

<Sheet.Root bind:open>
  <Sheet.Content side="right" class="sheet-content-wide">
    {#if loading}
      <Sheet.Header>
        <Sheet.Title>Loading...</Sheet.Title>
      </Sheet.Header>
      <div class="loading-state">
        <Loader2 class="size-8 animate-spin" />
        <span>Loading article details...</span>
      </div>
    {:else if error}
      <Sheet.Header>
        <Sheet.Title>Error</Sheet.Title>
      </Sheet.Header>
      <div class="error-state">
        <Brain class="size-8" />
        <span>Error: {error}</span>
      </div>
    {:else if data?.article}
      <Sheet.Header>
        <Sheet.Title class="article-title">
          {data.article.title || "Untitled Article"}
        </Sheet.Title>
        <Sheet.Description>
          <a href={data.article.url} target="_blank" rel="noopener noreferrer" class="domain-anchor">
            {getDomain(data.article.url)}
            <ExternalLink class="size-4" />
          </a>
        </Sheet.Description>
      </Sheet.Header>

      <div class="sheet-body">
        <!-- Metadata Section -->
        <section class="section">
          <div class="info-grid">
            <a
              href={`https://news.ycombinator.com/item?id=${data.article.hn_id}`}
              target="_blank"
              rel="noopener noreferrer"
              class="info-box info-box-link">
              <div class="info-label">
                <MessageSquare class="size-4" />
                <span>HN Stats</span>
              </div>
              <div class="info-value">
                {data.article.hn_score || 0} points / <br />
                {data.article.hn_comments || 0} comments
                <ExternalLink class="size-3 external-icon" />
              </div>
            </a>

            {#if data.article.hn_author}
              <a
                href={`https://news.ycombinator.com/user?id=${data.article.hn_author}`}
                target="_blank"
                rel="noopener noreferrer"
                class="info-box info-box-link">
                <div class="info-label">
                  <User class="size-4" />
                  <span>Poster</span>
                </div>
                <div class="info-value">
                  {data.article.hn_author}
                  <ExternalLink class="size-3 external-icon" />
                </div>
              </a>
            {/if}

            <div class="info-box">
              <div class="info-label">
                <Clock class="size-4" />
                <span>Posted</span>
              </div>
              <div class="info-value">
                {formatTimeAgo(data.article.hn_timestamp)}
                <span class="date-muted">({formatDate(data.article.hn_timestamp)})</span>
              </div>
            </div>
          </div>
        </section>

        <!-- Analysis Section -->
        {#if data.article.analysis}
          <section class="section">
            <h3 class="section-title">
              <Brain class="size-4" />
              <span>Analysis</span>
            </h3>

            <div class="metrics-grid">
              <div class="metric-card {getSentimentClass(data.article.sentiment_score)}">
                <div class="metric-label">sentiment</div>
                <div class="metric-value">{formatSentimentScore(data.article.sentiment_score)}</div>
              </div>

              <div class="metric-card">
                <div class="metric-label">utility</div>
                <span class="metric-badge {getUtilityBadgeClass(data.article.analysis.utility)}">
                  {data.article.analysis.utility}
                </span>
              </div>

              <div class="metric-card">
                <div class="metric-label">trajectory</div>
                <span class="metric-badge {getTrajectoryBadgeClass(data.article.analysis.trajectory)}">
                  {data.article.analysis.trajectory}
                </span>
              </div>

              {#if data.article.analysis.topic}
                <div class="metric-card">
                  <div class="metric-label">topic</div>
                  <span class="metric-badge badge-neutral">{data.article.analysis.topic}</span>
                </div>
              {/if}
            </div>

            <div class="summary-block">
              <p>{data.article.analysis.summary}</p>
            </div>

            {#if data.article.analysis.quotes && data.article.analysis.quotes.length > 0}
              <div class="quotes-section">
                <h4 class="subsection-title">
                  <Quote class="size-4" />
                  <span>Key Quotes</span>
                </h4>
                {#each data.article.analysis.quotes as quote}
                  <blockquote class="quote-item">{quote}</blockquote>
                {/each}
              </div>
            {/if}
          </section>
        {/if}

        <!-- Collapsible Content Section -->
        {#if data.article.text && data.article.text.length > 0}
          <section class="section">
            <button class="collapse-trigger" onclick={() => (contentExpanded = !contentExpanded)}>
              <span class="section-title">
                <span>Article Content</span>
                <span class="content-hint">({data.article.text.length.toLocaleString()} chars)</span>
              </span>
              <ChevronDown class="size-4 collapse-icon {contentExpanded ? 'rotated' : ''}" />
            </button>
            {#if contentExpanded}
              <div class="content-text">{data.article.text}</div>
            {/if}
          </section>
        {/if}
      </div>
    {:else}
      <Sheet.Header>
        <Sheet.Title>No Data</Sheet.Title>
      </Sheet.Header>
      <div class="empty-state">
        <Brain class="size-8" />
        <span>No article data available</span>
      </div>
    {/if}
  </Sheet.Content>
</Sheet.Root>

<style>
  :global([data-slot="sheet-content"].sheet-content-wide) {
    width: 90%;
    max-width: 700px;
  }

  .loading-state,
  .error-state,
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    padding: 3rem;
    text-align: center;
    color: var(--color-text-muted);
    font-family: var(--font-mono);
    height: 100%;
  }

  :global(.loading-state .animate-spin) {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }

  :global([data-slot="sheet-title"].article-title) {
    color: var(--color-text-primary);
    font-family: var(--font-mono);
    font-size: 1.1rem;
    font-weight: 600;
    line-height: 1.4;
  }

  .domain-anchor {
    color: var(--color-primary);
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    font-size: 0.875rem;
  }

  .domain-anchor:hover {
    text-decoration: underline;
  }

  .sheet-body {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    padding: 0 1rem 1rem;
    overflow-y: auto;
    max-height: calc(100vh - 120px);
  }

  .section {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .section-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-family: var(--font-mono);
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--color-text-primary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .subsection-title {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text-muted);
    margin: 0 0 0.5rem 0;
  }

  .info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 0.75rem;
  }

  .info-box {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: 0.75rem;
    text-decoration: none;
    transition: all 0.2s var(--ease-swift);
  }

  .info-box-link:hover {
    border-color: var(--color-primary);
    background: var(--color-bg);
  }

  .info-label {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-family: var(--font-mono);
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-muted);
    margin-bottom: 0.25rem;
  }

  .info-value {
    font-family: var(--font-mono);
    font-weight: 600;
    font-size: 0.9rem;
    color: var(--color-text-primary);
    display: flex;
    align-items: center;
    gap: 0.375rem;
    flex-wrap: wrap;
  }

  .info-box-link .info-value {
    color: var(--color-primary);
  }

  .external-icon {
    color: var(--color-primary);
  }

  .date-muted {
    font-size: 0.75rem;
    color: var(--color-text-muted);
    font-weight: 400;
  }

  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
    gap: 0.5rem;
  }

  .metric-card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: 0.75rem;
    text-align: center;
  }

  .metric-card.sentiment-positive {
    border-color: var(--color-primary);
  }
  .metric-card.sentiment-positive .metric-value {
    color: var(--color-primary);
  }

  .metric-card.sentiment-negative {
    border-color: var(--color-destructive);
  }
  .metric-card.sentiment-negative .metric-value {
    color: var(--color-destructive);
  }

  .metric-card.sentiment-neutral {
    border-color: var(--color-warning);
  }
  .metric-card.sentiment-neutral .metric-value {
    color: var(--color-warning);
  }

  .metric-label {
    font-family: var(--font-mono);
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-muted);
    margin-bottom: 0.25rem;
  }

  .metric-value {
    font-family: var(--font-mono);
    font-size: 1.1rem;
    font-weight: 700;
  }

  .metric-badge {
    display: inline-block;
    padding: 0.2rem 0.5rem;
    border-radius: var(--radius-sm);
    font-family: var(--font-mono);
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: capitalize;
  }

  .badge-positive {
    background: color-mix(in srgb, var(--color-primary), transparent 75%);
    color: var(--color-primary);
  }
  .badge-negative {
    background: color-mix(in srgb, var(--color-destructive), transparent 75%);
    color: var(--color-destructive);
  }
  .badge-mixed {
    background: color-mix(in srgb, var(--color-warning), transparent 75%);
    color: var(--color-warning);
  }
  .badge-neutral {
    background: var(--color-surface);
    color: var(--color-text-secondary);
    border: 1px solid var(--color-border);
  }

  .summary-block {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: 1rem;
  }

  .summary-block p {
    margin: 0;
    font-size: 0.9rem;
    line-height: 1.6;
    color: var(--color-text-primary);
  }

  .quotes-section {
    margin-top: 0.5rem;
  }

  .quote-item {
    margin: 0 0 0.5rem 0;
    padding: 0.75rem;
    background: var(--color-bg);
    border-left: 3px solid var(--color-primary);
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    font-style: italic;
    font-size: 0.85rem;
    color: var(--color-text-secondary);
    line-height: 1.5;
  }

  .quote-item:last-child {
    margin-bottom: 0;
  }

  .collapse-trigger {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    padding: 0.75rem;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all 0.2s var(--ease-swift);
  }

  .collapse-trigger:hover {
    border-color: var(--color-primary);
  }

  .content-hint {
    font-size: 0.7rem;
    color: var(--color-text-muted);
    font-weight: 400;
    text-transform: none;
    letter-spacing: normal;
  }

  .collapse-icon {
    transition: transform 0.2s var(--ease-swift);
  }

  .collapse-icon.rotated {
    transform: rotate(180deg);
  }

  .content-text {
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: 1rem;
    white-space: pre-wrap;
    line-height: 1.7;
    color: var(--color-text-primary);
    font-size: 0.85rem;
    max-height: 300px;
    overflow-y: auto;
  }

  @media (max-width: 640px) {
    :global([data-slot="sheet-content"].sheet-content-wide) {
      width: 100%;
      max-width: 100%;
    }
  }
</style>
