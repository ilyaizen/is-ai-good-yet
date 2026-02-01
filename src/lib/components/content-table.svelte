<script lang="ts">
  import type { UrlEntry } from "$lib/server/db"
  import {
    Search,
    ChevronDown,
    ChevronUp,
    ExternalLink,
    Filter,
    LayoutList,
    SlidersHorizontal,
    ChevronRight,
  } from "lucide-svelte"
  import * as Select from "$lib/components/ui/select"
  import * as InputGroup from "$lib/components/ui/input-group"
  import { page } from "$app/stores"
  import { goto } from "$app/navigation"
  import { browser } from "$app/environment"
  import ArticleDetailsSheet from "$lib/components/landing/article-details-sheet.svelte"

  let {
    data = [],
    enableDetailLinks = false,
    title = "Analyzed Content",
    syncWithUrl = false,
  }: {
    data: UrlEntry[]
    enableDetailLinks?: boolean
    title?: string
    syncWithUrl?: boolean
  } = $props()

  // Sheet state for article details
  let sheetOpen = $state(false)
  let selectedArticleId = $state<number | null>(null)

  function openArticleSheet(hnId: number) {
    selectedArticleId = hnId
    sheetOpen = true
  }

  // Time decay colors (from recent-articles-table)
  const TIME_DECAY_MONTHS = 6
  const TIME_WINDOW_YEARS = 3
  const TIME_DECAY_MS = TIME_DECAY_MONTHS * 30 * 24 * 60 * 60 * 1000
  const TIME_WINDOW_MS = TIME_WINDOW_YEARS * 365 * 24 * 60 * 60 * 1000

  const COLOR_GREEN = "var(--color-primary)"
  const COLOR_YELLOW = "var(--color-warning)"
  const COLOR_RED = "var(--color-destructive)"

  function hexToRgb(hex: string): [number, number, number] {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
    return result ? [parseInt(result[1], 16), parseInt(result[2], 16), parseInt(result[3], 16)] : [0, 0, 0]
  }

  function interpolateColor(color1: string, color2: string, factor: number): string {
    const rgb1 = hexToRgb(color1)
    const rgb2 = hexToRgb(color2)
    const result = rgb1.map((c, i) => Math.round(c + factor * (rgb2[i] - c)))
    return `rgb(${result[0]}, ${result[1]}, ${result[2]})`
  }

  function getTimeColor(timestamp: number | null): string {
    if (!timestamp) return COLOR_RED
    const now = new Date().getTime()
    const articleTime = timestamp * 1000
    const age = now - articleTime

    if (age < 0) return COLOR_GREEN
    if (age <= TIME_DECAY_MS) {
      return interpolateColor(COLOR_GREEN, COLOR_YELLOW, age / TIME_DECAY_MS)
    }
    if (age <= TIME_WINDOW_MS) {
      const remainingRatio = (age - TIME_DECAY_MS) / (TIME_WINDOW_MS - TIME_DECAY_MS)
      return interpolateColor(COLOR_YELLOW, COLOR_RED, remainingRatio)
    }
    return COLOR_RED
  }

  function formatTimeAgo(timestamp: number | null): string {
    if (!timestamp) return "-"
    const now = new Date()
    const date = new Date(timestamp * 1000)
    const diffMs = now.getTime() - date.getTime()
    const diffSecs = Math.floor(diffMs / 1000)
    const diffMins = Math.floor(diffSecs / 60)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)
    const diffWeeks = Math.floor(diffDays / 7)
    const diffYears = Math.floor(diffWeeks / 52)

    if (diffSecs < 60) return "just now"
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    if (diffWeeks < 52) return `${diffWeeks}w ago`
    return `${diffYears}y ago`
  }

  function formatDate(timestamp: number | null): string {
    if (!timestamp) return "-"
    return new Date(timestamp * 1000).toISOString().split("T")[0]
  }

  function getDomain(url: string): string {
    try {
      const urlObj = new URL(url)
      return urlObj.hostname.replace(/^www\./, "")
    } catch {
      return url.replace(/^www\./, "")
    }
  }

  function getSentimentColor(score: number | null): string {
    if (score === null) return "var(--color-muted-foreground)"
    if (score > 0.2) return "var(--color-primary)"
    if (score < -0.2) return "var(--color-destructive)"
    return "var(--color-warning)"
  }

  function formatSentimentScore(score: number | null): string {
    if (score === null) return "-"
    const prefix = score >= 0 ? "+" : ""
    return `${prefix}${score.toFixed(2)}`
  }

  // Extract summary from classification_json
  function getSummary(item: UrlEntry): string | null {
    if (item.classification_json) {
      try {
        const analysis = JSON.parse(item.classification_json)
        if (analysis.summary) return analysis.summary
      } catch {}
    }
    return null
  }

  // Extract rejection/reasoning from content_filter_json (prefilter stage)
  function getRejectionReason(item: UrlEntry): string | null {
    if (item.content_filter_json) {
      try {
        const filter = JSON.parse(item.content_filter_json)
        if (filter.reasoning) return filter.reasoning
      } catch {}
    }
    return null
  }

  // Get the secondary text line (summary or rejection reason)
  function getSecondaryText(item: UrlEntry): string | null {
    const summary = getSummary(item)
    if (summary) return summary
    const rejection = getRejectionReason(item)
    if (rejection) return rejection
    return null
  }

  function getParam<T>(key: string, defaultVal: T, parser?: (v: string) => T): T {
    if (!syncWithUrl) return defaultVal
    const val = $page.url.searchParams.get(key)
    if (val === null) return defaultVal
    if (parser) return parser(val)
    if (typeof defaultVal === "number") return parseInt(val) as T
    if (typeof defaultVal === "boolean") return (val === "true") as T
    return val as T
  }

  let searchQuery = $state(getParam("q", ""))
  let sortField = $state<keyof UrlEntry>(getParam<keyof UrlEntry>("sort", "hn_timestamp", (v) => v as keyof UrlEntry))
  let sortDirection = $state<"asc" | "desc">(getParam<"asc" | "desc">("dir", "desc", (v) => v as "asc" | "desc"))
  let statusFilter = $state(getParam("status", "scraped"))
  let hideMissingMetadata = $state(getParam("hide_missing", true))
  let showOnlyOpinionLinks = $state(getParam("opinions", false))
  let contentCategoryFilter = $state(getParam("category", "all"))
  let minScore = $state(getParam("min_score", 20))
  let minComments = $state(getParam("min_comments", 5))
  const initialPage = getParam("page", 1)
  let currentPage = $state(initialPage)
  let pageInput = $state(initialPage.toString())
  let itemsPerPage = $state(getParam("per_page", 20))

  // Controls drawer visibility - closed by default to save space
  let controlsOpen = $state(false)

  const scoreOptions = Array.from({ length: 26 }, (_, i) => i * 20)
  const commentOptions = Array.from({ length: 41 }, (_, i) => i * 5)

  const IRRELEVANT_DOMAINS = [
    "github.com",
    "arxiv.org",
    "twitter.com",
    "x.com",
    "reddit.com",
    "youtube.com",
    "docs.google.com",
    "drive.google.com",
    "gist.github.com",
    "gitlab.com",
    "bitbucket.org",
    "stackoverflow.com",
    "stackexchange.com",
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "discord.com",
    "slack.com",
    "notion.so",
    "figma.com",
    "miro.com",
    "trello.com",
    "jira.atlassian.com",
    "huggingface.co",
    "kaggle.com",
    "colab.research.google.com",
    "pypi.org",
    "npmjs.com",
    "crates.io",
  ]

  let showOnlyRelevant = $state(getParam("relevant", true))

  function isRelevantUrl(url: string): boolean {
    try {
      const hostname = new URL(url).hostname.replace(/^www\./, "")
      return !IRRELEVANT_DOMAINS.some((domain) => hostname === domain || hostname.endsWith("." + domain))
    } catch {
      return true
    }
  }

  $effect(() => {
    if (!syncWithUrl || !browser) return

    const url = new URL($page.url)
    const updateParam = (key: string, val: any, def: any) => {
      if (val !== def) url.searchParams.set(key, String(val))
      else url.searchParams.delete(key)
    }

    updateParam("q", searchQuery, "")
    updateParam("sort", sortField, "hn_timestamp")
    updateParam("dir", sortDirection, "desc")
    updateParam("status", statusFilter, "all")
    updateParam("category", contentCategoryFilter, "all")
    updateParam("relevant", showOnlyRelevant, true)
    updateParam("hide_missing", hideMissingMetadata, true)
    updateParam("opinions", showOnlyOpinionLinks, false)
    updateParam("min_score", minScore, -1)
    updateParam("min_comments", minComments, -1)
    updateParam("per_page", itemsPerPage, 20)
    updateParam("page", currentPage, 1)

    if (url.toString() !== $page.url.toString()) {
      goto(url, { replaceState: true, keepFocus: true, noScroll: true })
    }
  })

  $effect(() => {
    pageInput = currentPage.toString()
  })

  $effect(() => {
    if (currentPage > totalPages) {
      currentPage = Math.max(1, totalPages)
    }
  })

  function commitPageChange() {
    const p = parseInt(pageInput)
    if (!isNaN(p) && p >= 1 && p <= totalPages) {
      currentPage = p
    } else {
      pageInput = currentPage.toString()
    }
  }

  function getDisplayStatus(item: UrlEntry) {
    if (item.scraped_status === "failed") return "failed"
    if (item.filter_score === -1) return "skipped"
    if (item.status === "analyzed") return "analyzed"
    if (item.scraped_status === "success") return "scraped"
    if (item.status === "resolved" && (!item.hn_title || !item.hn_timestamp)) {
      return "missing-metadata"
    }
    if (item.status === "resolved") return "resolved"
    return "pending"
  }

  let filteredItems = $derived(
    data
      .filter((item) => {
        const matchesSearch = item.url.toLowerCase().includes(searchQuery.toLowerCase())
        let displayStatus = getDisplayStatus(item)
        const matchesStatus = statusFilter === "all" || displayStatus === statusFilter
        const matchesRelevant = !showOnlyRelevant || isRelevantUrl(item.url)
        const matchesMetadata = !hideMissingMetadata || (!!item.hn_id && !!item.hn_title)
        const matchesOpinionFilter = !showOnlyOpinionLinks || item.is_opinion === true
        const matchesCategory = contentCategoryFilter === "all" || item.content_category === contentCategoryFilter
        const matchesMinScore = minScore === 0 || (item.hn_score !== null && item.hn_score >= minScore)
        const matchesMinComments = minComments === 0 || (item.hn_comments !== null && item.hn_comments >= minComments)

        return (
          matchesSearch &&
          matchesStatus &&
          matchesRelevant &&
          matchesMetadata &&
          matchesOpinionFilter &&
          matchesCategory &&
          matchesMinScore &&
          matchesMinComments
        )
      })
      .sort((a, b) => {
        const valA = a[sortField]
        const valB = b[sortField]

        if (valA === valB) return 0
        if (valA === null || valA === undefined) return 1
        if (valB === null || valB === undefined) return -1

        let comparison = 0
        if (typeof valA === "string" && typeof valB === "string") {
          comparison = valA.localeCompare(valB)
        } else if (typeof valA === "boolean" && typeof valB === "boolean") {
          comparison = valA === valB ? 0 : valA ? -1 : 1
        } else if (typeof valA === "number" && typeof valB === "number") {
          comparison = valA < valB ? -1 : 1
        } else {
          comparison = String(valA).localeCompare(String(valB))
        }

        return sortDirection === "asc" ? comparison : -comparison
      })
  )

  let totalPages = $derived(Math.ceil(filteredItems.length / itemsPerPage))
  let paginatedItems = $derived(filteredItems.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage))

  function handleSort(field: keyof UrlEntry) {
    if (sortField === field) {
      sortDirection = sortDirection === "asc" ? "desc" : "asc"
    } else {
      sortField = field
      sortDirection = "desc"
      if (field === "url" || field === "status") {
        sortDirection = "asc"
      }
    }
  }
