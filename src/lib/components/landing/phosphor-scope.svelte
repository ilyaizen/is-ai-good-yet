<script lang="ts">
  import type { PageData } from "../../../routes/$types"
  import type { InfluentialArticle } from "$lib/server/db"
  import { cueHover, cueScrub, cueToggle } from "$lib/audio/v12-sound"
  import {
    answerFor,
    bandScore,
    chartBounds,
    formatInt,
    formatIsoDate,
    formatMediumDate,
    formatMonthLabel,
    hostnameOf,
    monthTicks,
    NO_CEILING,
    sentimentBand,
    sortStories,
    verdictBandFor,
    weeklyRange,
    YES_FLOOR,
    type StorySortKey,
  } from "./phosphor-data"
  import PhosphorFxBar from "./phosphor-fx-bar.svelte"
  import PhosphorStoryDialog from "./phosphor-story-dialog.svelte"
  import PhFlowNumber from "./ph-flow-number.svelte"
  import PhosphorMoreInfo from "./phosphor-more-info.svelte"
  import VisitorCounter from "$lib/components/visitor-counter.svelte"
  import { v12Effects } from "$lib/state/v12-effects.svelte"

  let {
    data,
    exportedAt,
    onReplay,
    replayDisabled = false,
    onDialogChange,
  }: {
    data: PageData
    exportedAt: string | null
    onReplay: () => void
    replayDisabled?: boolean
    onDialogChange?: (open: boolean) => void
  } = $props()

  const ranges: ReadonlyArray<{ days: number | null; label: string }> = [
    { days: 90, label: "90D" },
    { days: 365, label: "1Y" },
    { days: null, label: "ALL" },
  ]

  const bandFilters: ReadonlyArray<{ key: "all" | "pos" | "neu" | "neg"; label: string }> = [
    { key: "all", label: "all" },
    { key: "pos", label: "+ pos" },
    { key: "neu", label: "± neu" },
    { key: "neg", label: "− neg" },
  ]

  const sortOptions: ReadonlyArray<{ key: StorySortKey; label: string }> = [
    { key: "hn_timestamp", label: "newest first" },
    { key: "hn_score", label: "hn points" },
    { key: "hn_comments", label: "comments" },
    { key: "sentiment_score", label: "most positive" },
  ]

  const PAGE_SIZE = 10

  let days = $state<number | null>(365)
  let selectedWeek = $state<number | null>(null)
  let plotWidth = $state(760)
  let plotHeight = $state(250)
  let dragging = $state(false)
  let methodOpen = $state(false)

  let band = $state<"all" | "pos" | "neu" | "neg">("all")
  let query = $state("")
  let sortKey = $state<StorySortKey>("hn_timestamp")
  let pageIndex = $state(0)
  let inspectedId = $state<number | null>(null)

  const current = $derived(data.verdictScore)
  const currentAnswer = $derived(answerFor(current.finalScore))
  // Semantic tone (pos/neu/neg) driving the verdict accent, glow, and score color
  const verdictTone = $derived(current.totalAnalyzed ? verdictBandFor(current.finalScore) : null)

  // Weekly chart series (strictly recorded weekly snapshots, never mixed with current export)
  const samples = $derived(weeklyRange(data.weeklySnapshots, days, exportedAt))
  const bounds = $derived(chartBounds(samples))
  const startMs = $derived(Date.parse(samples[0]?.weekStart ?? ""))
  const endMs = $derived(Date.parse(samples.at(-1)?.weekStart ?? ""))

  const points = $derived(
    samples.map((sample) => ({
      sample,
      x: xAt(Date.parse(sample.weekStart)),
      y: yAt(sample.verdictScore),
    }))
  )

  const xLabels = $derived(monthTicks(startMs, endMs, plotWidth, days))
  const inspectedPoint = $derived(selectedWeek === null ? null : (points[selectedWeek] ?? null))

  // Sort the full eligible story set newest-first BEFORE slicing any page
  const search = $derived(query.trim().toLowerCase())
  const filteredStories = $derived.by(() => {
    const eligible = data.topArticles.filter((story) => {
      if (band !== "all" && sentimentBand(story.sentiment_score) !== band) return false
      if (!search) return true
      return `${story.hn_title} ${story.topic ?? ""} ${story.url}`.toLowerCase().includes(search)
    })
    return sortStories(eligible, sortKey)
  })

  const visibleStories = $derived(filteredStories.slice(pageIndex * PAGE_SIZE, (pageIndex + 1) * PAGE_SIZE))
  const inspectedIndex = $derived(filteredStories.findIndex((story) => story.hn_id === inspectedId))
  const inspectedStory = $derived(inspectedIndex >= 0 ? filteredStories[inspectedIndex] : null)

  $effect(() => {
    onDialogChange?.(inspectedId !== null)
  })

  function xAt(time: number): number {
    if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || endMs === startMs) {
      return plotWidth / 2
    }
    return 8 + ((plotWidth - 16) * (time - startMs)) / (endMs - startMs)
  }

  function yAt(score: number): number {
    const span = Math.max(1, bounds.top - bounds.bottom)
    return 10 + ((plotHeight - 20) * (bounds.top - score)) / span
  }

  function pickNearest(clientX: number, target: HTMLElement): void {
    if (!points.length) return
    const x = clientX - target.getBoundingClientRect().left
    const nearest = points.reduce(
      (best, point, index) => (Math.abs(point.x - x) < Math.abs((points[best]?.x ?? 0) - x) ? index : best),
      0
    )
    if (nearest !== selectedWeek) {
      selectedWeek = nearest
      cueScrub()
    }
  }

  function onPointerDown(event: PointerEvent): void {
    if (event.button !== 0 || !(event.currentTarget instanceof HTMLElement)) return
    dragging = true
    event.currentTarget.setPointerCapture(event.pointerId)
    pickNearest(event.clientX, event.currentTarget)
  }

  function onPointerMove(event: PointerEvent): void {
    if (!dragging || !(event.currentTarget instanceof HTMLElement)) return
    pickNearest(event.clientX, event.currentTarget)
  }

  function onPointerUp(event: PointerEvent): void {
    if (dragging && event.currentTarget instanceof HTMLElement) {
      dragging = false
    }
  }

  function openStory(story: InfluentialArticle): void {
    inspectedId = story.hn_id
  }

  function stepStory(offset: number): void {
    const next = filteredStories[inspectedIndex + offset]
    if (next) inspectedId = next.hn_id
  }

  function inspectWeek(target: number): void {
    const clamped = Math.min(Math.max(target, 0), points.length - 1)
    if (clamped !== selectedWeek) {
      selectedWeek = clamped
      cueScrub()
    }
  }

  function onHitKeydown(event: KeyboardEvent): void {
    const last = points.length - 1
    const current = selectedWeek ?? last
    if (event.key === "ArrowLeft" || event.key === "ArrowDown") {
      event.preventDefault()
      inspectWeek(current - 1)
    } else if (event.key === "ArrowRight" || event.key === "ArrowUp") {
      event.preventDefault()
      inspectWeek(current + 1)
    } else if (event.key === "Home") {
      event.preventDefault()
      inspectWeek(0)
    } else if (event.key === "End") {
      event.preventDefault()
      inspectWeek(last)
    }
  }
