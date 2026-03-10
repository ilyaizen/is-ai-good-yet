<script lang="ts">
  import type { PageData } from "./$types"
  import type { AnalysisPrompts, AnalysisPromptsSuccess, AnalysisPromptsError } from "./+page.server"
  import {
    ArrowLeft,
    MessageSquare,
    User,
    FileText,
    ExternalLink,
    Clock,
    Brain,
    Quote,
    Copy,
    Check,
    Terminal,
  } from "@lucide/svelte"
  import * as Tabs from "$lib/components/ui/tabs"

  let { data }: { data: PageData } = $props()

  function isPromptsError(prompts: AnalysisPrompts): prompts is AnalysisPromptsError {
    return "error" in prompts
  }

  function isPromptsSuccess(prompts: AnalysisPrompts): prompts is AnalysisPromptsSuccess {
    return !("error" in prompts)
  }

  let activeTab = $state("analysis")
  let promptsData = $derived(data.prompts && isPromptsSuccess(data.prompts) ? data.prompts : null)
  let copiedPrefilter = $state(false)
  let copiedClassifier = $state(false)

  const contentLength = $derived(data.article?.text?.length ?? 0)
  const hasContent = $derived(contentLength > 0)
  const formattedContentLength = $derived(contentLength.toLocaleString())

  async function copyToClipboard(text: string, id: "prefilter" | "classifier") {
    try {
      await navigator.clipboard.writeText(text)
      if (id === "prefilter") {
        copiedPrefilter = true
        setTimeout(() => (copiedPrefilter = false), 2000)
      } else {
        copiedClassifier = true
        setTimeout(() => (copiedClassifier = false), 2000)
      }
    } catch (err) {
      console.error("Failed to copy:", err)
    }
  }

  function formatDate(dateStr: string | number | undefined): string {
    if (!dateStr) return "N/A"
    try {
      const date = new Date(typeof dateStr === "number" ? dateStr * 1000 : dateStr)
      return date.toISOString().split("T")[0]
    } catch {
      return String(dateStr)
    }
  }

  function formatTimeAgo(dateStr: string | number | undefined): string {
    if (!dateStr) return "N/A"
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

  function getPrefilterCategories(): string[] {
    if (!data.article) return []
    const categoryStr = data.article.content_category
    if (!categoryStr) return []
    return categoryStr.split(",").map((c: string) => c.trim())
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

<svelte:head>
  <title>{data.article?.title || "Article Preview"} - Is AI Good Yet?</title>
</svelte:head>

<div class="page-container">
  <div class="details-page">
    <a href="/" class="back-link">
      <ArrowLeft class="size-4" />
      <span>back to home</span>
    </a>

    {#if data.article}
      <div class="article-header">
        <div class="article-title-row">
          <span class="article-title">
            {data.article.title || "Untitled Article"}
          </span>
          <a href={data.article.url} target="_blank" rel="noopener noreferrer" class="domain-anchor">
            {getDomain(data.article.url)}
            <ExternalLink class="size-4 domain-external-icon" />
          </a>
        </div>

        <div class="badges-row">
          {#each getPrefilterCategories() as category}
            <span class="badge badge-category">{category}</span>
          {/each}
          {#if data.article.analysis?.topic}
            <span class="badge badge-topic">{data.article.analysis.topic}</span>
          {/if}
        </div>

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
              <div class="value-row">
                <span>{data.article.hn_score || 0} pts / {data.article.hn_comments || 0} comments</span>
                <ExternalLink class="size-4 external-link-icon" />
              </div>
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
                <div class="value-row">
                  <span>{data.article.hn_author}</span>
                  <ExternalLink class="size-4 external-link-icon" />
                </div>
              </div>
            </a>
          {/if}

          <div class="info-box">
            <div class="info-label">
              <Clock class="size-4" />
              <span>Posted</span>
            </div>
            <div class="info-value">
              <span>{formatTimeAgo(data.article.hn_timestamp)}</span>
              <span class="date-parens">({formatDate(data.article.hn_timestamp)})</span>
            </div>
          </div>
        </div>
      </div>

      <div class="tabs-container">
        <Tabs.Root bind:value={activeTab} class="custom-tabs">
          <Tabs.List class="tabs-list">
            <Tabs.Trigger value="analysis" class="tab-trigger">
              <Brain class="size-4" />
              <span>Analysis</span>
            </Tabs.Trigger>
            <Tabs.Trigger value="prompts" class="tab-trigger">
              <Terminal class="size-4" />
              <span>Prompts</span>
            </Tabs.Trigger>
            <Tabs.Trigger value="content" class="tab-trigger">
              <FileText class="size-4" />
              <span>Content</span>
              <span class="tab-hint">({formattedContentLength})</span>
            </Tabs.Trigger>
          </Tabs.List>

          <Tabs.Content value="analysis" class="tab-content">
            {#if data.article.analysis && data.article.analysis.summary}
              <div class="terminal-section">
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

                  <div class="metric-card">
                    <div class="metric-label">topic</div>
                    <span class="metric-badge badge-neutral">{data.article.analysis.topic}</span>
                  </div>
                </div>

                <div class="summary-block">
                  <div class="block-header">
                    <span class="prompt-symbol">$</span>
                    <span>summary</span>
                  </div>
                  <div class="block-content">{data.article.analysis.summary}</div>
                </div>

                {#if data.article.analysis.quotes && data.article.analysis.quotes.length > 0}
                  <div class="quotes-block">
                    <div class="block-header">
                      <Quote class="size-4" />
                      <span>key_quotes</span>
                    </div>
                    {#each data.article.analysis.quotes as quote}
                      <blockquote class="quote-item">{quote}</blockquote>
                    {/each}
                  </div>
                {/if}
              </div>
            {:else}
              <div class="empty-state">
                <Terminal class="size-8" />
                <span>No sentiment analysis available.</span>
              </div>
            {/if}
          </Tabs.Content>

          <Tabs.Content value="prompts" class="tab-content">
            {#if promptsData}
              <div class="terminal-section">
                <div class="prompt-block">
                  <div class="block-header">
                    <span class="prompt-symbol">$</span>
                    <span>prefilter_prompt</span>
                    <span class="model-tag">{promptsData.prefilter.model}</span>
                    <span class="size-tag">
                      {promptsData.prefilter.actual_length.toLocaleString()} / {promptsData.prefilter.truncation_limit.toLocaleString()}
                      chars
                    </span>
                    <button
                      class="copy-btn"
                      onclick={() => {
                        if (promptsData) {
                          copyToClipboard(promptsData.prefilter.prompt, "prefilter")
                        }
                      }}
                      title="Copy prefilter prompt">
                      {#if copiedPrefilter}
                        <Check class="size-3" />
                      {:else}
                        <Copy class="size-3" />
                      {/if}
                    </button>
                  </div>
                  <pre class="prompt-content">{promptsData.prefilter.prompt}</pre>
                </div>

                {#if data.article.content_filter_json}
                  <div class="prompt-block response-block">
                    <div class="block-header">
                      <span class="prompt-symbol">></span>
                      <span>prefilter_response</span>
                      <span class="model-tag">{promptsData.prefilter.model}</span>
                    </div>
                    <pre class="prompt-content response-content">{JSON.stringify(
                        data.article.content_filter_json,
                        null,
                        2
                      )}</pre>
                  </div>
                {/if}

                <div class="prompt-block">
                  <div class="block-header">
                    <span class="prompt-symbol">$</span>
                    <span>classifier_prompt</span>
                    <span class="model-tag">{promptsData.classifier.model}</span>
                    <span class="size-tag">
                      {promptsData.classifier.actual_length.toLocaleString()} / {promptsData.classifier.truncation_limit.toLocaleString()}
                      chars
                    </span>
                    <button
                      class="copy-btn"
                      onclick={() => {
                        if (promptsData) {
                          const fullPrompt = `${promptsData.classifier.system_prompt}\n\n${promptsData.classifier.user_prompt}`
                          copyToClipboard(fullPrompt, "classifier")
                        }
                      }}
                      title="Copy classifier prompt">
                      {#if copiedClassifier}
                        <Check class="size-3" />
                      {:else}
                        <Copy class="size-3" />
                      {/if}
                    </button>
                  </div>
                  <div class="prompt-section-title">system_prompt</div>
                  <pre class="prompt-content system-content">{promptsData.classifier.system_prompt}</pre>
                  <div class="prompt-section-title">user_prompt</div>
                  <pre class="prompt-content">{promptsData.classifier.user_prompt}</pre>
                </div>

                {#if data.article.analysis}
                  <div class="prompt-block response-block">
                    <div class="block-header">
                      <span class="prompt-symbol">></span>
                      <span>sentiment_analysis_response</span>
                      <span class="model-tag">{promptsData.classifier.model}</span>
                    </div>
                    <pre class="prompt-content response-content">{JSON.stringify(data.article.analysis, null, 2)}</pre>
                  </div>
                {:else if promptsData?.text_missing}
                  <div class="prompt-block pending-block">
                    <div class="pending-message">
                      <Terminal class="size-4" />
                      <span>Article content not scraped. Run scraper to enable classification.</span>
                    </div>
                  </div>
                {:else}
                  <div class="prompt-block pending-block">
                    <div class="pending-message">
                      <Terminal class="size-4" />
                      <span>Article not classified. Run sentiment analyzer to see response.</span>
                    </div>
                  </div>
                {/if}
              </div>
            {:else if data.prompts && isPromptsError(data.prompts)}
              <div class="empty-state">
                <Terminal class="size-8" />
                <span>Prompts unavailable: {data.prompts.error}</span>
              </div>
            {:else}
              <div class="empty-state">
                <Terminal class="size-8" />
                <span>Run scraper to generate prompt previews.</span>
              </div>
            {/if}
          </Tabs.Content>

          <Tabs.Content value="content" class="tab-content">
            {#if hasContent}
              <div class="terminal-section">
                <div class="content-block">
                  <div class="block-header">
                    <FileText class="size-4" />
                    <span>article_content</span>
                    <span class="size-tag">{formattedContentLength} chars</span>
                  </div>
                  <div class="content-text">{data.article.text}</div>
                </div>
              </div>
            {:else}
              <div class="empty-state">
                <FileText class="size-8" />
                <span>No content available</span>
              </div>
            {/if}
          </Tabs.Content>
        </Tabs.Root>
      </div>
    {:else}
      <div class="alert-box">
        <div class="alert-icon">!</div>
        <div class="alert-content">
          <h3>Content Unavailable</h3>
          <p>
            {#if data.error}
              Error: {data.error}
            {:else}
              This article content could not be found. It may not have been scraped successfully yet.
            {/if}
          </p>
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .page-container {
    max-width: 80rem;
    width: 100%;
    margin: 0 auto;
    padding: 0 1.5rem;
  }

  .details-page {
    padding: 2rem 0;
  }

  .back-link {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--color-text-secondary);
    text-decoration: none;
    font-family: var(--font-mono);
    font-size: 0.875rem;
    margin-bottom: 2rem;
    transition: color 0.2s;
  }

  .back-link:hover {
    color: var(--color-accent);
  }

  .article-header {
    margin-bottom: 3rem;
  }

  .article-title-row {
    margin-bottom: 1.25rem;
    font-family: var(--font-mono);
  }

  .article-title {
    color: var(--color-text-primary);
    font-size: 1.25rem;
    font-weight: 600;
  }

  .domain-anchor {
    color: var(--color-accent);
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
  }

  .domain-anchor:hover {
    text-decoration: underline;
  }

  .domain-external-icon {
    color: var(--color-accent);
    transition: opacity 0.2s;
    flex-shrink: 0;
  }

  .badges-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
  }

  .badge {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.25rem 0.625rem;
    border-radius: var(--radius-sm);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .badge-category {
    background: rgba(168, 85, 247, 0.25);
    color: #9333ea;
  }

  .badge-topic {
    background: rgba(14, 165, 233, 0.25);
    color: #0ea5e9;
  }

  .info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
  }

  .info-box {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: 1rem;
    text-decoration: none;
    transition: all 0.2s;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  .info-box:hover {
    border-color: var(--color-accent);
  }

  .info-box-link:hover {
    border-color: var(--color-accent);
    background: var(--color-bg);
  }

  .external-link-icon {
    color: var(--color-accent);
    transition: opacity 0.2s;
    flex-shrink: 0;
  }

  .info-box-link .info-value {
    color: var(--color-accent);
  }

  .info-box-link:hover .value-row {
    text-decoration: underline;
  }

  .value-row {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
  }

  .info-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-family: var(--font-mono);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-muted);
    margin-bottom: 0.5rem;
  }

  .info-value {
    font-family: var(--font-mono);
    font-weight: 600;
    font-size: 1.125rem;
    color: var(--color-text-primary);
  }

  .date-parens {
    font-size: 0.875em;
    color: var(--color-text-muted);
    font-weight: 400;
  }

  .custom-tabs {
    width: 100%;
  }

  :global(.tabs-list) {
    background: var(--color-surface);
    border-radius: var(--radius-md);
  }

  .tab-trigger {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.875rem 0.75rem;
    border-radius: var(--radius-sm);
    font-family: var(--font-mono);
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--color-text-muted);
    transition: all 0.2s;
    cursor: pointer;
    border: none;
    background: transparent;
    width: 100%;
    min-height: 44px;
  }

  .tab-trigger:hover {
    color: var(--color-text-primary);
    background: var(--color-bg);
  }

  :global(.tab-trigger[data-state="active"]) {
    background: var(--color-accent);
    color: var(--color-accent-foreground);
  }

  .tab-hint {
    font-size: 0.7rem;
    opacity: 0.7;
  }

  .tab-content {
    margin-top: 1.5rem;
    padding: 0.5rem;
  }

  .terminal-section {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 1rem;
  }

  .metric-card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: 1rem;
    text-align: center;
  }

  .metric-card.sentiment-positive {
    border-color: #22c55e;
  }
  .metric-card.sentiment-positive .metric-value {
    color: #22c55e;
  }

  .metric-card.sentiment-negative {
    border-color: #ef4444;
  }
  .metric-card.sentiment-negative .metric-value {
    color: #ef4444;
  }

  .metric-card.sentiment-neutral {
    border-color: #eab308;
  }
  .metric-card.sentiment-neutral .metric-value {
    color: #eab308;
  }

  .metric-label {
    font-family: var(--font-mono);
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-muted);
    margin-bottom: 0.5rem;
  }

  .metric-value {
    font-family: var(--font-mono);
    font-size: 1.5rem;
    font-weight: 700;
  }

  .metric-badge {
    display: inline-block;
    padding: 0.25rem 0.625rem;
    border-radius: var(--radius-sm);
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: capitalize;
  }

  .badge-positive {
    background: rgba(34, 197, 94, 0.25);
    color: #16a34a;
  }
  .badge-negative {
    background: rgba(239, 68, 68, 0.25);
    color: #dc2626;
  }
  .badge-mixed {
    background: rgba(234, 179, 8, 0.25);
    color: #ca8a04;
  }
  .badge-neutral {
    background: var(--color-surface);
    color: var(--color-text-secondary);
    border: 1px solid var(--color-border);
  }

  .block-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    font-family: var(--font-mono);
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--color-text-primary);
    margin-bottom: 1rem;
    flex-wrap: wrap;
    padding: 1rem 1rem 0 1rem;
  }

  .prompt-symbol {
    color: var(--color-accent);
  }

  .model-tag {
    background: var(--color-accent);
    color: var(--color-accent-foreground);
    padding: 0.125rem 0.5rem;
    border-radius: var(--radius-sm);
    font-size: 0.7rem;
    font-family: var(--font-mono);
  }

  .size-tag {
    font-size: 0.75rem;
    color: var(--color-text-muted);
    font-family: var(--font-mono);
  }

  .copy-btn {
    margin-left: auto;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    background: transparent;
    border: none;
    color: var(--color-text-muted);
    cursor: pointer;
    transition: all 0.2s;
  }

  .copy-btn:hover {
    color: var(--color-accent);
    background: rgba(var(--color-accent-rgb, 59, 130, 246), 0.1);
  }

  .summary-block {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: 1rem;
  }

  .block-content {
    color: var(--color-text-primary);
    font-size: 0.9rem;
    line-height: 1.6;
  }

  .quotes-block {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: 1rem;
  }

  .quote-item {
    margin: 0 0 0.75rem 0;
    padding: 0.75rem 1rem;
    background: var(--color-bg);
    border-left: 2px solid var(--color-accent);
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    font-style: italic;
    font-size: 0.875rem;
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
  }

  .quote-item:last-child {
    margin-bottom: 0;
  }

  .prompt-block {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    overflow: hidden;
  }

  .prompt-block.response-block {
    border-left: 3px solid var(--color-accent);
  }

  .prompt-block.pending-block {
    border-left: 3px solid var(--color-text-muted);
  }

  .prompt-section-title {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-muted);
    margin: 1rem 1rem 0.5rem 1rem;
  }

  .prompt-content {
    margin: 0;
    padding: 1rem;
    background: var(--color-bg);
    font-family: var(--font-mono);
    font-size: 0.8rem;
    line-height: 1.6;
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-x: auto;
    color: var(--color-text-primary);
    border-top: 1px solid var(--color-border);
  }

  .prompt-content.system-content {
    border-left: 3px solid var(--color-accent);
  }

  .prompt-content.response-content {
    background: rgba(var(--color-accent-rgb, 59, 130, 246), 0.05);
  }

  .pending-message {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1.5rem;
    text-align: center;
    color: var(--color-text-muted);
    font-style: italic;
    font-size: 0.875rem;
    font-family: var(--font-mono);
  }

  .content-block {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    overflow: hidden;
  }

  .content-text {
    padding: 1.5rem;
    white-space: pre-wrap;
    line-height: 1.8;
    color: var(--color-text-primary);
    font-size: 0.9rem;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    padding: 3rem;
    text-align: center;
    background: var(--color-surface);
    border: 1px dashed var(--color-border);
    border-radius: var(--radius-md);
    color: var(--color-text-muted);
    font-family: var(--font-mono);
  }

  .alert-box {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    background: rgba(245, 158, 11, 0.1);
    border-left: 4px solid #f59e0b;
    padding: 1.5rem;
    border-radius: var(--radius-md);
  }

  .alert-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    background: #f59e0b;
    color: white;
    border-radius: 50%;
    font-weight: 700;
    font-size: 14px;
    flex-shrink: 0;
    font-family: var(--font-mono);
  }

  .alert-content h3 {
    margin: 0 0 0.5rem 0;
    font-size: 1.125rem;
    color: #92400e;
    font-family: var(--font-mono);
  }

  .alert-content p {
    margin: 0;
    color: #b45309;
  }

  @media (max-width: 768px) {
    .tab-hint {
      display: none;
    }
  }
</style>