</script>

{#snippet tableControls()}
  <div class="controls-section">
    <button onclick={() => (controlsOpen = !controlsOpen)} class="filter-toggle-btn">
      <SlidersHorizontal class="h-4 w-4" />
      <span>Filters</span>
      <ChevronDown class="h-4 w-4 transition-transform duration-200 {controlsOpen ? 'rotate-180' : ''}" />
    </button>

    <div class="controls-drawer {controlsOpen ? 'open' : ''}">
      <div class="controls-content">
        <div class="controls-row">
          <button
            onclick={() => (showOnlyRelevant = !showOnlyRelevant)}
            class="relevant-toggle {showOnlyRelevant ? 'active' : ''}"
          >
            <span class="toggle-dot {showOnlyRelevant ? 'active' : ''}"></span>
            Relevant Only
          </button>

          <InputGroup.Root class="w-auto gap-2 text-sm">
            <InputGroup.Addon>
              <Filter class="h-4 w-4" />
            </InputGroup.Addon>
            <Select.Root type="single" bind:value={statusFilter}>
              <Select.Trigger class="w-40 border-none! shadow-none! bg-transparent! text-muted-foreground">
                {statusFilter === "all" ? "All Statuses" : statusFilter.charAt(0).toUpperCase() + statusFilter.slice(1)}
              </Select.Trigger>
              <Select.Content>
                <Select.Item value="all" label="All Statuses" />
                <Select.Item value="pending" label="Pending" />
                <Select.Item value="resolved" label="Resolved" />
                <Select.Item value="scraped" label="Scraped" />
                <Select.Item value="analyzed" label="Analyzed" />
                <Select.Item value="failed" label="Failed" />
                <Select.Item value="skipped" label="Skipped" />
                <Select.Item value="missing-metadata" label="Missing Metadata" />
              </Select.Content>
            </Select.Root>
          </InputGroup.Root>

          <Select.Root type="single" bind:value={contentCategoryFilter}>
            <Select.Trigger class="w-40 text-sm border-border">
              {contentCategoryFilter === "all"
                ? "All Categories"
                : contentCategoryFilter === "AI_DISCOURSE"
                  ? "Discourse"
                  : contentCategoryFilter === "AI_NEWS"
                    ? "News"
                    : contentCategoryFilter === "NOISE"
                      ? "Noise"
                      : "Skipped"}
            </Select.Trigger>
            <Select.Content>
              <Select.Item value="all" label="All Categories" />
              <Select.Item value="AI_DISCOURSE" label="Discourse (Opinion/Analysis)" />
              <Select.Item value="AI_NEWS" label="News (Facts/Releases)" />
              <Select.Item value="NOISE" label="Noise (Irrelevant)" />
              <Select.Item value="SKIPPED" label="Skipped (Domain filter)" />
            </Select.Content>
          </Select.Root>

          <div class="search-wrapper">
            <InputGroup.Root class="w-full max-w-64 sm:max-w-56 text-sm">
              <InputGroup.Addon>
                <Search class="h-4 w-4" />
              </InputGroup.Addon>
              <InputGroup.Input type="text" bind:value={searchQuery} placeholder="Search URLs..." />
            </InputGroup.Root>
          </div>
        </div>

        <div class="controls-row">
          <InputGroup.Root class="w-auto text-sm">
            <InputGroup.Addon class="text-xs text-muted-foreground">Score ≥</InputGroup.Addon>
            <Select.Root type="single" value={minScore.toString()} onValueChange={(v) => (minScore = parseInt(v))}>
              <Select.Trigger
                class="w-20 border-none! shadow-none! bg-transparent! text-muted-foreground text-center justify-center"
              >
                {minScore}
              </Select.Trigger>
              <Select.Content class="max-h-60">
                {#each scoreOptions as opt}
                  <Select.Item value={opt.toString()} label={opt.toString()} />
                {/each}
              </Select.Content>
            </Select.Root>
          </InputGroup.Root>

          <InputGroup.Root class="w-auto text-sm">
            <InputGroup.Addon class="text-xs text-muted-foreground">Comments ≥</InputGroup.Addon>
            <Select.Root
              type="single"
              value={minComments.toString()}
              onValueChange={(v) => (minComments = parseInt(v))}
            >
              <Select.Trigger
                class="w-20 border-none! shadow-none! bg-transparent! text-muted-foreground text-center justify-center"
              >
                {minComments}
              </Select.Trigger>
              <Select.Content class="max-h-60">
                {#each commentOptions as opt}
                  <Select.Item value={opt.toString()} label={opt.toString()} />
                {/each}
              </Select.Content>
            </Select.Root>
          </InputGroup.Root>

          <InputGroup.Root class="w-auto gap-2 text-sm">
            <InputGroup.Addon>
              <LayoutList class="h-4 w-4" />
            </InputGroup.Addon>
            <Select.Root
              type="single"
              value={itemsPerPage.toString()}
              onValueChange={(v) => (itemsPerPage = parseInt(v))}
            >
              <Select.Trigger class="w-40 border-none! shadow-none! bg-transparent! text-muted-foreground">
                Show {itemsPerPage} results
              </Select.Trigger>
              <Select.Content>
                <Select.Item value="20" label="Show 20 results" />
                <Select.Item value="40" label="Show 40 results" />
                <Select.Item value="60" label="Show 60 results" />
                <Select.Item value="80" label="Show 80 results" />
                <Select.Item value="100" label="Show 100 results" />
              </Select.Content>
            </Select.Root>
          </InputGroup.Root>
        </div>
      </div>
    </div>
  </div>
{/snippet}

{#snippet paginationControls()}
  <div class="pagination-controls">
    <div class="pagination-info">
      <span class="text-muted">
        Showing <span class="text-bold">{(currentPage - 1) * itemsPerPage + 1}</span>
        to <span class="text-bold">{Math.min(currentPage * itemsPerPage, filteredItems.length)}</span>
        of <span class="text-bold">{filteredItems.length}</span>
      </span>
    </div>

    <nav class="pagination-nav" aria-label="Pagination">
      <button
        onclick={() => (currentPage = Math.max(1, currentPage - 1))}
        disabled={currentPage === 1}
        class="pagination-btn"
        aria-label="Previous page"
      >
        <ChevronDown class="h-4 w-4 rotate-90" />
      </button>
      <div class="pagination-page-display">
        <input
          type="text"
          class="pagination-page-input"
          bind:value={pageInput}
          onblur={commitPageChange}
          onkeydown={(e) => e.key === "Enter" && commitPageChange()}
          aria-label="Current page"
        />
        <span class="pagination-separator">/</span>
        <span class="pagination-total">{Math.max(1, totalPages)}</span>
      </div>
      <button
        onclick={() => (currentPage = Math.min(totalPages, currentPage + 1))}
        disabled={currentPage === totalPages || totalPages === 0}
        class="pagination-btn"
        aria-label="Next page"
      >
        <ChevronDown class="h-4 w-4 -rotate-90" />
      </button>
    </nav>
  </div>
{/snippet}

<div class="content-table-section">
  <h3 class="section-title">{title}</h3>
  <p class="section-subtitle">Displaying {filteredItems.length} articles</p>

  {@render tableControls()}
  {@render paginationControls()}

  <div class="table-wrapper">
    <table class="articles-table">
      <thead>
        <tr>
          <th class="col-time">
            <button class="sort-btn" onclick={() => handleSort("hn_timestamp")} title="Sort by time">
              Time
              {#if sortField === "hn_timestamp"}
                {#if sortDirection === "asc"}
                  <ChevronUp class="sort-icon" />
                {:else}
                  <ChevronDown class="sort-icon" />
                {/if}
              {/if}
            </button>
          </th>
          <th class="col-title">Title</th>
          <th class="col-sentiment text-center">
            <button class="sort-btn" onclick={() => handleSort("sentiment_score")} title="Sort by sentiment">
              Sentiment
              {#if sortField === "sentiment_score"}
                {#if sortDirection === "asc"}
                  <ChevronUp class="sort-icon" />
                {:else}
                  <ChevronDown class="sort-icon" />
                {/if}
              {/if}
            </button>
          </th>
        </tr>
      </thead>
      <tbody>
        {#each paginatedItems as item (item.id)}
          {@const displayStatus = getDisplayStatus(item)}
          {@const secondaryText = getSecondaryText(item)}
          {@const canNavigate = enableDetailLinks && item.scraped_status === "success" && item.hn_id}
          <tr
            class="article-row"
            class:clickable={canNavigate}
            onclick={() => canNavigate && openArticleSheet(item.hn_id!)}
          >
            <td class="col-time">
              <span
                class="time-ago"
                style="color: {getTimeColor(item.hn_timestamp)}"
                title={formatDate(item.hn_timestamp)}
              >
                {formatTimeAgo(item.hn_timestamp)}
              </span>
            </td>
            <td class="col-title">
              <div class="title-cell">
                <div class="title-row">
                  {#if canNavigate}
                    <button
                      type="button"
                      class="title-link"
                      title={item.hn_title || item.url}
                      onclick={(e: MouseEvent) => {
                        e.stopPropagation()
                        openArticleSheet(item.hn_id!)
                      }}
                    >
                      <span class="title-text-content">{item.hn_title || item.url}</span>
                      <ChevronRight class="size-4 title-chevron" />
                    </button>
                  {:else}
                    <span class="title-text" title={item.hn_title || item.url}>
                      {item.hn_title || item.url}
                    </span>
                  {/if}
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="domain-anchor"
                    title="Open original article"
                    onclick={(e) => e.stopPropagation()}
                  >
                    {getDomain(item.url)}
                    <ExternalLink class="size-3 domain-external-icon" />
                  </a>
                  {#if item.hn_id}
                    <span class="title-meta">
                      <a
                        href={`https://news.ycombinator.com/item?id=${item.hn_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        class="hn-link"
                        onclick={(e) => e.stopPropagation()}
                      >
                        {item.hn_score || 0}v/{item.hn_comments || 0}c
                      </a>
                    </span>
                  {/if}
                </div>
                <div class="summary-row">
                  {#if secondaryText}
                    <div class="summary-cell" title={secondaryText}>
                      <div class="summary-track">
                        <span class="summary-text">{secondaryText}</span>
                      </div>
                    </div>
                  {/if}
                  <div class="summary-badges">
                    <span class="badge badge-status badge-status-{displayStatus}">{displayStatus}</span>
                    {#if item.content_category}
                      <span class="badge badge-category">{item.content_category}</span>
                    {/if}
                  </div>
                </div>
              </div>
            </td>
            <td class="col-sentiment">
              <span class="sentiment-score" style="color: {getSentimentColor(item.sentiment_score)}">
                {formatSentimentScore(item.sentiment_score)}
              </span>
            </td>
          </tr>
        {/each}

        {#if paginatedItems.length === 0}
          <tr>
            <td colspan="3" class="empty-cell">No articles match your criteria.</td>
          </tr>
        {/if}
      </tbody>
    </table>
  </div>

  {@render paginationControls()}
</div>

<ArticleDetailsSheet bind:hnId={selectedArticleId} bind:open={sheetOpen} />

<style>
  .content-table-section {
    padding: 1.5rem;
    background: var(--color-card);
    border: 1px solid var(--color-border);
    border-radius: 0.75rem;
  }

  .section-title {
    font-family: var(--font-mono);
    font-size: 1rem;
    font-weight: 600;
    color: var(--color-foreground);
    margin: 0 0 0.25rem 0;
    text-align: center;
  }

  .section-subtitle {
    font-size: 0.75rem;
    color: var(--color-muted-foreground);
    margin: 0 0 1rem 0;
    text-align: center;
  }

  /* Controls Section */
  .controls-section {
    padding-bottom: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .filter-toggle-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    border-radius: 0.5rem;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    background: var(--color-muted);
    color: var(--color-muted-foreground);
    border: 1px solid var(--color-border);
    transition: all 0.15s var(--ease-swift);
    align-self: flex-start;
  }

  .filter-toggle-btn:hover {
    background: var(--color-muted);
    color: var(--color-foreground);
    border-color: var(--color-border);
  }

  .controls-drawer {
    overflow: hidden;
    transition: all 0.3s var(--ease-swift);
    max-height: 0;
    opacity: 0;
  }

  .controls-drawer.open {
    max-height: 24rem;
    opacity: 1;
  }

  .controls-content {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding-top: 0.5rem;
  }

  .controls-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
  }

  .relevant-toggle {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.375rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    background: var(--color-muted);
    color: var(--color-muted-foreground);
    border: 1px solid var(--color-border);
    transition: all 0.15s var(--ease-swift);
  }

  .relevant-toggle.active {
    background: color-mix(in srgb, var(--color-primary), transparent 80%);
    color: var(--color-primary);
    border-color: var(--color-primary);
  }

  .toggle-dot {
    width: 0.5rem;
    height: 0.5rem;
    border-radius: 50%;
    background: var(--color-muted-foreground);
    opacity: 0.5;
  }

  .toggle-dot.active {
    background: var(--color-primary);
    opacity: 1;
  }

  .search-wrapper {
    flex: 1;
    min-width: 12rem;
  }

  /* Table Styles */
  .table-wrapper {
    overflow-x: auto;
  }

  .articles-table {
    width: 100%;
    border-collapse: collapse;
    font-family: var(--font-mono);
    font-size: 0.8rem;
  }

  .articles-table th {
    text-align: left;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid var(--color-border);
    color: var(--color-muted-foreground);
    font-weight: 500;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .articles-table td {
    padding: 0.625rem 0.75rem;
    border-bottom: 1px solid var(--color-border);
    color: var(--color-foreground);
    vertical-align: middle;
  }

  .articles-table tbody tr:last-child td {
    border-bottom: none;
  }

  .article-row {
    transition: background-color 0.15s var(--ease-swift);
  }

  .article-row.clickable {
    cursor: pointer;
  }

  .article-row:hover {
    background: var(--color-muted);
  }

  .article-row:hover .title-link {
    text-decoration: underline;
  }

  .article-row:hover .summary-track {
    animation: marquee var(--marquee-duration, 8s) linear infinite;
  }

  /* Sort button */
  .sort-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    background: none;
    border: none;
    padding: 0;
    color: var(--color-muted-foreground);
    font-family: inherit;
    font-size: inherit;
    font-weight: inherit;
    text-transform: inherit;
    letter-spacing: inherit;
    cursor: pointer;
    transition: color 0.15s var(--ease-swift);
  }

  .sort-btn:hover {
    color: var(--color-foreground);
  }

  :global(.sort-icon) {
    width: 0.75rem;
    height: 0.75rem;
  }

  /* Column widths */
  .col-time {
    width: 5.5rem;
  }

  .col-title {
    min-width: 280px;
    max-width: 600px;
  }

  .col-sentiment {
    width: 6rem;
    text-align: center;
  }

  .time-ago {
    font-weight: 500;
    color: var(--color-foreground);
  }

  /* Title cell */
  .title-cell {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .title-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .title-link {
    color: var(--color-primary);
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    overflow: hidden;
    font-weight: 500;
    flex: 1;
    min-width: 0;
    font-family: var(--font-mono);
    background: none;
    border: none;
    padding: 0;
    cursor: pointer;
    text-align: left;
    font-size: inherit;
  }

  .title-link:hover {
    text-decoration: underline;
  }

  .title-text-content {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .title-chevron {
    flex-shrink: 0;
    opacity: 0;
    transition: opacity 0.15s var(--ease-swift);
    color: var(--color-primary);
  }

  .article-row:hover .title-chevron {
    opacity: 1;
  }

  .title-text {
    color: var(--color-foreground);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
    font-family: var(--font-mono);
  }

  .domain-anchor {
    color: var(--color-primary);
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    font-family: var(--font-mono);
    font-size: 0.7rem;
    flex-shrink: 0;
  }

  .domain-anchor:hover {
    text-decoration: underline;
  }

  .title-meta {
    display: inline-flex;
    align-items: center;
    font-size: 0.7rem;
    flex-shrink: 0;
  }

  .hn-link {
    display: inline-flex;
    align-items: center;
    color: var(--hn-link-color, #ff6600);
    text-decoration: none;
  }

  .hn-link:hover {
    text-decoration: underline;
  }

  /* Summary row with badges */
  .summary-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  /* Summary cell with marquee effect */
  .summary-cell {
    position: relative;
    overflow: hidden;
    height: 1.25rem;
    cursor: default;
    flex: 1;
    min-width: 0;
  }

  .summary-track {
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    white-space: nowrap;
    transition: transform 0.3s var(--ease-swift);
  }

  .summary-text {
    display: inline-block;
    font-size: 0.7rem;
    color: var(--color-muted-foreground);
    padding-right: 2rem;
  }

  @keyframes marquee {
    0% {
      transform: translateY(-50%) translateX(0);
    }
    100% {
      transform: translateY(-50%) translateX(calc(-100% + 480px));
    }
  }

  /* Fade edges for summary */
  .summary-cell::after {
    content: "";
    position: absolute;
    right: 0;
    top: 0;
    bottom: 0;
    width: 2rem;
    background: linear-gradient(to right, transparent, var(--color-card));
    pointer-events: none;
  }

  .articles-table tbody tr:hover .summary-cell::after {
    background: linear-gradient(to right, transparent, var(--color-muted));
  }

  /* Badges in summary row */
  .summary-badges {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    flex-shrink: 0;
  }

  .badge {
    font-family: var(--font-mono);
    font-size: 0.55rem;
    font-weight: 600;
    padding: 0.125rem 0.375rem;
    border-radius: var(--radius-sm);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    white-space: nowrap;
  }

  .badge-category {
    background: rgba(168, 85, 247, 0.25);
    color: #9333ea;
  }

  /* Status badge colors */
  .badge-status-resolved {
    background: color-mix(in srgb, var(--color-primary), transparent 75%);
    color: var(--color-primary);
  }

  .badge-status-scraped {
    background: rgba(59, 130, 246, 0.25);
    color: #2563eb;
  }

  .badge-status-analyzed {
    background: rgba(168, 85, 247, 0.25);
    color: #7c3aed;
  }

  .badge-status-failed {
    background: rgba(239, 68, 68, 0.25);
    color: #dc2626;
  }

  .badge-status-pending {
    background: rgba(234, 179, 8, 0.25);
    color: #ca8a04;
  }

  .badge-status-missing-metadata {
    background: rgba(249, 115, 22, 0.25);
    color: #ea580c;
  }

  .badge-status-skipped {
    background: rgba(100, 116, 139, 0.25);
    color: #475569;
  }

  /* Sentiment score */
  .sentiment-score {
    font-weight: 700;
    font-size: 1rem;
    font-family:
      system-ui,
      -apple-system,
      BlinkMacSystemFont,
      "Segoe UI",
      Roboto,
      sans-serif;
    letter-spacing: -0.02em;
    line-height: 1;
    display: block;
    text-align: center;
  }

  .empty-cell {
    height: 6rem;
    text-align: center;
    color: var(--color-muted-foreground);
  }

  /* Pagination Controls */
  .pagination-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 0;
    border-top: 1px solid var(--color-border);
    margin-top: 0.75rem;
  }

  .pagination-controls:first-of-type {
    border-top: none;
    margin-top: 0;
    margin-bottom: 0.75rem;
    border-bottom: 1px solid var(--color-border);
    padding-bottom: 0.75rem;
    padding-top: 0;
  }

  .pagination-info {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--color-muted-foreground);
  }

  .text-muted {
    color: var(--color-muted-foreground);
  }

  .text-bold {
    font-weight: 600;
    color: var(--color-foreground);
  }

  .pagination-nav {
    display: inline-flex;
    align-items: center;
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
    overflow: hidden;
    background: var(--color-card);
  }

  .pagination-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.5rem 0.625rem;
    background: transparent;
    border: none;
    color: var(--color-muted-foreground);
    cursor: pointer;
    transition: all 0.15s var(--ease-swift);
    font-family: var(--font-mono);
    font-size: 0.875rem;
  }

  .pagination-btn:hover:not(:disabled) {
    background: var(--color-muted);
    color: var(--color-foreground);
  }

  .pagination-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .pagination-page-display {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0 0.625rem;
    border-left: 1px solid var(--color-border);
    border-right: 1px solid var(--color-border);
    background: transparent;
    color: var(--color-muted-foreground);
    font-family: var(--font-mono);
    font-size: 0.875rem;
  }

  .pagination-page-input {
    background: transparent;
    border: none;
    text-align: center;
    width: 2rem;
    color: var(--color-foreground);
    font-family: var(--font-mono);
    font-size: 0.875rem;
    padding: 0;
  }

  .pagination-page-input:focus {
    outline: none;
  }

  .pagination-separator {
    opacity: 0.5;
  }

  .pagination-total {
    font-weight: 600;
  }

  /* Responsive adjustments */
  @media (max-width: 768px) {
    .content-table-section {
      padding: 1rem;
    }

    .articles-table {
      font-size: 0.75rem;
    }

    .articles-table th,
    .articles-table td {
      padding: 0.4rem 0.5rem;
    }

    .col-title {
      max-width: 180px;
    }

    .summary-badges {
      display: none;
    }

    .col-time {
      width: 4.5rem;
    }

    .pagination-controls {
      flex-direction: column;
      gap: 0.5rem;
    }
  }

  @media (max-width: 480px) {
    .col-time {
      display: none;
    }

    .title-meta {
      flex-wrap: wrap;
    }

    .summary-badges {
      display: none;
    }
  }
</style>