</script>

<div class="dir-phosphor ph-page">
  <div class="ph-scan" aria-hidden="true"></div>

  <header class="ph-header">
    <div class="ph-wrap ph-header-row">
      <a class="ph-brand" href="#home">
        <span class="ph-sigil" aria-hidden="true">&gt;</span>
        <strong>is-ai-good-yet</strong>
        <span class="ph-scope">// hacker news &middot; ai coding</span>
      </a>
      <div class="ph-header-right">
        <a class="ph-link" href="#details">more info</a>
        <a
          class="ph-link"
          href="#ph-method"
          onclick={() => {
            methodOpen = true
          }}>methodology</a
        >
        <PhosphorFxBar {onReplay} {replayDisabled} />
      </div>
    </div>
  </header>

  <main class="ph-wrap ph-main">
    <!-- CURRENT VERDICT (never changes when inspecting weekly history) -->
    <section
      id="home"
      tabindex="-1"
      class={`ph-hero${verdictTone ? ` ph-tone-${verdictTone}` : ""}`}
      aria-labelledby="ph-verdict-heading"
    >
      <div class="ph-hero-left">
        <p class="ph-prompt"><span class="ph-sigil" aria-hidden="true">&gt;</span> is ai &ldquo;good&rdquo; yet?</p>
        <h1 id="ph-verdict-heading" class="ph-verdict">
          {#if current.totalAnalyzed}
            {currentAnswer}.
          {:else}
            UNAVAILABLE.
          {/if}
        </h1>
      </div>

      {#if current.totalAnalyzed}
        <div class="ph-hero-right" aria-label="Current verdict score">
          <p class="ph-kicker">current verdict</p>
          <p class="ph-score">
            <strong><PhFlowNumber value={current.finalScore.toFixed(1)} /></strong><span>/100</span>
          </p>
          <p class="ph-thresholds">
            YES &ge;{YES_FLOOR} &middot; NO &lt;{NO_CEILING}{#if exportedAt} &middot; {exportedAt.slice(0, 10)}{/if}
          </p>
        </div>
      {/if}
    </section>

    <!-- DOMINANT WEEKLY HISTORY SCOPE -->
    <section id="weekly" class="ph-panel" aria-labelledby="ph-scope-heading">
      <div class="ph-panel-head">
        <div>
          <h2 id="ph-scope-heading"><span class="ph-path">/weekly</span> sentiment history</h2>
          <p class="ph-sub">
            Recorded weekly rolling snapshots &middot; inspecting a week keeps the current verdict fixed
          </p>
        </div>
        <div class="ph-ranges" role="group" aria-label="Weekly history range">
          {#each ranges as range (range.label)}
            <button
              type="button"
              class="ph-btn"
              aria-pressed={days === range.days}
              onclick={() => {
                cueToggle()
                days = range.days
                selectedWeek = null
              }}
            >
              {range.label}
            </button>
          {/each}
        </div>
      </div>

      {#if points.length}
        <figure class="ph-figure">
          <div class="ph-scope-grid">
            <div class="ph-yaxis" aria-hidden="true">
              {#each bounds.ticks as tick (tick)}
                <span style:top={`${(100 * yAt(tick)) / plotHeight}%`}>{tick}</span>
              {/each}
            </div>

            <div class="ph-screen" bind:clientWidth={plotWidth} bind:clientHeight={plotHeight}>
              <svg viewBox={`0 0 ${plotWidth} ${plotHeight}`} aria-hidden="true">
                <!-- NOT YET threshold zone (45-55) -->
                <rect
                  class="ph-band"
                  x="0"
                  y={yAt(YES_FLOOR)}
                  width={plotWidth}
                  height={Math.max(0, yAt(NO_CEILING) - yAt(YES_FLOOR))}
                />

                <!-- Horizontal ticks & thresholds -->
                {#each bounds.ticks as tick (tick)}
                  <line
                    class:ph-threshold-yes={tick === YES_FLOOR}
                    class:ph-threshold-no={tick === NO_CEILING}
                    class:ph-gridline={tick !== YES_FLOOR && tick !== NO_CEILING}
                    x1="0"
                    x2={plotWidth}
                    y1={yAt(tick)}
                    y2={yAt(tick)}
                  />
                {/each}

                <!-- Vertical month gridlines -->
                {#each xLabels as tickMs (tickMs)}
                  <line
                    class="ph-gridline"
                    x1={xAt(tickMs)}
                    x2={xAt(tickMs)}
                    y1={yAt(bounds.top)}
                    y2={yAt(bounds.bottom)}
                  />
                {/each}

                <!-- Connecting guides between adjacent recorded weeks (halo + beam core) -->
                {#each points as point, index (point.sample.week)}
                  {#if index > 0}
                    <line
                      class="ph-trace-glow"
                      x1={points[index - 1].x}
                      x2={point.x}
                      y1={points[index - 1].y}
                      y2={point.y}
                    />
                    <line
                      class="ph-trace"
                      x1={points[index - 1].x}
                      x2={point.x}
                      y1={points[index - 1].y}
                      y2={point.y}
                    />
                  {/if}
                {/each}

                <!-- Recorded weekly snapshot dots -->
                {#each points as point, index (point.sample.week)}
                  <circle
                    class:ph-dot-latest={index === points.length - 1}
                    class="ph-dot"
                    cx={point.x}
                    cy={point.y}
                    r={index === points.length - 1 ? 3.5 : plotWidth < 460 ? 1.8 : 2.3}
                  />
                {/each}

                {#if inspectedPoint}
                  <line
                    class="ph-cursor"
                    x1={inspectedPoint.x}
                    x2={inspectedPoint.x}
                    y1={yAt(bounds.top)}
                    y2={yAt(bounds.bottom)}
                  />
                  <circle class="ph-dot-active" cx={inspectedPoint.x} cy={inspectedPoint.y} r="5" />
                {/if}
              </svg>

              <div class="ph-zone-tags" aria-hidden="true">
                <span class="ph-zone-tag ph-zone-yes" style:top={`${(100 * yAt(YES_FLOOR)) / plotHeight}%`}>
                  YES &ge;{YES_FLOOR}
                </span>
                <span
                  class="ph-zone-tag ph-zone-mid"
                  style:top={`${(50 * (yAt(YES_FLOOR) + yAt(NO_CEILING))) / plotHeight}%`}
                >
                  NOT YET
                </span>
                <span class="ph-zone-tag ph-zone-no" style:top={`${(100 * yAt(NO_CEILING)) / plotHeight}%`}>
                  NO &lt;{NO_CEILING}
                </span>
              </div>

              <!-- Week inspector: pointer scrub + ARIA slider semantics on the chart itself -->
              <div
                class="ph-hit"
                role="slider"
                tabindex="0"
                aria-label="Inspect recorded week"
                aria-valuemin={0}
                aria-valuemax={Math.max(0, points.length - 1)}
                aria-valuenow={selectedWeek ?? points.length - 1}
                aria-valuetext={inspectedPoint
                  ? `Week of ${formatMediumDate(inspectedPoint.sample.weekStart)}, score ${inspectedPoint.sample.verdictScore.toFixed(1)}, ${answerFor(inspectedPoint.sample.verdictScore)}`
                  : `Latest recorded week ${formatMediumDate(points[points.length - 1].sample.weekStart)}, score ${points[points.length - 1].sample.verdictScore.toFixed(1)}`}
                onpointerdown={onPointerDown}
                onpointermove={onPointerMove}
                onpointerup={onPointerUp}
                onpointercancel={onPointerUp}
                onkeydown={onHitKeydown}
              ></div>
            </div>

            <div class="ph-xaxis" aria-hidden="true">
              {#each xLabels as tickMs (tickMs)}
                <span style:left={`${(100 * xAt(tickMs)) / plotWidth}%`}>{formatMonthLabel(tickMs)}</span>
              {/each}
            </div>
          </div>

          <figcaption class="ph-scrub-bar">
            <output class="ph-readout">
              {#if inspectedPoint}
                <span>week {inspectedPoint.sample.weekStart}</span>
                <strong class={`ph-read-${verdictBandFor(inspectedPoint.sample.verdictScore)}`}>
                  <PhFlowNumber value={inspectedPoint.sample.verdictScore.toFixed(1)} /> &middot; {answerFor(inspectedPoint.sample.verdictScore)}
                </strong>
                <button
                  type="button"
                  class="ph-clear"
                  onclick={() => {
                    cueToggle()
                    selectedWeek = null
                  }}>clear</button
                >
              {:else}
                <span>
                  {points.length} recorded weeks &middot; latest {points[points.length - 1].sample.weekStart} ({points[
                    points.length - 1
                  ].sample.verdictScore.toFixed(1)})
                </span>
              {/if}
            </output>
          </figcaption>
        </figure>
      {:else}
        <p class="ph-empty">No weekly snapshots in this range.</p>
      {/if}
    </section>

    <!-- NEWEST-FIRST HN EVIDENCE STREAM -->
    <section id="articles-table" class="ph-evidence" aria-labelledby="ph-feed-heading">
      <div class="ph-panel-head">
        <div>
          <h2 id="ph-feed-heading"><span class="ph-path">/hn/stories</span> hacker news evidence</h2>
          <p class="ph-sub">
            Sorted newest first by HN submission time &middot; {formatInt(filteredStories.length)} stories
          </p>
        </div>
      </div>

      <div class="ph-tools">
        <div class="ph-chips" role="group" aria-label="Filter stories by sentiment">
          {#each bandFilters as filter (filter.key)}
            <button
              type="button"
              class="ph-btn"
              aria-pressed={band === filter.key}
              onclick={() => {
                cueToggle()
                band = filter.key
                pageIndex = 0
              }}
            >
              {filter.label}
            </button>
          {/each}
        </div>

        <label class="ph-grep">
          <span>grep</span>
          <input
            type="search"
            bind:value={query}
            oninput={() => {
              pageIndex = 0
            }}
            placeholder="title, topic, domain"
            autocomplete="off"
          />
        </label>

        <label class="ph-sort">
          <span>order</span>
          <select
            bind:value={sortKey}
            onchange={() => {
              cueToggle()
              pageIndex = 0
            }}
          >
            {#each sortOptions as option (option.key)}
              <option value={option.key}>{option.label}</option>
            {/each}
          </select>
        </label>
      </div>

      {#if visibleStories.length}
        <div class="ph-cols" aria-hidden="true">
          <span>posted</span>
          <span>sentiment</span>
          <span>story</span>
          <span class="num">pts</span>
          <span class="num">cmt</span>
        </div>

        <ul class="ph-list">
          {#each visibleStories as story (story.hn_id)}
            {@const storyBand = sentimentBand(story.sentiment_score)}
            {@const domain = hostnameOf(story.url)}
            <li>
              <button
                type="button"
                class="ph-row"
                onclick={() => openStory(story)}
                onpointerenter={() => cueHover(story.sentiment_score * 50)}
              >
                <span class="ph-date">{formatIsoDate(story)}</span>
                <span class={`ph-sent ph-sent-${storyBand}`}>
                  {bandScore(story.sentiment_score)}
                </span>
                <span class="ph-title">
                  <strong>{story.hn_title}</strong>
                  {#if domain}<small>{domain}</small>{/if}
                </span>
                <span class="ph-num"><span class="ph-mob-k">pts </span>{formatInt(story.hn_score)}</span>
                <span class="ph-num"><span class="ph-mob-k">cmt </span>{formatInt(story.hn_comments)}</span>
              </button>
            </li>
          {/each}
        </ul>

        <nav class="ph-pager" aria-label="Story pages">
          <button
            type="button"
            class="ph-btn"
            disabled={pageIndex === 0}
            onclick={() => {
              cueToggle()
              pageIndex -= 1
            }}>prev</button
          >
          <span>
            {pageIndex * PAGE_SIZE + 1}–{pageIndex * PAGE_SIZE + visibleStories.length} of {formatInt(
              filteredStories.length
            )}
          </span>
          <button
            type="button"
            class="ph-btn"
            disabled={(pageIndex + 1) * PAGE_SIZE >= filteredStories.length}
            onclick={() => {
              cueToggle()
              pageIndex += 1
            }}>next</button
          >
        </nav>
      {:else}
        <p class="ph-empty">No stories match the current filter.</p>
      {/if}
    </section>

    <PhosphorMoreInfo quotes={data.detailQuotes} />

    <!-- METHODOLOGY (sample size, rolling window, and weighting live exclusively here) -->
    <details id="ph-method" class="ph-method" bind:open={methodOpen}>
      <summary>&gt; cat methodology.txt</summary>
      <div class="ph-method-body">
        {#if current.totalAnalyzed}
          <p>
            Current verdict sample: {formatInt(current.totalAnalyzed)} analyzed Hacker News articles in a rolling
            {current.monthsAnalyzed}-month window ({formatInt(data.permanentRecord.totalArticles)} all-time analyzed).
            {#if exportedAt} Exported {formatMediumDate(exportedAt)} (UTC).{/if}
          </p>
        {/if}
        <p>
          Verdict weighting: each article’s sentiment is weighted by influence (Hacker News points and recency). The
          0–100 score reflects the positive share of combined positive and negative contributions. YES is
          &ge;{YES_FLOOR}; NO is &lt;{NO_CEILING}; scores between {NO_CEILING} and {YES_FLOOR} are NOT YET.
        </p>
        <p>
          History and feed rules: only dots on the weekly chart are recorded snapshots; connecting segments join
          adjacent recorded weeks as visual guides, not daily readings. Hacker News stories above are ordered newest
          first by actual HN submission time (<code>hn_timestamp</code>) for reading clarity; presentation order does
          not alter verdict weighting.
        </p>
      </div>
    </details>

    <footer class="ph-footer">
      <div>
        <div>Hacker News sentiment on AI-assisted coding.</div>
        <div>Unique visitors: <strong><VisitorCounter animated={v12Effects.motionOK} /></strong></div>
      </div>
      <nav aria-label="Source links">
        <a href="https://github.com/ilyaizen/is-ai-good-yet" target="_blank" rel="noreferrer">GitHub</a>
        <a href="https://hcker.news/" target="_blank" rel="noreferrer">Hcker.news</a>
        <a href="https://news.ycombinator.com/item?id=46851589" target="_blank" rel="noreferrer">Original HN post</a>
      </nav>
    </footer>
  </main>

  <PhosphorStoryDialog
    article={inspectedStory}
    onClose={() => {
      inspectedId = null
    }}
    onStep={stepStory}
    hasPrevious={inspectedIndex > 0}
    hasNext={inspectedIndex >= 0 && inspectedIndex < filteredStories.length - 1}
  />
</div>

<style>
  .ph-page {
    position: relative;
    min-height: 100vh;
    background: var(--td-ground);
    color: var(--td-ink);
    font-family: var(--font-mono);
    font-size: 0.875rem;
    line-height: 1.5;
    font-variant-numeric: tabular-nums;
  }

  .ph-scan {
    position: fixed;
    inset: 0;
    z-index: 30;
    pointer-events: none;
    background: repeating-linear-gradient(
      to bottom,
      transparent 0 2px,
      var(--td-scanline) 2px 3px
    );
    opacity: 0.28;
  }

  .ph-wrap {
    width: min(100%, 72rem);
    margin-inline: auto;
    padding-inline: clamp(0.85rem, 3vw, 2rem);
  }

  .ph-header {
    position: sticky;
    top: 0;
    z-index: 20;
    background: var(--td-ground);
    border-bottom: 1px solid var(--td-rule);
  }

  .ph-header-row {
    min-height: 3.1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.5rem 1rem;
    padding-block: 0.4rem;
    font-size: 0.78rem;
  }

  .ph-brand {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    color: inherit;
    text-decoration: none;
  }

  .ph-sigil,
  .ph-path {
    color: var(--td-accent);
  }

  .ph-scope {
    color: var(--td-faint);
  }

  .ph-header-right {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.55rem 0.9rem;
  }

  .ph-link {
    color: var(--td-muted);
    text-decoration: underline;
    text-underline-offset: 0.22em;
    transition: color 140ms var(--ease-swift);
  }

  .ph-link:hover,
  .ph-link:focus-visible {
    color: var(--td-accent);
  }

  .ph-main {
    padding-block: clamp(1.25rem, 3vw, 2rem) 3.5rem;
    display: grid;
    gap: clamp(1.4rem, 3vw, 2.25rem);
  }

  /* Hero */
  .ph-hero {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 1rem 2rem;
    padding-bottom: 1.25rem;
    border-bottom: 1px solid var(--td-rule);
  }

  .ph-hero:focus {
    outline: none;
  }

  .ph-prompt {
    margin: 0 0 0.3rem;
    color: var(--td-muted);
    font-size: 0.92rem;
  }

  /* Verdict tone: semantic sentiment color drives the hero accent via scoped vars */
  .ph-tone-yes {
    --td-verdict: var(--td-pos);
    --td-verdict-glow: var(--td-pos-soft);
  }

  .ph-tone-mid {
    --td-verdict: var(--td-neu);
    --td-verdict-glow: var(--td-neu-soft);
  }

  .ph-tone-no {
    --td-verdict: var(--td-neg);
    --td-verdict-glow: var(--td-neg-soft);
  }

  .ph-verdict {
    margin: 0;
    font-size: clamp(2.8rem, 8.5vw, 5.4rem);
    line-height: 0.94;
    font-weight: 700;
    letter-spacing: -0.04em;
    color: var(--td-verdict, var(--td-ink-bright));
    text-shadow: 0 0 0.35em var(--td-verdict-glow, var(--td-glow));
  }

  .ph-hero-right {
    text-align: right;
  }

  .ph-kicker {
    margin: 0;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--td-faint);
  }

  .ph-score {
    margin: 0.15rem 0 0.25rem;
    line-height: 1;
    white-space: nowrap;
  }

  .ph-score strong {
    font-size: clamp(1.9rem, 4.4vw, 2.9rem);
    font-weight: 700;
    letter-spacing: -0.05em;
    color: var(--td-verdict, var(--td-ink-bright));
  }

  .ph-score span {
    margin-left: 0.2rem;
    color: var(--td-muted);
    font-size: 0.85rem;
  }

  .ph-thresholds {
    margin: 0;
    font-size: 0.75rem;
    color: var(--td-faint);
  }

  /* Scope panel */
  .ph-panel {
    border: 1px solid var(--td-rule);
    background: var(--td-surface);
    padding: clamp(0.85rem, 2.2vw, 1.35rem);
  }

  .ph-panel-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.75rem 1rem;
    margin-bottom: 1rem;
  }

  h2 {
    margin: 0;
    font-size: 1rem;
    font-weight: 700;
    color: var(--td-ink);
  }

  .ph-sub {
    margin: 0.25rem 0 0;
    font-size: 0.76rem;
    color: var(--td-faint);
  }

  .ph-ranges {
    display: flex;
    gap: 0.3rem;
  }

  .ph-btn {
    min-height: 2rem;
    padding: 0 0.65rem;
    border: 1px solid var(--td-rule);
    background: var(--td-ground);
    color: var(--td-muted);
    font: inherit;
    font-size: 0.75rem;
    cursor: pointer;
    white-space: nowrap;
    transition:
      background-color 140ms var(--ease-swift),
      border-color 140ms var(--ease-swift),
      color 140ms var(--ease-swift);
  }

  .ph-btn:hover:not(:disabled),
  .ph-btn:focus-visible {
    border-color: var(--td-accent);
    color: var(--td-ink-bright);
  }

  .ph-btn[aria-pressed="true"] {
    background: var(--td-accent);
    border-color: var(--td-accent);
    color: var(--td-ground);
    font-weight: 700;
  }

  .ph-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .ph-figure {
    margin: 0;
  }

  .ph-scope-grid {
    display: grid;
    grid-template-columns: 2.1rem minmax(0, 1fr);
    row-gap: 0.35rem;
  }

  .ph-yaxis,
  .ph-screen,
  .ph-xaxis {
    position: relative;
  }

  .ph-yaxis span {
    position: absolute;
    right: 0.45rem;
    transform: translateY(-50%);
    font-size: 0.7rem;
    color: var(--td-faint);
  }

  .ph-screen {
    height: clamp(12rem, 29vw, 17.5rem);
    border: 1px solid var(--td-rule-soft);
    background: var(--td-ground);
    overflow: hidden;
  }

  .ph-screen svg {
    display: block;
    width: 100%;
    height: 100%;
  }

  .ph-band {
    fill: var(--td-neu-wash);
  }

  .ph-gridline {
    stroke: var(--td-rule-soft);
    stroke-width: 1;
  }

  .ph-threshold-yes {
    stroke: var(--td-pos-soft);
    stroke-width: 1;
    stroke-dasharray: 4 4;
  }

  .ph-threshold-no {
    stroke: var(--td-neg-soft);
    stroke-width: 1;
    stroke-dasharray: 4 4;
  }

  .ph-trace-glow {
    stroke: var(--td-glow);
    stroke-width: 5.5;
    stroke-linecap: round;
  }

  .ph-trace {
    stroke: var(--td-accent);
    stroke-width: 1.75;
    stroke-linecap: round;
  }

  .ph-dot {
    fill: var(--td-accent);
  }

  .ph-dot-latest {
    fill: var(--td-ink-bright);
  }

  .ph-cursor {
    stroke: var(--td-ink);
    stroke-width: 1;
    stroke-dasharray: 3 3;
  }

  .ph-dot-active {
    fill: var(--td-ground);
    stroke: var(--td-ink-bright);
    stroke-width: 2;
  }

  .ph-zone-tags {
    position: absolute;
    inset: 0 0.55rem 0 auto;
    pointer-events: none;
    font-size: 0.66rem;
    letter-spacing: 0.06em;
  }

  .ph-zone-tag {
    position: absolute;
    right: 0;
    white-space: nowrap;
    padding-inline: 0.25rem;
    background: var(--td-ground);
  }

  .ph-zone-yes {
    color: var(--td-pos);
    transform: translateY(-120%);
  }

  .ph-zone-mid {
    color: var(--td-neu);
    transform: translateY(-50%);
  }

  .ph-zone-no {
    color: var(--td-neg);
    transform: translateY(25%);
  }

  .ph-hit {
    position: absolute;
    inset: 0;
    cursor: ew-resize;
    touch-action: pan-y;
  }

  .ph-hit:focus-visible {
    outline: 2px solid var(--td-accent);
    outline-offset: -3px;
  }

  .ph-xaxis {
    grid-column: 2;
    height: 1.35rem;
  }

  .ph-xaxis span {
    position: absolute;
    transform: translateX(-50%);
    font-size: 0.7rem;
    color: var(--td-faint);
    white-space: nowrap;
  }

  .ph-scrub-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.6rem 1.25rem;
    margin-top: 0.85rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--td-rule-soft);
    font-size: 0.78rem;
  }

  .ph-readout {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.45rem 0.75rem;
    color: var(--td-muted);
  }

  .ph-readout strong {
    color: var(--td-ink-bright);
  }

  .ph-readout .ph-read-yes {
    color: var(--td-pos);
  }

  .ph-readout .ph-read-mid {
    color: var(--td-neu);
  }

  .ph-readout .ph-read-no {
    color: var(--td-neg);
  }

  .ph-clear {
    border: 1px solid var(--td-rule);
    background: var(--td-ground);
    color: var(--td-muted);
    padding: 0.15rem 0.5rem;
    font: inherit;
    font-size: 0.72rem;
    cursor: pointer;
    transition:
      border-color 140ms var(--ease-swift),
      color 140ms var(--ease-swift);
  }

  .ph-clear:hover,
  .ph-clear:focus-visible {
    border-color: var(--td-accent);
    color: var(--td-accent);
  }

  /* Evidence log */
  .ph-tools {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: 0.85rem;
    font-size: 0.76rem;
  }

  .ph-chips {
    display: flex;
    gap: 0.3rem;
    flex-wrap: wrap;
  }

  .ph-grep,
  .ph-sort {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    min-height: 2rem;
    padding: 0 0.55rem;
    border: 1px solid var(--td-rule);
    background: var(--td-surface);
    color: var(--td-faint);
    transition: border-color 140ms var(--ease-swift);
  }

  .ph-grep:focus-within,
  .ph-sort:focus-within {
    border-color: var(--td-accent);
  }

  .ph-grep {
    margin-left: auto;
  }

  .ph-grep input,
  .ph-sort select {
    background: transparent;
    border: 0;
    color: var(--td-ink);
    font: inherit;
    outline: none;
  }

  .ph-sort select option {
    background: var(--td-ground);
    color: var(--td-ink);
  }

  .ph-grep input {
    width: 11.5rem;
  }

  .ph-grep input::placeholder {
    color: var(--td-faint);
  }

  .ph-cols,
  .ph-row {
    display: grid;
    grid-template-columns: 6.4rem 4.8rem minmax(0, 1fr) 4.2rem 4.2rem;
    align-items: baseline;
    gap: 0.75rem;
  }

  .ph-cols {
    padding: 0.45rem 0.6rem;
    border-top: 1px solid var(--td-rule);
    border-bottom: 1px solid var(--td-rule);
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--td-faint);
  }

  .ph-cols .num,
  .ph-num {
    text-align: right;
    white-space: nowrap;
  }

  .ph-list {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .ph-row {
    width: 100%;
    padding: 0.62rem 0.6rem;
    border: 0;
    border-bottom: 1px solid var(--td-rule-soft);
    background: transparent;
    color: inherit;
    font: inherit;
    text-align: left;
    cursor: pointer;
    transition: background-color 110ms var(--ease-swift);
  }

  .ph-row:hover,
  .ph-row:focus-visible {
    background: var(--td-hover);
  }

  .ph-date {
    color: var(--td-muted);
    font-size: 0.78rem;
    white-space: nowrap;
  }

  .ph-sent {
    display: inline-block;
    width: fit-content;
    padding: 0 0.35rem;
    font-size: 0.76rem;
    white-space: nowrap;
    border: 1px solid transparent;
  }

  .ph-sent-pos {
    color: var(--td-pos);
  }

  .ph-sent-neu {
    color: var(--td-neu);
  }

  .ph-sent-neg {
    color: var(--td-neg);
    border-color: var(--td-neg-soft);
  }

  .ph-title {
    min-width: 0;
    overflow-wrap: anywhere;
  }

  .ph-title strong {
    font-weight: 500;
    color: var(--td-ink);
  }

  .ph-title small {
    margin-left: 0.55rem;
    color: var(--td-faint);
    font-size: 0.75rem;
  }

  .ph-num {
    color: var(--td-muted);
    font-size: 0.8rem;
  }

  .ph-mob-k {
    display: none;
  }

  .ph-pager {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    padding-top: 0.8rem;
    font-size: 0.76rem;
    color: var(--td-faint);
  }

  .ph-empty {
    margin: 0;
    padding: 1.5rem 0;
    color: var(--td-muted);
  }

  /* Methodology */
  .ph-method {
    border-top: 1px solid var(--td-rule);
    padding-top: 0.85rem;
  }

  .ph-method summary {
    cursor: pointer;
    color: var(--td-accent);
    font-size: 0.84rem;
    width: fit-content;
  }

  .ph-method-body {
    margin-top: 0.75rem;
    display: grid;
    gap: 0.55rem;
    max-width: 74ch;
    color: var(--td-muted);
    font-size: 0.8rem;
  }

  .ph-method-body p {
    margin: 0;
  }

  .ph-method-body code {
    color: var(--td-ink);
  }

  /* Footer */
  .ph-footer {
    border-top: 1px solid var(--td-rule-soft);
    padding-top: 0.9rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.5rem 1.25rem;
    font-size: 0.76rem;
    color: var(--td-faint);
  }

  .ph-footer strong {
    color: var(--td-accent);
  }

  .ph-footer nav {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem 1rem;
  }

  .ph-footer a {
    color: var(--td-muted);
    text-decoration: underline;
    text-underline-offset: 0.2em;
    transition: color 140ms var(--ease-swift);
  }

  .ph-footer a:hover,
  .ph-footer a:focus-visible {
    color: var(--td-accent);
  }

  :is(a, button, input, select, summary):focus-visible {
    outline: 2px solid var(--td-accent);
    outline-offset: 2px;
  }

  :global(html.fx-off) .ph-scan,
  :global(html.fx-off) .ph-trace-glow {
    display: none;
  }

  :global(html.fx-off) .ph-verdict {
    text-shadow: none;
  }

  :global(html.fx-off) .ph-btn,
  :global(html.fx-off) .ph-row,
  :global(html.fx-off) .ph-link,
  :global(html.fx-off) .ph-clear,
  :global(html.fx-off) .ph-grep,
  :global(html.fx-off) .ph-sort,
  :global(html.fx-off) .ph-footer a {
    transition: none;
  }

  @media (prefers-reduced-motion: reduce) {
    .ph-scan,
    .ph-trace-glow {
      display: none;
    }

    .ph-verdict {
      text-shadow: none;
    }

    .ph-btn,
    .ph-row,
    .ph-link,
    .ph-clear,
    .ph-grep,
    .ph-sort,
    .ph-footer a {
      transition: none;
    }
  }

  @media (max-width: 680px) {
    .ph-scope {
      display: none;
    }

    .ph-hero {
      align-items: flex-start;
    }

    .ph-hero-right {
      text-align: left;
    }

    .ph-grep {
      margin-left: 0;
      width: 100%;
    }

    .ph-grep input {
      width: 100%;
    }

    .ph-sort {
      width: 100%;
      justify-content: space-between;
    }

    .ph-cols {
      display: none;
    }

    .ph-row {
      grid-template-columns: auto auto auto 1fr;
      gap: 0.35rem 0.65rem;
      padding-inline: 0.25rem;
    }

    .ph-title {
      grid-column: 1 / -1;
      order: -1;
    }

    .ph-title small {
      display: block;
      margin-left: 0;
      margin-top: 0.15rem;
    }

    .ph-num {
      text-align: left;
      font-size: 0.74rem;
    }

    .ph-mob-k {
      display: inline;
      color: var(--td-faint);
    }
  }
</style>
