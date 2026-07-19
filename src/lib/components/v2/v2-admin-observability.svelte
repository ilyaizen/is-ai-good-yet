<script lang="ts">
  import type {
    V2AdminData,
    V2AdminStoryDetails,
    V2AnalysisRun,
    V2DimensionAnalysis
  } from "$lib/server/v2-admin-data";

  let { data }: { data: V2AdminData } = $props();
  let storyDetails = $state<Record<number, V2AdminStoryDetails>>({});
  let storyLoading = $state<Record<number, boolean>>({});
  let storyErrors = $state<Record<number, string>>({});
  // Refs to each <details> element so expand-all / collapse-all can flip them
  // without relying on a shared boolean (native details keeps its own state).
  let storyRows = $state<Array<HTMLDetailsElement>>([]);
  let allOpen = $state(false);

  function setAllStoriesOpen(open: boolean): void {
    for (const el of storyRows) {
      if (el.open !== open) el.open = open;
    }
    allOpen = open;
  }

  async function loadStoryDetails(storyId: number): Promise<void> {
    if (storyDetails[storyId] || storyLoading[storyId]) return;

    storyLoading[storyId] = true;
    delete storyErrors[storyId];
    try {
      const response = await fetch(`/api/v2/admin/stories/${storyId}`);
      if (!response.ok) throw new Error(`Story details request failed (${response.status}).`);
      const payload = (await response.json()) as { story: V2AdminStoryDetails };
      storyDetails[storyId] = payload.story;
    } catch (error) {
      storyErrors[storyId] = error instanceof Error ? error.message : "Story details request failed.";
    } finally {
      storyLoading[storyId] = false;
    }
  }

  function handleStoryToggle(event: Event, storyId: number): void {
    if ((event.currentTarget as HTMLDetailsElement).open) void loadStoryDetails(storyId);
  }

  function formatNumber(value: number): string {
    return new Intl.NumberFormat("en-US").format(value);
  }

  function formatTimestamp(value: string | null): string {
    if (!value) return "—";
    return new Date(value).toLocaleString("en-GB", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "UTC"
    });
  }

  function formatHnTimestamp(seconds: number): string {
    if (!seconds) return "—";
    return new Date(seconds * 1000).toLocaleDateString("en-GB", {
      year: "numeric",
      month: "short",
      day: "2-digit"
    });
  }

  function formatDuration(ms: number | null | undefined): string {
    if (ms === null || ms === undefined || !Number.isFinite(ms) || ms <= 0) return "—";
    if (ms < 1000) return `${Math.round(ms)} ms`;
    const seconds = ms / 1000;
    if (seconds < 60) return `${seconds.toFixed(1)} s`;
    const minutes = Math.floor(seconds / 60);
    const rem = Math.round(seconds - minutes * 60);
    return `${minutes}m ${rem}s`;
  }

  function formatSeconds(totalSeconds: number | null | undefined): string {
    if (totalSeconds === null || totalSeconds === undefined || !Number.isFinite(totalSeconds) || totalSeconds <= 0) return "—";
    if (totalSeconds < 60) return `${totalSeconds.toFixed(1)} s`;
    const minutes = Math.floor(totalSeconds / 60);
    const rem = Math.round(totalSeconds - minutes * 60);
    return `${minutes}m ${rem}s`;
  }

  function formatTokens(n: number): string {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
    return String(n);
  }

  // Maps a persisted status to a shared .v2-status tone class (see v2.css).
  function statusTone(status: string | null | undefined): string {
    if (status === "accepted" || status === "succeeded") return "v2-status--ok";
    if (status === "running" || status === "partial") return "v2-status--live";
    if (status === "failed" || status === "rejected") return "v2-status--bad";
    return "";
  }

  function score(value: number | null): string {
    if (value === null) return "N/A";
    return `${value > 0 ? "+" : ""}${value.toFixed(2)}`;
  }

  function resultSummary(run: V2AnalysisRun | null): string {
    if (!run) return "Not analyzed";
    return typeof run.result.summary === "string" ? run.result.summary : run.reason || "No summary persisted.";
  }

  function dimensionsForSource(dimensions: V2DimensionAnalysis[], source: string): V2DimensionAnalysis[] {
    return dimensions.filter((dimension) => dimension.source === source);
  }

  function pretty(value: Record<string, unknown>): string {
    return JSON.stringify(value, null, 2);
  }
