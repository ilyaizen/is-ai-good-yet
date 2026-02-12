<script lang="ts">
  import { ChevronRight, ExternalLink, Info } from "lucide-svelte"
  import ThemeItem from "./theme-item.svelte"
  import AnimatedButton from "$lib/components/ui/animated-button.svelte"
  import { onMount } from "svelte"
  import themesData from "$lib/data/themes.json"
  import articlesData from "$lib/data/articles.json"
  import verdictData from "$lib/data/verdict.json"
  import Marquee from "$lib/components/ui/marquee.svelte"
  import ArticleDetailsSheet from "$lib/components/landing/article-details-sheet.svelte"
  import { scrollToBottom } from "$lib/scroll"
  import { cn } from "$lib/utils"

  // Props
  let { visible = false }: { visible?: boolean } = $props()

  // State
  let entering = $state(true)
  let titleInView = $state(false)
  let titleElement: HTMLElement | undefined = $state()
  let articlesButtonHovered = $state(false)
  let articlesButtonFocused = $state(false)
  let aboutButtonHovered = $state(false)
  let aboutButtonFocused = $state(false)

  // Quote processing
  type Quote = { text: string; sentiment: "positive" | "negative" | "neutral"; hnId: number }
  let row1: Quote[] = $state([])
  let row2: Quote[] = $state([])
  let row3: Quote[] = $state([])

  // Sheet state
  let sheetOpen = $state(false)
  let selectedArticleId = $state<number | null>(null)

  function openArticleSheet(hnId: number) {
    selectedArticleId = hnId
    sheetOpen = true
  }

  // Top articles per sentiment group (sorted by influence)
  type ArticleLink = { hnId: number; title: string; url: string; score: number }

  const topArticlesBySentiment = $derived.by(() => {
    const groups: Record<string, ArticleLink[]> = { positive: [], negative: [], neutral: [] }
    for (const a of articlesData) {
      const label = a.sentiment_label || "neutral"
      if (groups[label]) {
        groups[label].push({
          hnId: a.hn_id,
          title: a.hn_title,
          url: a.url || `https://news.ycombinator.com/item?id=${a.hn_id}`,
          score: a.influenceScore,
        })
      }
    }
    // Sort by influence, take top 5
    for (const key of Object.keys(groups)) {
      groups[key] = groups[key].sort((a, b) => b.score - a.score).slice(0, 0)
    }
    return groups
  })

  // Pipeline stats from verdict data
  const stats = verdictData.current
  const permanent = verdictData.permanent
  const pipeline = verdictData.pipeline

  $effect(() => {
    // Extract quotes from articles
    const allQuotes: Quote[] = articlesData.flatMap((article) => {
      const qList = (article.quotes || []) as string[]
      const sentiment = (article.sentiment_label || "neutral") as "positive" | "negative" | "neutral"

      return qList
        .filter((q) => q.length > 20 && q.length < 150)
        .map((text) => ({
          text: text.replace(/^"|"$/g, "").trim(),
          sentiment,
          hnId: article.hn_id,
        }))
    })

    const shuffled = allQuotes.sort(() => 0.5 - Math.random())
    const perRow = 15
    row1 = shuffled.slice(0, perRow)
    row2 = shuffled.slice(perRow, perRow * 2)
    row3 = shuffled.slice(perRow * 2, perRow * 3)
  })

  // Typing animation state
  let typedLabel = $state("")
  let labelTypingComplete = $state(false)
  const LABEL_TEXT = "details:"

  function scrollToArticles() {
    const el = document.getElementById("articles-table")
    if (el) {
      el.scrollIntoView({ behavior: "smooth" })
    }
  }

  function typeLabel() {
    let charIndex = 0
    const typeNextChar = () => {
      if (charIndex < LABEL_TEXT.length) {
        charIndex += 1
        typedLabel = LABEL_TEXT.slice(0, charIndex)
        setTimeout(typeNextChar, 30)
      } else {
        labelTypingComplete = true
      }
    }
    setTimeout(typeNextChar, 100)
  }

  onMount(() => {
    if (visible) {
      entering = false
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            titleInView = true
            observer.disconnect()
          }
        })
      },
      { threshold: 0.1 }
    )

    if (titleElement) {
      observer.observe(titleElement)
    }

    return () => {
      observer.disconnect()
    }
  })

  $effect(() => {
    if (visible) {
      entering = false
    }

    if (visible && titleInView && typedLabel === "") {
      typeLabel()
    }
  })
