<script lang="ts">
  import type { InfluentialArticle } from "$lib/server/db"
  import type { ArticleDetails, ArticleDetailsResponse } from "$lib/types/article-details"
  import { cueHover, cueSheet } from "$lib/audio/v12-sound"
  import { bandScore, formatInt, formatIsoDate, hostnameOf, sentimentBand } from "./phosphor-data"

  let {
    article,
    onClose,
    onStep,
    hasPrevious,
    hasNext,
  }: {
    article: InfluentialArticle | null
    onClose: () => void
    onStep: (offset: number) => void
    hasPrevious: boolean
    hasNext: boolean
  } = $props()

  let dialog = $state<HTMLDialogElement>()
  let details = $state<ArticleDetails | null>(null)
  let failed = $state(false)
  const articleId = $derived(article?.hn_id)

  $effect(() => {
    if (!dialog) return
    if (articleId !== undefined && !dialog.open) {
      dialog.showModal()
      cueSheet(true)
    } else if (articleId === undefined && dialog.open) {
      dialog.close()
    }
  })

  $effect(() => {
    const currentId = articleId
    details = null
    failed = false
    if (currentId === undefined) return
    const controller = new AbortController()
    void fetch(`/api/article-details/${currentId}`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Details unavailable")
        const payload: ArticleDetailsResponse = await response.json()
        if (!controller.signal.aborted) {
          details = payload.article
          failed = !payload.article
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) failed = true
      })
    return () => controller.abort()
  })

  function close(): void {
    cueSheet(false)
    onClose()
  }

  function step(offset: number): void {
    if ((offset < 0 && !hasPrevious) || (offset > 0 && !hasNext)) return
    cueHover((article?.sentiment_score ?? 0) * 50)
    onStep(offset)
    const body = dialog?.querySelector(".dlg-body")
    if (body) body.scrollTop = 0
  }

  function onKeydown(event: KeyboardEvent): void {
    if (event.altKey || event.ctrlKey || event.metaKey) return
    const key = event.key.toLowerCase()
    if (key === "j" || key === "k") {
      event.preventDefault()
      step(key === "j" ? 1 : -1)
    }
  }
</script>

<dialog
  bind:this={dialog}
  class="dlg"
  aria-labelledby="dlg-title"
  oncancel={(event) => {
    event.preventDefault()
    close()
  }}
  onkeydown={onKeydown}