</script>

<svelte:head>
  <title>V2 operations · Is AI Good Yet?</title>
</svelte:head>

<!--
  Three .v2-card sections in priority order: observatory (health at a glance),
  orchestration (run ledger), then the story ledger (deep dive). The shell bar
  (nav + logout) lives in +layout.svelte, not in the hero card.
-->
<div class="v2-admin-shell mx-auto max-w-[96rem] px-4 pt-8 sm:px-6 lg:px-8">
  <!-- Observatory card: page header (kicker + hero title + lede) with the
       KPI strip as its body. Same .v2-card chrome as the methodology card. -->
  <section class="v2-card">
    <header class="v2-card__head">
      <p class="v2-card__kicker">Observability</p>
      <div class="v2-card__head-row">
        <div>
          <h1 class="v2-card__title v2-card__title--hero">Analysis observatory</h1>
          <p class="v2-card__lede">
            Live V2 state from the pipeline database — per-story runs, provenance, and orchestration.
          </p>
        </div>
        <span class="v2-card__chip {data.available ? 'v2-status--ok' : 'v2-status--bad'}">
          {data.available ? "DB live" : "DB unavailable"}
        </span>
      </div>
    </header>

    {#if !data.available}
      <div class="v2-admin-empty">
        <strong>V2 tables are unavailable.</strong>
        <p>The production pipeline database has not exposed the complete V2 schema yet.</p>
      </div>
    {:else}
      <div class="v2-grid v2-admin-metrics" aria-label="V2 analysis totals">
        <article><span>Eligible stories</span><strong>{formatNumber(data.summary.eligibleStories)}</strong><small>passed prefilter</small></article>
        <article><span>Article analyses</span><strong>{formatNumber(data.summary.articleAccepted)}</strong><small>accepted runs</small></article>
        <article><span>Community analyses</span><strong>{formatNumber(data.summary.communityAccepted)}</strong><small>accepted aggregates</small></article>
        <article><span>Comment analyses</span><strong>{formatNumber(data.summary.commentsAccepted)}</strong><small>accepted comments</small></article>
        <article><span>Failed analyses</span><strong>{formatNumber(data.summary.failedAnalyses)}</strong><small>persisted failures</small></article>
        <article><span>Saved tokens</span><strong>{formatNumber(data.summary.inputTokens + data.summary.outputTokens)}</strong><small>{formatNumber(data.summary.inputTokens)} in · {formatNumber(data.summary.outputTokens)} out</small></article>
      </div>
    {/if}
  </section>

  {#if data.available}
    <section class="v2-card v2-admin-runs" aria-labelledby="v2-run-ledger-title">
      <header class="v2-card__head">
        <p class="v2-card__kicker">Orchestration</p>
        <div class="v2-card__head-row">
          <div>
            <h2 id="v2-run-ledger-title" class="v2-card__title">V2 run ledger</h2>
            <p class="v2-card__lede">
              Pipeline-level runs from the <code>v2_orchestration_runs</code> table.
            </p>
          </div>
        </div>
      </header>
      <div class="v2-admin-table-wrap">
        <table class="v2-admin-table">
          <thead><tr><th>Run</th><th>Status</th><th>Last stage</th><th>Started</th><th>Finished</th><th class="v2-admin-num">Duration</th><th class="v2-admin-num">Stories</th><th class="v2-admin-num">Articles</th><th class="v2-admin-num">Comments</th><th>Error</th></tr></thead>
          <tbody>
            {#each data.orchestrationRuns as run (run.runId)}
              {@const durationSec = run.startedAt && run.finishedAt
                ? (new Date(run.finishedAt).getTime() - new Date(run.startedAt).getTime()) / 1000
                : null}
              <tr>
                <td title={run.runId}>{run.runId.slice(0, 10)}</td>
                <td><span class="v2-status {statusTone(run.status)}">{run.status}</span></td>
                <td>{run.stage}</td>
                <td>{formatTimestamp(run.startedAt)}</td>
                <td>{formatTimestamp(run.finishedAt)}</td>
                <td class="v2-admin-num">{formatSeconds(durationSec)}</td>
                <td class="v2-admin-num">{run.storiesDiscovered}</td>
                <td class="v2-admin-num">{run.articlesProcessed}</td>
                <td class="v2-admin-num">{run.commentsAnalyzed}</td>
                <td>{run.errorCode ?? "—"}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

    <section class="v2-card v2-admin-stories" aria-labelledby="v2-story-ledger-title">
      <header class="v2-card__head">
        <p class="v2-card__kicker">Analysis ledger</p>
        <div class="v2-card__head-row">
          <div>
            <h2 id="v2-story-ledger-title" class="v2-card__title">Every persisted V2 property</h2>
            <p class="v2-card__lede">
              Lightweight run state up front. Full properties and exact result JSON load only when a story is opened.
            </p>
          </div>
          <div class="v2-admin-ledger-actions">
            <b class="v2-admin-count">{data.stories.length} stories</b>
            {#if data.stories.length}
              <button
                type="button"
                class="v2-admin-toggle-all"
                onclick={() => setAllStoriesOpen(!allOpen)}
                aria-pressed={allOpen}
              >
                {allOpen ? "Collapse all" : "Expand all"}
              </button>
            {/if}
          </div>
        </div>
      </header>

      <div class="v2-admin-story-list">
        {#each data.stories as story, i (story.hnStoryId)}
          <details
            class="v2-admin-story"
            bind:this={storyRows[i]}
            ontoggle={(event) => handleStoryToggle(event, story.hnStoryId)}
          >
            <summary>
              <div class="v2-admin-story__identity">
                <div class="v2-admin-story__kicker">
                  <span>HN {story.hnStoryId}</span>
                  {#if story.hnTimestamp}
                    <time datetime={new Date(story.hnTimestamp * 1000).toISOString()}>
                      {formatHnTimestamp(story.hnTimestamp)}
                    </time>
                  {/if}
                  {#if story.eligible === null}
                    <span class="v2-status">Not checked</span>
                  {:else if story.eligible}
                    <span class="v2-status v2-status--ok">Eligible</span>
                  {:else}
                    <span class="v2-status v2-status--bad">Rejected</span>
                  {/if}
                </div>
                <strong>
                  <a href={story.url} target="_blank" rel="noopener noreferrer" title={story.url}>
                    {story.title}
                  </a>
                </strong>
                <small>
                  {story.hnScore} pts · {story.hnComments} comments
                  {#if story.scopes.length}
                    <span class="v2-admin-scopes">
                      {#each story.scopes as scope (scope)}
                        <span class="v2-admin-scope">{scope}</span>
                      {/each}
                    </span>
                  {/if}
                </small>
              </div>
              <div class="v2-admin-story__states">
                <span class="v2-status {statusTone(story.articleStatus)}">ARTICLE {story.articleStatus ?? "missing"}</span>
                <span class="v2-status {statusTone(story.communityStatus)}">COMMUNITY {story.communityStatus ?? "missing"}</span>
                <i aria-hidden="true" class="v2-admin-story__chevron">⌄</i>
              </div>
            </summary>

            <div class="v2-admin-story__body">
              {#if storyLoading[story.hnStoryId]}
                <p class="v2-admin-loading">Loading exact persisted properties…</p>
              {:else if storyErrors[story.hnStoryId]}
                <div class="v2-admin-load-error">
                  <span>{storyErrors[story.hnStoryId]}</span>
                  <button type="button" onclick={() => loadStoryDetails(story.hnStoryId)}>Retry</button>
                </div>
              {:else if storyDetails[story.hnStoryId]}
                {@const details = storyDetails[story.hnStoryId]}
                <div class="v2-grid v2-grid--framed v2-admin-prefilter">
                  <div><span>Eligibility</span><strong>{story.eligible === null ? "Not checked" : story.eligible ? "Eligible" : "Rejected"}</strong></div>
                  <div><span>Reason code</span><strong>{details.prefilterReasonCode ?? "—"}</strong></div>
                  <div><span>Prefilter model</span><strong>{details.prefilterModel ?? "—"}</strong></div>
                  <div><span>Decision time</span><strong>{formatTimestamp(details.decidedAt)}</strong></div>
                  <div><span>Selected / accepted comments</span><strong>{story.selectedComments} / {story.acceptedComments}</strong></div>
                  <p>{details.prefilterReason ?? "No prefilter reason persisted."}</p>
                </div>

                <div class="v2-admin-source-grid">
                  {#each [["article", details.article], ["community", details.community]] as [source, run]}
                    <article class="v2-admin-source">
                      <header>
                        <div><span>{String(source).toUpperCase()}</span><strong>{resultSummary(run as V2AnalysisRun | null)}</strong></div>
                        <b class="v2-status {statusTone((run as V2AnalysisRun | null)?.status)}">{(run as V2AnalysisRun | null)?.status ?? "missing"}</b>
                      </header>
                      {#if run}
                        {@const analysis = run as V2AnalysisRun}
                        <dl class="v2-grid v2-kv">
                          <div><dt>Model</dt><dd>{analysis.model}</dd></div>
                          <div><dt>Analysis / parser</dt><dd>{analysis.analysisVersion} / {analysis.parserVersion}</dd></div>
                          <div><dt>Contract</dt><dd>{analysis.contractVersion}</dd></div>
                          <div><dt>Prompt</dt><dd>{analysis.promptVersion}</dd></div>
                          <div><dt>Selection</dt><dd>{analysis.selectionVersion || "N/A"}</dd></div>
                          <div><dt>Analyzed</dt><dd>{formatTimestamp(analysis.analyzedAt)}</dd></div>
                          <div><dt>Provenance</dt><dd title={`prompt ${analysis.promptHash} · input ${analysis.inputHash}`}>{analysis.promptHash.slice(0, 10)} · {analysis.inputHash.slice(0, 10)}</dd></div>
                        </dl>

                        <div class="v2-grid v2-admin-metric-strip" aria-label={`${source} run metrics`}>
                          <div class="v2-admin-metric">
                            <span>Input tokens</span>
                            <strong>{formatTokens(analysis.metrics.inputTokens)}</strong>
                          </div>
                          <div class="v2-admin-metric">
                            <span>Output tokens</span>
                            <strong>{formatTokens(analysis.metrics.outputTokens)}</strong>
                          </div>
                          <div class="v2-admin-metric">
                            <span>Inference</span>
                            <strong>{formatDuration(analysis.metrics.inferenceTimeMs)}</strong>
                          </div>
                          <div class="v2-admin-metric">
                            <span>Total tokens</span>
                            <strong>{formatTokens(analysis.metrics.inputTokens + analysis.metrics.outputTokens)}</strong>
                          </div>
                        </div>

                        <div class="v2-admin-dimensions">
                          {#each dimensionsForSource(details.dimensions, String(source)) as dimension (`${dimension.source}-${dimension.dimension}`)}
                            <section>
                              <div><span>{dimension.dimension}</span><strong>{score(dimension.score)}</strong></div>
                              <small>
                                {dimension.applicability} · confidence {(dimension.confidence * 100).toFixed(0)}% · {dimension.evidenceCount} evidence
                              </small>
                              <div
                                class="v2-admin-conf-bar"
                                role="img"
                                aria-label={`confidence ${Math.round(dimension.confidence * 100)}%`}
                              >
                                <span style={`width: ${Math.max(4, Math.min(100, Math.round(dimension.confidence * 100)))}%`}></span>
                              </div>
                              <p>{dimension.rationale || "No rationale persisted."}</p>
                            </section>
                          {/each}
                        </div>

                        <details class="v2-code v2-code--flat v2-admin-json">
                          <summary>Raw JSON · tokens, inference, parameters, full result</summary>
                          <pre>{pretty(analysis.result)}</pre>
                        </details>
                      {:else}
                        <p class="v2-admin-missing">No {source} analysis has been persisted for this story.</p>
                      {/if}
                    </article>
                  {/each}
                </div>

                {#if details.articleText !== null}
                  <details class="v2-code v2-admin-text">
                    <summary>Article body · prefilter input <small>{details.articleText.length.toLocaleString()} chars</small></summary>
                    <pre>{details.articleText}</pre>
                  </details>
                {:else}
                  <p class="v2-admin-missing">Article body text is not stored for this story.</p>
                {/if}

                {#if details.comments.length}
                  <div class="v2-admin-comments">
                    <div class="v2-admin-comments__head">
                      <span>Selected comments</span>
                      <b class="v2-admin-count">{details.comments.length} analyzed</b>
                    </div>
                    {#each details.comments as comment (comment.hnCommentId)}
                      <article class="v2-admin-comment">
                        <header>
                          <span>{comment.author}</span>
                          <b class="v2-status {statusTone(comment.analysisStatus)}">{comment.analysisStatus ?? "not analyzed"}</b>
                        </header>
                        <p>{comment.text}</p>
                        {#if comment.selectionReason}
                          <small>selected · {comment.selectionReason}</small>
                        {/if}
                        {#if Object.keys(comment.analysisResult).length}
                          <details class="v2-code v2-code--flat v2-admin-json">
                            <summary>Raw result</summary>
                            <pre>{pretty(comment.analysisResult)}</pre>
                          </details>
                        {/if}
                      </article>
                    {/each}
                  </div>
                {:else}
                  <p class="v2-admin-missing">No comments were selected for this story.</p>
                {/if}
              {/if}
            </div>
          </details>
        {/each}
      </div>
    </section>
  {/if}
</div>

<style>
  .v2-admin-shell {
    display: flex;
    flex-direction: column;
    color: var(--v2-text);
    font-feature-settings: "cv01", "ss03";
  }
  /* Stack the cards with the same rhythm. */
  .v2-admin-shell > * + * {
    margin-top: 1.25rem;
  }
  /* Priority order: observatory (0) → orchestration → story ledger (deep dive last). */
  .v2-admin-runs {
    order: 1;
  }
  .v2-admin-stories {
    order: 2;
  }

  /* KPI strip — content layer over .v2-grid (the grid mechanism lives there). */
  .v2-admin-metrics {
    --v2-grid-cols: 6;
  }
  .v2-admin-metrics article {
    padding: 1rem;
  }
  .v2-admin-metrics span {
    color: var(--v2-text-faint);
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
  }
  .v2-admin-metrics strong {
    display: block;
    margin-top: 0.6rem;
    font:
      510 1.75rem/1 ui-monospace,
      monospace;
  }
  .v2-admin-metrics small {
    display: block;
    overflow: hidden;
    margin-top: 0.45rem;
    color: var(--v2-text-muted);
    font-size: 0.69rem;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Count badge — right slot of the ledger head-row. */
  .v2-admin-count {
    align-self: flex-start;
    border: 1px solid var(--v2-separator);
    border-radius: 0.3rem;
    padding: 0.25rem 0.55rem;
    color: var(--v2-text-muted);
    font:
      500 0.68rem ui-monospace,
      monospace;
  }

  /* Ledger actions = count + expand/collapse-all, grouped at the right edge. */
  .v2-admin-ledger-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    align-self: flex-start;
  }
  .v2-admin-toggle-all {
    border: 1px solid var(--v2-separator);
    border-radius: 0.3rem;
    background: color-mix(in srgb, var(--v2-text) 3%, transparent);
    padding: 0.3rem 0.65rem;
    color: var(--v2-text-muted);
    font:
      500 0.68rem ui-monospace,
      monospace;
    cursor: pointer;
    transition: 0.15s ease;
  }
  .v2-admin-toggle-all:hover {
    border-color: var(--v2-phosphor);
    color: var(--v2-text);
  }
  .v2-admin-toggle-all[aria-pressed="true"] {
    border-color: color-mix(in oklch, var(--v2-phosphor) 35%, transparent);
    color: var(--v2-phosphor);
  }

  .v2-admin-story {
    border-bottom: 1px solid var(--v2-separator-quiet);
  }
  .v2-admin-story:last-child {
    border: 0;
  }
  .v2-admin-story > summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 1rem 1.25rem;
    cursor: pointer;
    list-style: none;
  }
  .v2-admin-story > summary::-webkit-details-marker {
    display: none;
  }
  .v2-admin-story > summary:hover {
    background: color-mix(in srgb, var(--v2-text) 2.5%, transparent);
  }
  .v2-admin-story__identity {
    display: grid;
    min-width: 0;
    gap: 0.3rem;
  }
  /* Kicker line: HN id · date · eligibility badge */
  .v2-admin-story__kicker {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.55rem;
  }
  .v2-admin-story__kicker > span:first-child {
    color: var(--v2-phosphor);
    font:
      500 0.65rem ui-monospace,
      monospace;
  }
  .v2-admin-story__kicker time {
    color: var(--v2-text-faint);
    font:
      500 0.65rem ui-monospace,
      monospace;
  }
  .v2-admin-story__identity strong {
    overflow: hidden;
    font-size: 0.9rem;
    font-weight: 510;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .v2-admin-story__identity strong a {
    color: inherit;
    text-decoration: none;
  }
  .v2-admin-story__identity strong a:hover {
    color: var(--v2-phosphor);
  }
  .v2-admin-story__identity small {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.35rem 0.55rem;
    color: var(--v2-text-faint);
    font-size: 0.7rem;
  }
  /* Scope chips in summary */
  .v2-admin-scopes {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 0.25rem;
  }
  .v2-admin-scope {
    padding: 0.1rem 0.4rem;
    background: var(--v2-recess);
    border: 1px solid var(--v2-separator-quiet);
    color: var(--v2-text-muted);
    font:
      500 0.58rem ui-monospace,
      monospace;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .v2-admin-story__states {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    white-space: nowrap;
  }
  .v2-admin-story__chevron {
    color: var(--v2-text-faint);
    transition: transform 0.15s ease;
    line-height: 1;
  }
  .v2-admin-story[open] .v2-admin-story__chevron {
    transform: rotate(180deg);
  }

  /* Prefilter grid — content layer over .v2-grid. */
  .v2-admin-prefilter {
    --v2-grid-cols: 5;
  }
  .v2-admin-prefilter > div {
    padding: 0.8rem;
  }
  .v2-admin-prefilter span {
    color: var(--v2-text-faint);
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
  }
  .v2-admin-prefilter strong {
    display: block;
    overflow: hidden;
    margin-top: 0.35rem;
    font:
      500 0.72rem ui-monospace,
      monospace;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .v2-admin-prefilter > p {
    grid-column: 1 / -1;
    margin: 0;
    padding: 0.8rem;
    color: var(--v2-text-muted);
    font-size: 0.75rem;
    line-height: 1.55;
  }

  /* Metric strip — content layer over .v2-grid; border-top separates it from the dl above. */
  .v2-admin-metric-strip {
    --v2-grid-cols: 4;
    border-top: 1px solid var(--v2-separator-quiet);
  }
  .v2-admin-metric {
    padding: 0.65rem 1rem;
  }
  .v2-admin-metric span {
    color: var(--v2-text-faint);
    font:
      500 0.6rem ui-monospace,
      monospace;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  .v2-admin-metric strong {
    display: block;
    margin-top: 0.3rem;
    color: var(--v2-phosphor);
    font:
      510 0.82rem ui-monospace,
      monospace;
  }

  /* Confidence bar inside dimension section */
  .v2-admin-conf-bar {
    height: 0.25rem;
    margin-top: 0.5rem;
    background: var(--v2-separator-quiet);
    border-radius: 1rem;
    overflow: hidden;
  }
  .v2-admin-conf-bar span {
    display: block;
    height: 100%;
    background: color-mix(in oklch, var(--v2-phosphor) 70%, transparent);
  }

  /* Numeric table cells */
  .v2-admin-table .v2-admin-num {
    text-align: right;
  }
  .v2-admin-story__body {
    padding: 0 1.25rem 1.25rem;
  }
  .v2-admin-loading,
  .v2-admin-load-error {
    margin: 0;
    padding: 1rem;
    border: 1px solid var(--v2-separator-quiet);
    border-radius: 0.5rem;
    background: var(--v2-recess);
    color: var(--v2-text-muted);
    font-size: 0.75rem;
  }
  .v2-admin-load-error {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    color: var(--v2-red);
  }
  .v2-admin-load-error button {
    border: 1px solid var(--v2-separator);
    border-radius: 0.35rem;
    padding: 0.35rem 0.6rem;
    color: var(--v2-text-muted);
  }
  .v2-admin-source-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.75rem;
    margin-top: 0.75rem;
  }
  .v2-admin-source {
    min-width: 0;
    border: 1px solid var(--v2-separator-quiet);
    border-radius: 0.5rem;
    background: var(--v2-recess);
    overflow: hidden;
  }
  .v2-admin-source > header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding: 1rem;
    border-bottom: 1px solid var(--v2-separator-quiet);
  }
  .v2-admin-source > header > div {
    display: grid;
    gap: 0.35rem;
  }
  .v2-admin-source > header span {
    color: var(--v2-phosphor);
    font:
      500 0.65rem ui-monospace,
      monospace;
    letter-spacing: 0.15em;
  }
  .v2-admin-source > header strong {
    color: var(--v2-text-muted);
    font-size: 0.76rem;
    font-weight: 400;
    line-height: 1.5;
  }
  .v2-admin-dimensions {
    display: grid;
    gap: 0.5rem;
    padding: 0.75rem;
  }
  .v2-admin-dimensions section {
    padding: 0.75rem;
    border: 1px solid var(--v2-separator-quiet);
    border-radius: 0.4rem;
  }
  .v2-admin-dimensions section > div {
    display: flex;
    justify-content: space-between;
  }
  .v2-admin-dimensions span {
    text-transform: uppercase;
    font:
      500 0.66rem ui-monospace,
      monospace;
  }
  .v2-admin-dimensions strong {
    color: var(--v2-phosphor);
    font:
      500 0.78rem ui-monospace,
      monospace;
  }
  .v2-admin-dimensions small {
    display: block;
    margin-top: 0.35rem;
    color: var(--v2-text-faint);
    font-size: 0.66rem;
  }
  .v2-admin-dimensions p {
    margin-top: 0.55rem;
    color: var(--v2-text-muted);
    font-size: 0.72rem;
    line-height: 1.5;
  }

  /* Raw JSON: keep horizontal scroll (long lines), shrink inside comments. */
  .v2-admin-json > pre {
    white-space: pre;
  }
  .v2-admin-comment .v2-admin-json {
    margin-top: 0.5rem;
  }
  .v2-admin-comment .v2-admin-json summary {
    padding: 0.4rem 0;
    font-size: 0.62rem;
  }
  .v2-admin-comment .v2-admin-json pre {
    max-height: 16rem;
    font-size: 0.62rem;
  }

  /* Article body: readable prose font, not mono. */
  .v2-admin-text > summary small {
    margin-left: 0.5rem;
    color: var(--v2-text-faint);
    font-size: 0.62rem;
    font-weight: 400;
  }
  .v2-admin-text > pre {
    font-family: var(--v2-font-copy);
    font-size: 0.72rem;
  }

  .v2-admin-missing {
    padding: 1rem;
    color: var(--v2-text-faint);
    font-size: 0.75rem;
  }

  /* Surfaced scraped/analyzed text — selected comments. */
  .v2-admin-comments {
    margin-top: 0.75rem;
  }
  .v2-admin-comments__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 0.5rem;
  }
  .v2-admin-comments__head span {
    color: var(--v2-text-faint);
    font:
      500 0.66rem ui-monospace,
      monospace;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }
  .v2-admin-comment {
    padding: 0.75rem 1rem;
    border: 1px solid var(--v2-separator-quiet);
    border-radius: 0.4rem;
    background: var(--v2-recess);
  }
  .v2-admin-comment + .v2-admin-comment {
    margin-top: 0.5rem;
  }
  .v2-admin-comment header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }
  .v2-admin-comment header span {
    color: var(--v2-phosphor);
    font:
      500 0.66rem ui-monospace,
      monospace;
  }
  .v2-admin-comment p {
    margin: 0.5rem 0 0;
    color: var(--v2-text-muted);
    font:
      0.78rem/1.55 var(--v2-font-copy);
    overflow-wrap: anywhere;
  }
  .v2-admin-comment small {
    display: block;
    margin-top: 0.4rem;
    color: var(--v2-text-faint);
    font-size: 0.64rem;
  }

  .v2-admin-table-wrap {
    overflow-x: auto;
  }
  .v2-admin-table {
    width: 100%;
    min-width: 68rem;
    border-collapse: collapse;
    font-size: 0.72rem;
  }
  .v2-admin-table th,
  .v2-admin-table td {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--v2-separator-quiet);
    text-align: left;
    white-space: nowrap;
  }
  .v2-admin-table th {
    color: var(--v2-text-faint);
    font:
      500 0.65rem ui-monospace,
      monospace;
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
  .v2-admin-table td {
    color: var(--v2-text-muted);
    font-family: ui-monospace, monospace;
  }

  .v2-admin-empty {
    padding: 2rem;
  }
  .v2-admin-empty strong {
    color: var(--v2-text);
  }
  .v2-admin-empty p {
    margin-top: 0.5rem;
    color: var(--v2-text-muted);
  }

  @media (max-width: 1100px) {
    .v2-admin-metrics {
      --v2-grid-cols: 3;
    }
    .v2-admin-prefilter {
      --v2-grid-cols: 2;
    }
    .v2-admin-metric-strip {
      --v2-grid-cols: 2;
    }
  }
  @media (max-width: 800px) {
    .v2-admin-source-grid {
      grid-template-columns: 1fr;
    }
    .v2-admin-story > summary {
      align-items: start;
      flex-direction: column;
    }
    .v2-admin-story__states {
      width: 100%;
      overflow-x: auto;
    }
  }
  @media (max-width: 560px) {
    .v2-admin-metrics {
      --v2-grid-cols: 2;
    }
    .v2-admin-prefilter {
      --v2-grid-cols: 1;
    }
    .v2-admin-source dl {
      --v2-grid-cols: 1;
    }
    .v2-admin-metric-strip {
      --v2-grid-cols: 1;
    }
  }
</style>
