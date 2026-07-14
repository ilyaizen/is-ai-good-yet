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

  function statusTone(status: string | null | undefined): string {
    if (status === "accepted" || status === "succeeded") return "v2-admin-status--success";
    if (status === "running" || status === "partial") return "v2-admin-status--active";
    if (status === "failed" || status === "rejected") return "v2-admin-status--failed";
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

<div class="v2-admin-shell mx-auto max-w-[96rem] px-4 pt-8 sm:px-6 lg:px-8">
  <header class="v2-admin-hero">
    <div>
      <div class="v2-admin-kicker"><span></span> V2 CONTROL PLANE</div>
      <h1>Analysis observatory</h1>
      <p>Actual V2 state from SQLite. No V1 counters, no generic status theater.</p>
    </div>
    <div class="v2-admin-hero__actions">
      <a href="/v2">Public dashboard</a>
      <a href="#v2-methodology-title">Methodology</a>
      <form method="post" action="?/logout">
        <button type="submit">Log out</button>
      </form>
    </div>
  </header>

  {#if !data.available}
    <section class="v2-admin-empty">
      <strong>V2 tables are unavailable.</strong>
      <p>The production pipeline database has not exposed the complete V2 schema yet.</p>
    </section>
  {:else}
    <section class="v2-admin-metrics" aria-label="V2 analysis totals">
      <article><span>Eligible stories</span><strong>{formatNumber(data.summary.eligibleStories)}</strong><small>passed prefilter</small></article>
      <article><span>Article analyses</span><strong>{formatNumber(data.summary.articleAccepted)}</strong><small>accepted runs</small></article>
      <article><span>Community analyses</span><strong>{formatNumber(data.summary.communityAccepted)}</strong><small>accepted aggregates</small></article>
      <article><span>Comment analyses</span><strong>{formatNumber(data.summary.commentsAccepted)}</strong><small>accepted comments</small></article>
      <article><span>Failed analyses</span><strong>{formatNumber(data.summary.failedAnalyses)}</strong><small>persisted failures</small></article>
      <article><span>Saved tokens</span><strong>{formatNumber(data.summary.inputTokens + data.summary.outputTokens)}</strong><small>{formatNumber(data.summary.inputTokens)} in · {formatNumber(data.summary.outputTokens)} out</small></article>
    </section>

    <section class="v2-admin-section" aria-labelledby="v2-story-ledger-title">
      <div class="v2-admin-section__head">
        <div>
          <span>ANALYSIS LEDGER</span>
          <h2 id="v2-story-ledger-title">Every persisted V2 property</h2>
          <p>Lightweight run state up front. Full properties and exact result JSON load only when a story is opened.</p>
        </div>
        <b>{data.stories.length} stories</b>
      </div>

      <div class="v2-admin-story-list">
        {#each data.stories as story (story.hnStoryId)}
          <details class="v2-admin-story" ontoggle={(event) => handleStoryToggle(event, story.hnStoryId)}>
            <summary>
              <div class="v2-admin-story__identity">
                <span>HN {story.hnStoryId}</span>
                <strong>{story.title}</strong>
                <small>{story.hnScore} points · {story.hnComments} comments · {story.scopes.join(" · ") || "no scopes"}</small>
              </div>
              <div class="v2-admin-story__states">
                <span class={statusTone(story.articleStatus)}>ARTICLE {story.articleStatus ?? "missing"}</span>
                <span class={statusTone(story.communityStatus)}>COMMUNITY {story.communityStatus ?? "missing"}</span>
                <i aria-hidden="true">⌄</i>
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
                <div class="v2-admin-prefilter">
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
                        <b class={statusTone((run as V2AnalysisRun | null)?.status)}>{(run as V2AnalysisRun | null)?.status ?? "missing"}</b>
                      </header>
                      {#if run}
                        {@const analysis = run as V2AnalysisRun}
                        <dl>
                          <div><dt>Model</dt><dd>{analysis.model}</dd></div>
                          <div><dt>Analysis / parser</dt><dd>{analysis.analysisVersion} / {analysis.parserVersion}</dd></div>
                          <div><dt>Contract</dt><dd>{analysis.contractVersion}</dd></div>
                          <div><dt>Prompt</dt><dd>{analysis.promptVersion}</dd></div>
                          <div><dt>Selection</dt><dd>{analysis.selectionVersion || "N/A"}</dd></div>
                          <div><dt>Analyzed</dt><dd>{formatTimestamp(analysis.analyzedAt)}</dd></div>
                          <div><dt>Tokens</dt><dd>{formatNumber(analysis.metrics.inputTokens)} in · {formatNumber(analysis.metrics.outputTokens)} out</dd></div>
                          <div><dt>Inference</dt><dd>{formatNumber(Math.round(analysis.metrics.inferenceTimeMs))} ms</dd></div>
                          <div><dt>Parameters</dt><dd>{pretty(analysis.parameters)}</dd></div>
                          <div><dt>Prompt hash</dt><dd title={analysis.promptHash}>{analysis.promptHash}</dd></div>
                          <div><dt>Input hash</dt><dd title={analysis.inputHash}>{analysis.inputHash}</dd></div>
                        </dl>

                        <div class="v2-admin-dimensions">
                          {#each dimensionsForSource(details.dimensions, String(source)) as dimension (`${dimension.source}-${dimension.dimension}`)}
                            <section>
                              <div><span>{dimension.dimension}</span><strong>{score(dimension.score)}</strong></div>
                              <small>{dimension.applicability} · confidence {dimension.confidence.toFixed(2)} · {dimension.evidenceCount} evidence</small>
                              <p>{dimension.rationale || "No rationale persisted."}</p>
                            </section>
                          {/each}
                        </div>

                        <details class="v2-admin-json">
                          <summary>Exact persisted result JSON</summary>
                          <pre>{pretty(analysis.result)}</pre>
                        </details>
                      {:else}
                        <p class="v2-admin-missing">No {source} analysis has been persisted for this story.</p>
                      {/if}
                    </article>
                  {/each}
                </div>
              {/if}
            </div>
          </details>
        {/each}
      </div>
    </section>

    <section class="v2-admin-section" aria-labelledby="v2-run-ledger-title">
      <div class="v2-admin-section__head">
        <div>
          <span>ORCHESTRATION</span>
          <h2 id="v2-run-ledger-title">V2 run ledger</h2>
          <p>Pipeline-level runs from <code>v2_orchestration_runs</code>, separate from the web runner below.</p>
        </div>
      </div>
      <div class="v2-admin-table-wrap">
        <table class="v2-admin-table">
          <thead><tr><th>Run</th><th>Status</th><th>Last stage</th><th>Started</th><th>Finished</th><th>Stories</th><th>Articles</th><th>Comments</th><th>Error</th></tr></thead>
          <tbody>
            {#each data.orchestrationRuns as run (run.runId)}
              <tr>
                <td title={run.runId}>{run.runId.slice(0, 10)}</td>
                <td><span class={statusTone(run.status)}>{run.status}</span></td>
                <td>{run.stage}</td>
                <td>{formatTimestamp(run.startedAt)}</td>
                <td>{formatTimestamp(run.finishedAt)}</td>
                <td>{run.storiesDiscovered}</td>
                <td>{run.articlesProcessed}</td>
                <td>{run.commentsAnalyzed}</td>
                <td>{run.errorCode ?? "—"}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>
  {/if}
</div>

<style>
  .v2-admin-shell { color: var(--v2-text); font-feature-settings: "cv01", "ss03"; }
  .v2-admin-hero { display: flex; align-items: end; justify-content: space-between; gap: 2rem; padding: 2rem 0 1.5rem; border-bottom: 1px solid var(--v2-separator); }
  .v2-admin-kicker, .v2-admin-section__head > div > span { color: var(--v2-text-faint); font: 500 .68rem/1.4 ui-monospace, monospace; letter-spacing: .18em; }
  .v2-admin-kicker span { display: inline-block; width: .45rem; height: .45rem; margin-right: .45rem; border-radius: 50%; background: var(--v2-phosphor); box-shadow: 0 0 12px var(--v2-phosphor); }
  .v2-admin-hero h1 { margin-top: .65rem; font-size: clamp(2rem, 5vw, 3.75rem); font-weight: 510; line-height: 1; letter-spacing: -.045em; }
  .v2-admin-hero p, .v2-admin-section__head p { margin-top: .75rem; color: var(--v2-text-muted); font-size: .88rem; }
  .v2-admin-hero__actions { display: flex; flex-wrap: wrap; gap: .5rem; }
  .v2-admin-hero__actions a, .v2-admin-hero__actions button { border: 1px solid var(--v2-separator); border-radius: .4rem; background: color-mix(in srgb, var(--v2-text) 3%, transparent); padding: .55rem .8rem; color: var(--v2-text-muted); font-size: .75rem; transition: .15s ease; }
  .v2-admin-hero__actions a:hover, .v2-admin-hero__actions button:hover { border-color: var(--v2-phosphor); color: var(--v2-text); }
  .v2-admin-metrics { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); border: 1px solid var(--v2-separator); border-radius: .65rem; margin-top: 1.25rem; overflow: hidden; }
  .v2-admin-metrics article { min-width: 0; padding: 1rem; border-right: 1px solid var(--v2-separator-quiet); background: color-mix(in srgb, var(--v2-text) 2%, transparent); }
  .v2-admin-metrics article:last-child { border: 0; }
  .v2-admin-metrics span, .v2-admin-prefilter span { color: var(--v2-text-faint); font-size: .68rem; text-transform: uppercase; letter-spacing: .12em; }
  .v2-admin-metrics strong { display: block; margin-top: .6rem; font: 510 1.75rem/1 ui-monospace, monospace; }
  .v2-admin-metrics small { display: block; overflow: hidden; margin-top: .45rem; color: var(--v2-text-muted); font-size: .69rem; text-overflow: ellipsis; white-space: nowrap; }
  .v2-admin-section { margin-top: 1.25rem; border: 1px solid var(--v2-separator); border-radius: .65rem; background: color-mix(in srgb, var(--v2-text) 1.5%, transparent); overflow: hidden; }
  .v2-admin-section__head { display: flex; justify-content: space-between; gap: 1rem; padding: 1.25rem; border-bottom: 1px solid var(--v2-separator); }
  .v2-admin-section__head h2 { margin-top: .4rem; font-size: 1.35rem; font-weight: 510; letter-spacing: -.025em; }
  .v2-admin-section__head b { align-self: start; border: 1px solid var(--v2-separator); border-radius: 999px; padding: .25rem .55rem; color: var(--v2-text-muted); font: 500 .68rem ui-monospace, monospace; }
  .v2-admin-story { border-bottom: 1px solid var(--v2-separator-quiet); }
  .v2-admin-story:last-child { border: 0; }
  .v2-admin-story > summary { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 1rem 1.25rem; cursor: pointer; list-style: none; }
  .v2-admin-story > summary:hover { background: color-mix(in srgb, var(--v2-text) 2.5%, transparent); }
  .v2-admin-story__identity { display: grid; min-width: 0; gap: .25rem; }
  .v2-admin-story__identity > span { color: var(--v2-phosphor); font: 500 .65rem ui-monospace, monospace; }
  .v2-admin-story__identity strong { overflow: hidden; font-size: .9rem; font-weight: 510; text-overflow: ellipsis; white-space: nowrap; }
  .v2-admin-story__identity small { color: var(--v2-text-faint); font-size: .7rem; }
  .v2-admin-story__states { display: flex; align-items: center; gap: .45rem; white-space: nowrap; }
  .v2-admin-story__states span, .v2-admin-source header b, .v2-admin-table span { border: 1px solid var(--v2-separator); border-radius: 999px; padding: .22rem .45rem; color: var(--v2-text-muted); font: 500 .62rem ui-monospace, monospace; text-transform: uppercase; }
  .v2-admin-status--success { border-color: color-mix(in srgb, #10b981 35%, transparent) !important; color: #6ee7b7 !important; }
  .v2-admin-status--active { border-color: color-mix(in srgb, #7170ff 45%, transparent) !important; color: #a5b4fc !important; }
  .v2-admin-status--failed { border-color: color-mix(in srgb, #fb7185 35%, transparent) !important; color: #fda4af !important; }
  .v2-admin-story[open] .v2-admin-story__states i { transform: rotate(180deg); }
  .v2-admin-story__body { padding: 0 1.25rem 1.25rem; }
  .v2-admin-loading, .v2-admin-load-error { margin: 0; padding: 1rem; border: 1px solid var(--v2-separator-quiet); border-radius: .5rem; background: var(--v2-recess); color: var(--v2-text-muted); font-size: .75rem; }
  .v2-admin-load-error { display: flex; align-items: center; justify-content: space-between; gap: 1rem; color: #fda4af; }
  .v2-admin-load-error button { border: 1px solid var(--v2-separator); border-radius: .35rem; padding: .35rem .6rem; color: var(--v2-text-muted); }
  .v2-admin-prefilter { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 1px; border: 1px solid var(--v2-separator-quiet); border-radius: .5rem; background: var(--v2-separator-quiet); overflow: hidden; }
  .v2-admin-prefilter > div { min-width: 0; padding: .8rem; background: var(--v2-recess); }
  .v2-admin-prefilter strong { display: block; overflow: hidden; margin-top: .35rem; font: 500 .72rem ui-monospace, monospace; text-overflow: ellipsis; white-space: nowrap; }
  .v2-admin-prefilter > p { grid-column: 1 / -1; margin: 0; padding: .8rem; background: var(--v2-recess); color: var(--v2-text-muted); font-size: .75rem; line-height: 1.55; }
  .v2-admin-source-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .75rem; margin-top: .75rem; }
  .v2-admin-source { min-width: 0; border: 1px solid var(--v2-separator-quiet); border-radius: .5rem; background: var(--v2-recess); overflow: hidden; }
  .v2-admin-source > header { display: flex; justify-content: space-between; gap: 1rem; padding: 1rem; border-bottom: 1px solid var(--v2-separator-quiet); }
  .v2-admin-source > header > div { display: grid; gap: .35rem; }
  .v2-admin-source > header span { color: var(--v2-phosphor); font: 500 .65rem ui-monospace, monospace; letter-spacing: .15em; }
  .v2-admin-source > header strong { color: var(--v2-text-muted); font-size: .76rem; font-weight: 400; line-height: 1.5; }
  .v2-admin-source dl { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); margin: 0; }
  .v2-admin-source dl div { min-width: 0; padding: .65rem 1rem; border-bottom: 1px solid var(--v2-separator-quiet); }
  .v2-admin-source dt { color: var(--v2-text-faint); font-size: .65rem; text-transform: uppercase; letter-spacing: .1em; }
  .v2-admin-source dd { overflow: hidden; margin-top: .25rem; color: var(--v2-text-muted); font: 400 .68rem/1.45 ui-monospace, monospace; text-overflow: ellipsis; white-space: nowrap; }
  .v2-admin-dimensions { display: grid; gap: .5rem; padding: .75rem; }
  .v2-admin-dimensions section { padding: .75rem; border: 1px solid var(--v2-separator-quiet); border-radius: .4rem; }
  .v2-admin-dimensions section > div { display: flex; justify-content: space-between; }
  .v2-admin-dimensions span { text-transform: uppercase; font: 500 .66rem ui-monospace, monospace; }
  .v2-admin-dimensions strong { color: var(--v2-phosphor); font: 500 .78rem ui-monospace, monospace; }
  .v2-admin-dimensions small { display: block; margin-top: .35rem; color: var(--v2-text-faint); font-size: .66rem; }
  .v2-admin-dimensions p { margin-top: .55rem; color: var(--v2-text-muted); font-size: .72rem; line-height: 1.5; }
  .v2-admin-json { border-top: 1px solid var(--v2-separator-quiet); }
  .v2-admin-json summary { padding: .8rem 1rem; color: var(--v2-text-muted); cursor: pointer; font: 500 .68rem ui-monospace, monospace; }
  .v2-admin-json pre { max-height: 30rem; overflow: auto; margin: 0; padding: 1rem; border-top: 1px solid var(--v2-separator-quiet); color: var(--v2-text-muted); font: .68rem/1.6 ui-monospace, monospace; white-space: pre; }
  .v2-admin-missing { padding: 1rem; color: var(--v2-text-faint); font-size: .75rem; }
  .v2-admin-table-wrap { overflow-x: auto; }
  .v2-admin-table { width: 100%; min-width: 68rem; border-collapse: collapse; font-size: .72rem; }
  .v2-admin-table th, .v2-admin-table td { padding: .75rem 1rem; border-bottom: 1px solid var(--v2-separator-quiet); text-align: left; white-space: nowrap; }
  .v2-admin-table th { color: var(--v2-text-faint); font: 500 .65rem ui-monospace, monospace; text-transform: uppercase; letter-spacing: .1em; }
  .v2-admin-table td { color: var(--v2-text-muted); font-family: ui-monospace, monospace; }
  .v2-admin-empty { margin-top: 1.25rem; padding: 2rem; border: 1px dashed var(--v2-separator); border-radius: .65rem; }
  .v2-admin-empty p { margin-top: .5rem; color: var(--v2-text-muted); }
  @media (max-width: 1100px) { .v2-admin-metrics { grid-template-columns: repeat(3, 1fr); } .v2-admin-metrics article:nth-child(3) { border-right: 0; } .v2-admin-metrics article:nth-child(-n+3) { border-bottom: 1px solid var(--v2-separator-quiet); } .v2-admin-prefilter { grid-template-columns: repeat(2, 1fr); } }
  @media (max-width: 800px) { .v2-admin-hero { align-items: start; flex-direction: column; } .v2-admin-source-grid { grid-template-columns: 1fr; } .v2-admin-story > summary { align-items: start; flex-direction: column; } .v2-admin-story__states { width: 100%; overflow-x: auto; } }
  @media (max-width: 560px) { .v2-admin-metrics { grid-template-columns: repeat(2, 1fr); } .v2-admin-metrics article { border-bottom: 1px solid var(--v2-separator-quiet); } .v2-admin-metrics article:nth-child(2n) { border-right: 0; } .v2-admin-prefilter { grid-template-columns: 1fr; } .v2-admin-source dl { grid-template-columns: 1fr; } }
</style>