>
  <header class="dlg-head">
    <span class="dlg-path">inspect // hn/{article?.hn_id ?? "—"}</span>
    <div class="dlg-actions">
      <button type="button" disabled={!hasPrevious} onclick={() => step(-1)} aria-label="Previous story (K)">prev K</button>
      <button type="button" disabled={!hasNext} onclick={() => step(1)} aria-label="Next story (J)">next J</button>
      <button type="button" onclick={close} aria-label="Close details">close Esc</button>
    </div>
  </header>

  {#if article}
    {@const band = sentimentBand(article.sentiment_score)}
    {@const domain = hostnameOf(article.url)}
    <div class="dlg-body">
      <h2 id="dlg-title">{article.hn_title}</h2>
      <dl class="dlg-meta">
        <div><dt>Posted (UTC)</dt><dd>{formatIsoDate(article)}</dd></div>
        <div>
          <dt>Sentiment</dt>
          <dd class={`band-${band}`}>{bandScore(article.sentiment_score)} ({article.sentiment_label})</dd>
        </div>
        <div><dt>HN Points</dt><dd>{formatInt(article.hn_score)}</dd></div>
        <div><dt>Comments</dt><dd>{formatInt(article.hn_comments)}</dd></div>
        <div><dt>Source</dt><dd>{domain || "news.ycombinator.com"}</dd></div>
        <div><dt>Topic</dt><dd>{article.topic || "—"}</dd></div>
      </dl>

      {#if article.summary}
        <h3>Summary</h3>
        <p class="dlg-summary">{article.summary}</p>
      {/if}

      <h3>Exported quotes</h3>
      {#if failed}
        <p class="dlg-note" role="status">Details are unavailable for this story.</p>
      {:else if !details}
        <p class="dlg-note" role="status">Loading story details…</p>
      {:else if details.analysis?.quotes?.length}
        <ul class="dlg-quotes">
          {#each details.analysis.quotes as quote, index (index)}
            <li><p>{quote}</p></li>
          {/each}
        </ul>
      {:else}
        <p class="dlg-note">No quotes were exported for this story.</p>
      {/if}

      <div class="dlg-links">
        <a href={`https://news.ycombinator.com/item?id=${article.hn_id}`} target="_blank" rel="noreferrer">
          Open HN thread
        </a>
        {#if article.url}
          <a href={article.url} target="_blank" rel="noreferrer">Open source article</a>
        {/if}
      </div>
    </div>
  {/if}
</dialog>

<style>
  .dlg {
    inset: 0 0 0 auto;
    margin: 0;
    width: min(100%, 36rem);
    max-width: 100%;
    height: 100dvh;
    max-height: 100dvh;
    background: var(--td-surface);
    color: var(--td-ink);
    border: 0;
    border-inline-start: 1px solid var(--td-rule);
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
  }

  .dlg[open] {
    display: flex;
    flex-direction: column;
    animation: dlg-slide-in 320ms var(--ease-swift) both;
  }

  .dlg::backdrop {
    background: var(--td-scrim);
  }

  .dlg-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    flex-wrap: wrap;
    padding: 0.75rem 1.1rem;
    border-bottom: 1px solid var(--td-rule);
    background: var(--td-raised);
    font-size: 0.75rem;
    color: var(--td-muted);
  }

  .dlg-actions {
    display: flex;
    gap: 0.35rem;
  }

  .dlg-actions button {
    min-height: 2rem;
    padding: 0 0.55rem;
    border: 1px solid var(--td-rule);
    background: var(--td-surface);
    color: var(--td-ink);
    font: inherit;
    cursor: pointer;
    transition:
      border-color 120ms var(--ease-swift),
      color 120ms var(--ease-swift);
  }

  .dlg-actions button:hover:not(:disabled),
  .dlg-actions button:focus-visible {
    border-color: var(--td-accent);
    color: var(--td-accent);
  }

  .dlg-actions button:focus-visible,
  .dlg-links a:focus-visible {
    outline: 2px solid var(--td-accent);
    outline-offset: 2px;
  }

  .dlg-actions button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .dlg-body {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 1.25rem 1.25rem 2rem;
  }

  h2 {
    margin: 0 0 1rem;
    font-size: clamp(1.1rem, 2.5vw, 1.35rem);
    line-height: 1.3;
    font-weight: 700;
    color: var(--td-ink-bright);
  }

  .dlg-meta {
    margin: 0 0 1.25rem;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    border-top: 1px solid var(--td-rule-soft);
    border-left: 1px solid var(--td-rule-soft);
  }

  .dlg-meta div {
    padding: 0.55rem 0.65rem;
    border-right: 1px solid var(--td-rule-soft);
    border-bottom: 1px solid var(--td-rule-soft);
    min-width: 0;
  }

  .dlg-meta dt {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--td-faint);
  }

  .dlg-meta dd {
    margin: 0.2rem 0 0;
    font-size: 0.82rem;
    color: var(--td-ink);
    overflow-wrap: anywhere;
  }

  .dlg-meta dd.band-pos {
    color: var(--td-pos);
  }
  .dlg-meta dd.band-neu {
    color: var(--td-neu);
  }
  .dlg-meta dd.band-neg {
    color: var(--td-neg);
  }

  h3 {
    margin: 1.3rem 0 0.5rem;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--td-faint);
  }

  .dlg-summary {
    margin: 0;
    font-size: 0.88rem;
    line-height: 1.55;
    color: var(--td-ink);
  }

  .dlg-note {
    margin: 0;
    font-size: 0.82rem;
    color: var(--td-muted);
  }

  .dlg-quotes {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 0.75rem;
  }

  .dlg-quotes li {
    border-inline-start: 2px solid var(--td-accent);
    padding: 0.45rem 0.75rem;
    background: var(--td-ground);
  }

  .dlg-quotes p {
    margin: 0;
    font-size: 0.84rem;
    line-height: 1.55;
    color: var(--td-ink);
  }

  .dlg-links {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem 1.25rem;
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid var(--td-rule-soft);
    font-size: 0.82rem;
  }

  .dlg-links a {
    color: var(--td-accent);
    text-decoration: underline;
    text-underline-offset: 0.2em;
  }

  @keyframes dlg-slide-in {
    from {
      transform: translateX(100%);
    }
  }

  @keyframes dlg-slide-up {
    from {
      transform: translateY(100%);
    }
  }

  @media (max-width: 640px) {
    .dlg {
      inset: auto 0 0 0;
      width: 100%;
      height: auto;
      max-height: 88dvh;
      border-inline-start: 0;
      border-top: 1px solid var(--td-rule);
    }

    .dlg[open] {
      animation-name: dlg-slide-up;
    }

    .dlg-meta {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  :global(html.fx-off) .dlg[open],
  :global(html.fx-off) .dlg-actions button {
    animation: none;
    transition: none;
  }

  @media (prefers-reduced-motion: reduce) {
    .dlg[open],
    .dlg-actions button {
      animation: none;
      transition: none;
    }
  }
</style>