</script>

<div class="w-full flex justify-center px-4 py-8">
  <section
    class="terminal-panel p-8 w-full max-w-5xl transform transition-all duration-500 ease-swift"
    class:opacity-0={!visible}
    class:translate-y-8={!visible}
    class:opacity-100={visible}
    class:translate-y-0={visible}
    aria-label="Project Details">
    <!-- Header -->
    <div class="flex items-center gap-1 mb-8" bind:this={titleElement}>
      <ChevronRight color="var(--color-accent)" strokeWidth={3} />
      <span class="font-mono font-semibold text-base">
        {typedLabel}
        {#if !labelTypingComplete}
          <span class="cursor"></span>
        {/if}
      </span>
    </div>

    <!-- Live Feed Marquees -->
    <div class="mt-8 w-full overflow-hidden mask-fade-sides">
      {#snippet quoteItem(quote: Quote)}
        <button
          class={cn(
            "flex items-center gap-1 px-1 py-1 rounded backdrop-blur-sm shadow-sm cursor-pointer text-left font-mono whitespace-nowrap text-xs transition-colors",
            {
              "text-primary bg-primary/15 border border-primary/30 hover:bg-primary/25": quote.sentiment === "positive",
              "text-destructive bg-destructive/15 border border-destructive/30 hover:bg-destructive/25":
                quote.sentiment === "negative",
              "text-warning bg-warning/15 border border-warning/30 hover:bg-warning/25": quote.sentiment === "neutral",
            }
          )}
          onclick={() => openArticleSheet(quote.hnId)}>
          "{quote.text}"
        </button>
      {/snippet}

      <div class="flex flex-col relative">
        <Marquee pauseOnHover={false} reverseOnHover={true} speed={300} class="" reverse={false}>
          {#each row1 as quote}
            {@render quoteItem(quote)}
          {/each}
        </Marquee>

        <Marquee pauseOnHover={false} reverseOnHover={true} speed={300} class="" reverse={true}>
          {#each row2 as quote}
            {@render quoteItem(quote)}
          {/each}
        </Marquee>

        <Marquee pauseOnHover={false} reverseOnHover={true} speed={300} class="" reverse={false}>
          {#each row3 as quote}
            {@render quoteItem(quote)}
          {/each}
        </Marquee>

        <!-- Fade edges -->
        <div
          class="pointer-events-none absolute inset-y-0 left-0 w-16 bg-linear-to-r from-terminal-background via-terminal-background/50 to-transparent z-10">
        </div>
        <div
          class="pointer-events-none absolute inset-y-0 right-0 w-16 bg-linear-to-l from-terminal-background via-terminal-background/50 to-transparent z-10">
        </div>
      </div>
    </div>

    <!-- Themes Summary -->
    <div class="space-y-4 font-mono my-8 summary-section">
      <h3 class="text-sm font-bold text-foreground uppercase tracking-wide mb-3">Summary</h3>
      <div class="text-sm text-foreground leading-relaxed">
        <p>
          it appears AI coding tools offer real advantages and help smaller teams ship faster. however, these gains come
          with heavy review overhead, serious reliability issues, risks of skill degradation, and questionable long-term
          economics. most experienced developers view them as a powerful but fallible, and consider over-reliance on
          them to be dangerous.
        </p>
      </div>
    </div>

    <!-- Synthesized Themes -->
    <div class="space-y-3 font-mono">
      <h3 class="text-sm font-bold text-foreground uppercase tracking-wide">Themes</h3>

      <!-- Positive Themes -->
      {#if themesData.positive && themesData.positive.length > 0}
        <div class="theme-group">
          <div class="text-primary font-bold mb-2 flex items-center gap-2">
            <span class="text-xs border border-primary/30 px-2 py-0.5 rounded bg-primary/10 uppercase">The Good</span>
          </div>
          <div class="space-y-0.5 pl-4 border-l-2 border-primary/20 lowercase">
            {#each themesData.positive.slice(0, 3) as theme}
              <ThemeItem title={theme.title} description={theme.description} sentiment="positive" />
            {/each}
          </div>
          <!-- Top articles -->
          {#if topArticlesBySentiment.positive.length > 0}
            <div class="mt-3 pl-4 space-y-1">
              {#each topArticlesBySentiment.positive as article}
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  class="group/link article-link-row"
                  title={article.title}>
                  <ExternalLink class="w-3.5 h-3.5 text-primary shrink-0" />
                  <span class="truncate">{article.title}</span>
                </a>
              {/each}
            </div>
          {/if}
        </div>
      {/if}

      <!-- Neutral Themes -->
      {#if themesData.neutral && themesData.neutral.length > 0}
        <div class="theme-group">
          <div class="text-warning font-bold mb-2 flex items-center gap-2">
            <span class="text-xs border border-warning/30 px-2 py-0.5 rounded bg-warning/10 uppercase"
              >The Neutral</span>
          </div>
          <div class="space-y-0.5 pl-4 border-l-2 border-warning/20">
            {#each themesData.neutral.slice(0, 3) as theme}
              <ThemeItem title={theme.title} description={theme.description} sentiment="neutral" />
            {/each}
          </div>
          {#if topArticlesBySentiment.neutral.length > 0}
            <div class="mt-3 pl-4 space-y-1">
              {#each topArticlesBySentiment.neutral as article}
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  class="group/link article-link-row"
                  title={article.title}>
                  <ExternalLink class="w-3.5 h-3.5 text-primary shrink-0" />
                  <span class="truncate">{article.title}</span>
                </a>
              {/each}
            </div>
          {/if}
        </div>
      {/if}

      <!-- Negative Themes -->
      {#if themesData.negative && themesData.negative.length > 0}
        <div class="theme-group">
          <div class="text-destructive font-bold mb-2 flex items-center gap-2">
            <span class="text-xs border border-destructive/30 px-2 py-0.5 rounded bg-destructive/10 uppercase"
              >The Bad</span>
          </div>
          <div class="space-y-0.5 pl-4 border-l-2 border-destructive/20">
            {#each themesData.negative.slice(0, 3) as theme}
              <ThemeItem title={theme.title} description={theme.description} sentiment="negative" />
            {/each}
          </div>
          {#if topArticlesBySentiment.negative.length > 0}
            <div class="mt-3 pl-4 space-y-1">
              {#each topArticlesBySentiment.negative as article}
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  class="group/link article-link-row"
                  title={article.title}>
                  <ExternalLink class="w-3.5 h-3.5 text-primary shrink-0" />
                  <span class="truncate">{article.title}</span>
                </a>
              {/each}
            </div>
          {/if}
        </div>
      {/if}
    </div>

    <!-- Methodology -->
    <div class="space-y-6 font-mono">
      <div class="methodology-section">
        <h3 class="text-sm font-bold text-foreground uppercase tracking-wide mt-8 mb-3">How It Works</h3>
        <div class="text-sm text-foreground leading-relaxed space-y-3">
          <p>
            <strong class="text-foreground">is AI “good” yet?</strong> tracks hacker news to see what devs
            <i>actually</i>
            think about AI coding tools. it runs a multi-stage python pipeline that collects AI-tagged submissions via
            <a href="https://histre.com/hn/?tags=+ai" target="_blank" rel="noopener noreferrer" class="article-link"
              >histre</a
            >, resolves them using
            <a href="https://hn.algolia.com" target="_blank" rel="noopener noreferrer" class="article-link">algolia</a>,
            scrapes all possible links, uses an llm to first filter out noise, then performs the actual sentiment
            analysis. each article is ranked based on <strong>utility</strong> and <strong>trajectory</strong> scores that
            are weight by engagement and recency.
          </p>
        </div>

        <!-- Pipeline stats -->
        <h3 class="text-sm font-bold text-foreground uppercase tracking-wide mt-8 mb-3">Pipeline Stats</h3>

        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <!-- Pipeline stats -->
          <div class="stat-card">
            <span class="stat-value text-muted-foreground">{pipeline.totalUrls.toLocaleString()}</span>
            <span class="stat-label">Total URLs</span>
          </div>
          <div class="stat-card">
            <span class="stat-value text-blue-500">{pipeline.scraped.toLocaleString()}</span>
            <span class="stat-label">Scraped</span>
          </div>
          <div class="stat-card">
            <span class="stat-value text-primary-500">{pipeline.analyzed.toLocaleString()}</span>
            <span class="stat-label">Prefiltered</span>
          </div>
          <div class="stat-card">
            <span class="stat-value text-fuchsia-500">{pipeline.relevant.toLocaleString()}</span>
            <span class="stat-label">Relevant</span>
          </div>

          <!-- Verdict stats -->
          <div class="stat-card">
            <span class="stat-value text-orange-500 opacity-80">{permanent.totalArticles.toLocaleString()}</span>
            <span class="stat-label">Analyzed</span>
          </div>
          <div class="stat-card">
            <span class="stat-value text-cyan-500 opacity-80">{stats.totalArticles.toLocaleString()}</span>
            <span class="stat-label">In window</span>
          </div>
          <div class="stat-card">
            <span class="stat-value text-green-500">{stats.positiveCount.toLocaleString()}</span>
            <span class="stat-label">Positive</span>
          </div>
          <div class="stat-card">
            <span class="stat-value text-red-500">{stats.negativeCount.toLocaleString()}</span>
            <span class="stat-label">Negative</span>
          </div>
          <div class="stat-card">
            <span class="stat-value text-yellow-500">{stats.neutralCount.toLocaleString()}</span>
            <span class="stat-label">Neutral</span>
          </div>
        </div>
      </div>
    </div>

    <!-- <h3 class="text-sm font-bold text-foreground uppercase tracking-wide mt-8 mb-3">Why</h3>
    <div class="text-sm text-foreground leading-relaxed space-y-3">
      <p>
        this exists because i kept seeing waves of AI-hate that just didn’t match my experience, and as i don’t jive
        with vibes or tribes, i built this website to find out if hn’s hivemind share similar sentiments. it’s also a
        small addition to my portfolio (i’m a web developer, not a statistician). thanks and if you find this
        interesting, please consider checking it out on <a
          href="https://github.com/ilyaizen/is-ai-good-yet"
          target="_blank"
          rel="noopener noreferrer"
          class="article-link">github</a
        >, dropping a star, or
        <a href="https://ko-fi.com/ilyaizen" target="_blank" rel="noopener noreferrer" class="article-link"
          >buying a coffee</a
        >… <i>a lot</i> of coffee went into this… either way, if this gets traction, i’ll share the pipeline—you never know.
      </p>
    </div> -->

    <!-- Divider -->
    <!-- <div class="border-t border-border/30 my-8"></div> -->

    <!-- Action Buttons -->
    <div class="flex flex-col sm:flex-row gap-4 mt-8">
      <AnimatedButton
        label="articles"
        onclick={scrollToArticles}
        bind:hovered={articlesButtonHovered}
        bind:focused={articlesButtonFocused} />

      <AnimatedButton
        label="about"
        icon={Info}
        onclick={() => scrollToBottom()}
        class="info-btn"
        bind:hovered={aboutButtonHovered}
        bind:focused={aboutButtonFocused} />
    </div>
  </section>

  <ArticleDetailsSheet bind:hnId={selectedArticleId} bind:open={sheetOpen} />
</div>

<style>
  .theme-group {
    opacity: 0;
    animation: fade-in-up 0.5s ease-out forwards;
  }

  .theme-group:nth-child(2) {
    animation-delay: 0.1s;
  }
  .theme-group:nth-child(3) {
    animation-delay: 0.2s;
  }
  .theme-group:nth-child(4) {
    animation-delay: 0.3s;
  }

  @keyframes fade-in-up {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .summary-section {
    opacity: 0;
    animation: fade-in-up 0.5s ease-out 0.05s forwards;
  }

  .methodology-section {
    opacity: 0;
    animation: fade-in-up 0.5s ease-out 0.15s forwards;
  }

  /* Methodology inline links */
  .article-link {
    color: var(--color-primary);
    font-weight: bold;
    text-decoration: none;
    transition: color 0.15s ease;
  }

  .article-link:hover {
    color: var(--color-primary);
    text-decoration: underline;
  }

  /* Article link rows under themes */
  .article-link-row {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-size: 0.8125rem;
    color: var(--color-muted-foreground);
    text-decoration: none;
    transition: color 0.15s ease;
    max-width: 100%;
    overflow: hidden;
  }

  .article-link-row:hover {
    color: var(--color-primary);
  }

  /* Stats cards */
  .stat-card {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
    padding: 0.75rem;
    border: 1px solid var(--color-border);
    border-radius: 0.2rem;
    background: var(--color-muted);
  }

  .stat-value {
    font-size: 1.25rem;
    font-weight: 700;
    line-height: 1;
  }

  .stat-label {
    font-size: 0.6875rem;
    color: var(--color-muted-foreground);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
</style>
