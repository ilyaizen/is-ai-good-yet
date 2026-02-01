<script lang="ts">
  import type { InfluentialArticle } from "$lib/server/db"
  import { NEUTRAL_MULTIPLIER } from "$lib/constants"
  import { ChevronDown, ChevronUp, ChevronRight, ExternalLink, LayoutList } from "lucide-svelte"
  import * as Select from "$lib/components/ui/select"
  import * as InputGroup from "$lib/components/ui/input-group"
  import { page } from "$app/stores"
  import { goto } from "$app/navigation"
  import { browser } from "$app/environment"
  import ArticleDetailsSheet from "./article-details-sheet.svelte"
  import HoverIcon from "./hover-icon.svelte"
  import LinkWithHoverIcon from "./link-with-hover-icon.svelte"

  let { articles }: { articles: InfluentialArticle[] } = $props()

  // Sheet state
  let sheetOpen = $state(false)
  let selectedArticleId = $state<number | null>(null)

  function openArticleSheet(hnId: number) {
    selectedArticleId = hnId
    sheetOpen = true
  }

  const TIME_DECAY_MONTHS = 6
  const TIME_WINDOW_YEARS = 3
  const TIME_DECAY_MS = TIME_DECAY_MONTHS * 30 * 24 * 60 * 60 * 1000
  const TIME_WINDOW_MS = TIME_WINDOW_YEARS * 365 * 24 * 60 * 60 * 1000

  const COLOR_GREEN = "#5c9e24"
  const COLOR_YELLOW = "#f59e0b"
  const COLOR_RED = "#ef4444"

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

  function getTimeColor(timestamp: number): string {
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

  // URL parameter helper
  function getParam<T>(key: string, defaultVal: T, parser?: (v: string) => T): T {
    const val = $page.url.searchParams.get(key)
    if (val === null) return defaultVal
    if (parser) return parser(val)
    if (typeof defaultVal === "number") return parseInt(val) as T
    return val as T
  }

  // Pagination state
  const initialPage = getParam("page", 1)
  let currentPage = $state(initialPage)
  let pageInput = $state(initialPage.toString())
  const initialPerPage = getParam("per_page", 20)
  let itemsPerPage = $state(initialPerPage)
  let isInitialized = $state(false)

  // Sync URL parameters
  $effect(() => {
    if (!browser) return
    if (!isInitialized) {
      isInitialized = true
      return
    }

    const url = new URL($page.url)
    const updateParam = (key: string, val: any, def: any) => {
      if (val !== def) url.searchParams.set(key, String(val))
      else url.searchParams.delete(key)
    }

    updateParam("per_page", itemsPerPage, 20)
    updateParam("page", currentPage, 1)

    if (url.toString() !== $page.url.toString()) {
      goto(url, { replaceState: true, keepFocus: true, noScroll: true })
    }
  })

  // Sync pageInput with currentPage
  $effect(() => {
    pageInput = currentPage.toString()
  })

  // Reset to page 1 if current page exceeds total pages
  $effect(() => {
    if (currentPage > totalPages && totalPages > 0) {
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

  function getCategories(article: InfluentialArticle): string[] {
    if (!article.content_category) return []
    return article.content_category
      .split(",")
      .map((c) => c.trim())
      .filter((c) => c !== "AI_DISCOURSE")
  }

  function getTopic(article: InfluentialArticle): string | null {
    return article.topic || null
  }

  // Calculate the contribution score - this is the final verdict impact
  // Positive/Negative articles: sentiment × influence (full contribution based on sentiment direction)
  // Neutral articles: influence × NEUTRAL_MULTIPLIER (sentiment is always 0, so use influence directly)
  function getContribution(article: InfluentialArticle): number {
    // Neutral articles (-0.2 to +0.2) have sentiment ≈ 0 (only mixed+uncertain = 0)
    // Use influence directly, scaled by NEUTRAL_MULTIPLIER
    if (article.sentiment_score >= -0.2 && article.sentiment_score <= 0.2) {
      return article.influenceScore * NEUTRAL_MULTIPLIER
    }
    // Positive/negative articles use sentiment × influence
    return article.sentiment_score * article.influenceScore
  }

  // Sorting state
  type SortField = "hn_timestamp" | "hn_score" | "sentiment_score" | "influenceScore" | "contribution" | "url"
  let sortField = $state<SortField>("hn_timestamp")
  let sortDirection = $state<"asc" | "desc">("desc")

  // Sort articles
  let sortedArticles = $derived(
    [...articles].sort((a, b) => {
      // Handle computed contribution field
      let valA: number | null | string
      let valB: number | null | string
      if (sortField === "contribution") {
        valA = getContribution(a)
        valB = getContribution(b)
      } else {
        valA = a[sortField]
        valB = b[sortField]
      }
      if (valA === valB) return 0
      if (valA === null || valA === undefined) return 1
      if (valB === null || valB === undefined) return -1

      if (typeof valA === "string" && typeof valB === "string") {
        const comparison = valA.localeCompare(valB)
        return sortDirection === "asc" ? comparison : -comparison
      }

      const comparison = (valA as number) < (valB as number) ? -1 : 1
      return sortDirection === "asc" ? comparison : -comparison
    })
  )

  // Pagination
  let totalPages = $derived(Math.ceil(sortedArticles.length / itemsPerPage))
  let paginatedArticles = $derived(sortedArticles.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage))

  // Calculate relative bar width based on absolute contribution (top article = 100%, others scaled proportionally)
  let maxAbsContribution = $derived(
    sortedArticles.length > 0 ? Math.max(...sortedArticles.map((a) => Math.abs(getContribution(a)))) : 1
  )

  function getRelativeWidth(article: InfluentialArticle): number {
    return (Math.abs(getContribution(article)) / maxAbsContribution) * 100
  }

  function getSentimentColor(label: "positive" | "negative" | "neutral"): string {
    switch (label) {
      case "positive":
        return "var(--color-primary)"
      case "negative":
        return "var(--color-destructive)"
      default:
        return "var(--color-warning)"
    }
  }

  // Format sentiment score with +/- prefix and two decimal places (in -1 to +1 scale)
  function formatSentimentScore(score: number): string {
    const prefix = score >= 0 ? "+" : ""
    return `${prefix}${score.toFixed(2)}`
  }

  // Calculate the product of sentiment score and influence score
  function calculateSentimentProduct(sentiment: number, influence: number): number {
    return sentiment * influence
  }

  // Format sentiment product result with no decimal places
  function formatSentimentProduct(value: number): string {
    const prefix = value >= 0 ? "+" : ""
    return `${prefix}${value.toFixed(0)}`
  }

  function handleSort(field: SortField) {
    if (sortField === field) {
      sortDirection = sortDirection === "asc" ? "desc" : "asc"
    } else {
      sortField = field
      sortDirection = "desc"
    }
  }

  function formatTimeAgo(timestamp: number): string {
    const now = new Date()
    const date = new Date(timestamp * 1000)
    const diffMs = now.getTime() - date.getTime()
    const diffSecs = Math.floor(diffMs / 1000)
    const diffMins = Math.floor(diffSecs / 60)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)
    const diffWeeks = Math.floor(diffDays / 7)
    const diffYears = Math.floor(diffWeeks / 52)

    if (diffSecs < 60) return "now"
    if (diffMins < 60) return `${diffMins}m`
    if (diffHours < 24) return `${diffHours}h`
    if (diffDays < 7) return `${diffDays}d`
    if (diffWeeks < 52) return `${diffWeeks}w`
    return `${diffYears}y`
  }

  function formatDate(timestamp: number): string {
    return new Date(timestamp * 1000).toISOString().split("T")[0]
  }

  function getDomain(url: string): string {
    try {
      const urlObj = new URL(url)
      let domain = urlObj.hostname
      return domain.replace(/^www\./, "")
    } catch {
      return url.replace(/^www\./, "")
    }
  }
</script>

{#snippet paginationControls()}
  <div class="flex flex-col gap-3">
    <div class="flex flex-col sm:flex-row items-center justify-between gap-3 text-sm">
      <div class="w-full sm:w-auto">
        <InputGroup.Root class="w-auto gap-2 text-sm">
          <InputGroup.Addon>
            <LayoutList class="h-4 w-4" />
          </InputGroup.Addon>
          <Select.Root
            type="single"
            value={itemsPerPage.toString()}
            onValueChange={(v) => {
              itemsPerPage = parseInt(v)
              currentPage = 1
            }}>
            <Select.Trigger class="w-40 border-none! shadow-none! bg-transparent! text-muted-foreground">
              show {itemsPerPage} results
            </Select.Trigger>
            <Select.Content>
              <Select.Item value="10" label="show 10 results" />
              <Select.Item value="20" label="show 20 results" />
              <Select.Item value="50" label="show 50 results" />
              <Select.Item value="100" label="show 100 results" />
            </Select.Content>
          </Select.Root>
        </InputGroup.Root>
      </div>

      <nav class="flex items-center gap-2" aria-label="Pagination">
        <button
          onclick={() => (currentPage = Math.max(1, currentPage - 1))}
          disabled={currentPage === 1}
          class="reveal-btn p-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Previous page">
          <ChevronDown class="h-4 w-4 rotate-90" />
        </button>
        <div class="flex items-center gap-1 font-mono text-muted-foreground px-2">
          <input
            type="text"
            class="w-8 h-6 bg-transparent text-center text-foreground font-medium rounded-sm border border-transparent hover:border-border focus:border-accent focus:outline-none transition-colors"
            bind:value={pageInput}
            onblur={commitPageChange}
            onkeydown={(e) => e.key === "Enter" && commitPageChange()}
            aria-label="Current page" />
          <span class="opacity-50">/</span>
          <span class="w-8 text-center">{Math.max(1, totalPages)}</span>
        </div>
        <button
          onclick={() => (currentPage = Math.min(totalPages, currentPage + 1))}
          disabled={currentPage === totalPages || totalPages === 0}
          class="reveal-btn p-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Next page">
          <ChevronDown class="h-4 w-4 -rotate-90" />
        </button>
      </nav>
    </div>

    <div class="text-right text-xs">
      <span class="text-muted-foreground">
        showing <span class="font-bold text-foreground">{(currentPage - 1) * itemsPerPage + 1}</span>
        to <span class="font-bold text-foreground">{Math.min(currentPage * itemsPerPage, sortedArticles.length)}</span>
        of <span class="font-bold text-foreground">{sortedArticles.length}</span>
      </span>
    </div>
  </div>
{/snippet}

<div class="mt-8 terminal-panel p-4 sm:p-6 md:p-8">
  <div class="flex items-center gap-1 mb-4 sm:mb-6">
    <ChevronRight color="var(--color-accent)" strokeWidth={3} />
    <span class="font-mono font-semibold text-base sm:text-lg">articles:</span>
  </div>

  {@render paginationControls()}

  <div class="overflow-x-auto mb-4 sm:mb-6">
    <table class="w-full border-collapse font-mono text-[0.8rem] md:text-[0.75rem]">
      <thead>
        <tr>
          <th
            class="p-2 sm:p-3 border-b border-border text-muted-foreground font-medium text-[0.7rem] uppercase tracking-wider w-14 text-center sm:w-12 max-[480px]:hidden">
            <button
              class="inline-flex items-center gap-1 bg-none border-none p-0 text-muted-foreground font-inherit font-medium uppercase tracking-wider cursor-pointer transition-colors hover:text-foreground"
              onclick={() => handleSort("hn_timestamp")}
              title="Sort by time">
              Age
              {#if sortField === "hn_timestamp"}
                {#if sortDirection === "asc"}
                  <ChevronUp class="w-3 h-3" />
                {:else}
                  <ChevronDown class="w-3 h-3" />
                {/if}
              {/if}
            </button>
          </th>
          <th
            class="text-left p-2 sm:p-3 border-b border-border text-muted-foreground font-medium text-[0.7rem] uppercase tracking-wider min-w-70 max-w-120 max-[768px]:max-w-45">
            <button
              class="inline-flex items-center gap-1 bg-none border-none p-0 text-muted-foreground font-inherit font-medium uppercase tracking-wider cursor-pointer transition-colors hover:text-foreground"
              onclick={() => handleSort("url")}
              title="Sort by URL">
              Title / URL
              {#if sortField === "url"}
                {#if sortDirection === "asc"}
                  <ChevronUp class="w-3 h-3" />
                {:else}
                  <ChevronDown class="w-3 h-3" />
                {/if}
              {/if}
            </button>
          </th>
          <th
            class="p-2 sm:p-3 border-b border-border text-muted-foreground font-medium text-[0.7rem] uppercase tracking-wider w-16 text-center">
            <button
              class="inline-flex items-center gap-1 bg-none border-none p-0 text-muted-foreground font-inherit font-medium uppercase tracking-wider cursor-pointer transition-colors hover:text-foreground"
              onclick={() => handleSort("contribution")}
              title="Sort by verdict contribution (sentiment × influence)">
              Score
              {#if sortField === "contribution"}
                {#if sortDirection === "asc"}
                  <ChevronUp class="w-3 h-3" />
                {:else}
                  <ChevronDown class="w-3 h-3" />
                {/if}
              {/if}
            </button>
          </th>
        </tr>
      </thead>
      <tbody>
        {#each paginatedArticles as article, index}
          {@const relativeWidth = getRelativeWidth(article)}
          {@const sentimentColor = getSentimentColor(article.sentiment_label)}
          <tr
            class="group cursor-pointer transition-colors duration-150 ease-swift hover:bg-muted"
            onclick={() => openArticleSheet(article.hn_id)}>
            <td
              class="p-2.5 sm:p-2 border-b border-border text-foreground align-middle last:border-b-0 w-14 text-center max-[480px]:hidden">
              <span
                class="font-bold text-base font-mono tracking-tight leading-none text-foreground"
                style="color: {getTimeColor(article.hn_timestamp)}"
                title={formatDate(article.hn_timestamp)}>
                {formatTimeAgo(article.hn_timestamp)}
              </span>
            </td>
            <td
              class="p-2.5 sm:p-2 border-b border-border text-foreground align-middle last:border-b-0 min-w-70 max-w-120 max-[768px]:max-w-45">
              <div class="flex flex-col gap-0.5">
                <div class="flex items-center gap-2 justify-between">
                  <button
                    type="button"
                    class="text-foreground no-underline flex items-center gap-1 overflow-hidden font-bold font-mono text-left flex-1 min-w-0 cursor-pointer group-hover:text-accent group-hover:underline"
                    title={article.hn_title}
                    onclick={(e: MouseEvent) => {
                      e.stopPropagation()
                      openArticleSheet(article.hn_id)
                    }}>
                    <span class="overflow-hidden text-ellipsis whitespace-nowrap">{article.hn_title}</span>
                    <HoverIcon showOnHover={true}>
                      {#snippet icon()}
                        <ChevronRight class="w-4 h-4 text-accent" />
                      {/snippet}
                    </HoverIcon>
                  </button>
                  <div class="inline-flex items-center gap-2 shrink-0 max-[480px]:text-[0.65rem]">
                    <LinkWithHoverIcon
                      href={article.url}
                      title="Open original article"
                      onclick={(e) => e.stopPropagation()}
                      className="text-accent no-underline font-mono text-[0.8rem] hover:underline">
                      {#snippet children()}
                        {getDomain(article.url)}
                      {/snippet}
                      {#snippet icon()}
                        <ExternalLink class="size-3" />
                      {/snippet}
                    </LinkWithHoverIcon>
                    <LinkWithHoverIcon
                      href={`https://news.ycombinator.com/item?id=${article.hn_id}`}
                      onclick={(e: MouseEvent) => e.stopPropagation()}
                      title={`Open HN page | ${article.hn_score} points / ${article.hn_comments} comments`}
                      className="text-(--hn-link-color) no-underline font-bold text-[0.8rem] hover:underline">
                      {#snippet children()}
                        {article.hn_score}/{article.hn_comments}
                      {/snippet}
                      {#snippet icon()}
                        <ExternalLink class="size-3" />
                      {/snippet}
                    </LinkWithHoverIcon>
                  </div>
                </div>
                <div
                  class="relative overflow-hidden h-5"
                  style="mask-image: linear-gradient(to right, black calc(100% - 2rem), transparent); -webkit-mask-image: linear-gradient(to right, black calc(100% - 2rem), transparent);"
                  title={article.summary}>
                  <div
                    class="absolute left-0 top-1/2 -translate-y-1/2 whitespace-nowrap group-hover:animate-[marquee_8s_linear_infinite] will-change-transform">
                    <span class="inline-block text-[0.7rem] text-muted-foreground pr-8">{article.summary || ""}</span>
                    <span class="inline-block text-[0.7rem] text-muted-foreground pr-8">{article.summary || ""}</span>
                  </div>
                </div>
              </div>
            </td>
            <td
              class="p-2.5 sm:p-2 text-foreground align-middle last:border-b-0 w-16 text-center"
              style="border-bottom: 1px solid var(--border);">
              <div class="flex flex-col justify-center items-center gap-px leading-none">
                <span
                  class="font-bold text-base font-mono tracking-tight leading-none block"
                  style="color: {sentimentColor}">
                  {formatSentimentProduct(getContribution(article))}
                </span>
              </div>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>

  {@render paginationControls()}
</div>

<ArticleDetailsSheet bind:hnId={selectedArticleId} bind:open={sheetOpen} />
