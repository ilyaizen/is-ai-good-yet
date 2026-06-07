<script lang="ts">
  import type { WeeklySnapshot, VerdictScore } from "$lib/server/db"
  import { EASE_SWIFT } from "$lib/constants"
  import { scrollToElement, scrollToBottom } from "$lib/scroll"
  import HistoryChart from "./history-chart.svelte"
  import NumberFlow from "@number-flow/svelte"
  import { onMount } from "svelte"
  import { ChevronRight } from "@lucide/svelte"
  import { RotateCcw } from "@lucide/svelte"
  import { ChevronDown } from "@lucide/svelte"
  import { useTokenStream } from "$lib/composables/use-token-stream.svelte"
  import AnimatedButton from "$lib/components/ui/animated-button.svelte"
  import { Info } from "@lucide/svelte"

  type Verdict = "Yes" | "No" | "Not yet" | "YES" | "NO" | "NOT_YET"

  let {
    verdict,
    score,
    weeklySnapshots,
    verdictScore,
    onReplay,
  }: {
    verdict: Verdict
    score: number
    weeklySnapshots?: WeeklySnapshot[]
    verdictScore?: VerdictScore
    onReplay?: () => void
  } = $props()

  let entering = $state(true)
  let hoveredSnapshot = $state<WeeklySnapshot | null>(null)

  // Typing animation state for "Articles:" label
  let typedLabel = $state("")
  let labelTypingComplete = $state(false)
  // Stutter animation for content blocks
  let animationStep = $state(0)
  const TOTAL_BLOCKS = 5

  // Viewport observer: destroy & re-animate when 300px out of view
  let sectionRef = $state<HTMLElement | null>(null)
  let isInViewport = $state(false)
  let hasAnimated = $state(false)

  // Verdict slide-in: starts offset, transitions to 0 after mount
  let verdictSlideIn = $state(false)

  // History section collapse state
  let historyExpanded = $state(false)
  let historyButtonFocused = $state(false)
  let historyButtonHovered = $state(false)

  // More Info button state
  let moreInfoButtonFocused = $state(false)
  let moreInfoButtonHovered = $state(false)
  let moreInfoButtonRef = $state<HTMLButtonElement | null>(null)

  // About button state
  let aboutButtonFocused = $state(false)
  let aboutButtonHovered = $state(false)

  // Reference to history button for simulated tab focus
  let historyButtonRef = $state<HTMLButtonElement | null>(null)

  // Replay button state
  let replayButtonFocused = $state(false)
  let replayButtonHovered = $state(false)
  let replayButtonRef = $state<HTMLButtonElement | null>(null)

  const LABEL_TEXT = "Articles:"
  const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

  // Description text for token streaming
  let descriptionLines = $state<string[]>([])
  let descriptionStream = $state<ReturnType<typeof useTokenStream> | null>(null)

  $effect(() => {
    if (verdictScore && !descriptionStream) {
      descriptionLines = [sentimentText, "based on the accumulated points of "]
      descriptionStream = useTokenStream(descriptionLines)
    }
  })

  function handleChartHover(snapshot: WeeklySnapshot | null) {
    hoveredSnapshot = snapshot
  }

  // Typing animation for the label
  function typeLabel() {
    let charIndex = 0
    const typeNextChar = () => {
      if (charIndex < LABEL_TEXT.length) {
        charIndex += 2
        typedLabel = LABEL_TEXT.slice(0, charIndex)
        setTimeout(typeNextChar, 15)
      } else {
        labelTypingComplete = true
        // Start block animation after typing label
        setTimeout(startBlockAnimation, 50)
      }
    }
    // Start typing after a slight delay
    setTimeout(typeNextChar, 50)
  }

  // Block-by-block stutter animation
  function startBlockAnimation() {
    if (animationStep < TOTAL_BLOCKS) {
      animationStep++

      // Trigger verdict slide-in on first block
      if (animationStep === 1) {
        requestAnimationFrame(() => {
          verdictSlideIn = true
        })
      }

      // At step 3, start description streaming and wait for it to complete
      if (animationStep === 3 && descriptionStream) {
        descriptionStream.stream(() => {
          // Continue with remaining animation steps after streaming completes
          continueBlockAnimation()
        })
        return // Don't continue immediately - wait for streaming callback
      }

      // Random delay for stutter effect (20-100ms)
      const delay = Math.floor(Math.random() * 80) + 20
      setTimeout(startBlockAnimation, delay)
    } else {
      triggerMoreInfoButtonFocus()
    }
  }

  // Continue animation after description streaming completes
  function continueBlockAnimation() {
    if (animationStep < TOTAL_BLOCKS) {
      animationStep++
      // Random delay for stutter effect (20-100ms)
      const delay = Math.floor(Math.random() * 80) + 20
      setTimeout(continueBlockAnimation, delay)
    } else {
      triggerMoreInfoButtonFocus()
    }
  }

  // Simulate tab key focus to more info button
  function triggerMoreInfoButtonFocus() {
    setTimeout(() => {
      // Only focus if not already interacting with mouse
      if (!moreInfoButtonHovered) {
        moreInfoButtonFocused = true
      }
    }, 300)
  }

  function scrollToArticles() {
    const el = document.getElementById("articles")
    if (el) {
      scrollToElement(el)
    }
  }

  // Derived state
  const isHoveringHistory = $derived(hoveredSnapshot !== null)

  // Track if user is interacting with ANY button except the Articles button's simulated focus
  const anyOtherButtonInteracted = $derived(
    historyButtonHovered ||
      historyButtonFocused ||
      aboutButtonHovered ||
      aboutButtonFocused ||
      replayButtonHovered ||
      replayButtonFocused ||
      isHoveringHistory
  )

  // Clear simulated focus when user interacts with other elements
  $effect(() => {
    if (anyOtherButtonInteracted && moreInfoButtonFocused) {
      moreInfoButtonFocused = false
    }
  })

  function handlePanelEnter() {
    if (moreInfoButtonFocused) {
      moreInfoButtonFocused = false
    }
  }

  const effectiveVerdict = $derived(hoveredSnapshot?.verdict ?? verdict)
  const effectiveScore = $derived(hoveredSnapshot?.verdictScore ?? score)

  // Article counts - derive from hovered snapshot or verdictScore prop
  const effectivePositive = $derived(hoveredSnapshot?.positiveCount ?? verdictScore?.positiveCount ?? 0)
  const effectiveNegative = $derived(hoveredSnapshot?.negativeCount ?? verdictScore?.negativeCount ?? 0)
  const effectiveNeutral = $derived(hoveredSnapshot?.neutralCount ?? verdictScore?.neutralCount ?? 0)
  const effectiveTotalArticles = $derived(effectivePositive + effectiveNeutral + effectiveNegative)
  const displayText = $derived(
    effectiveVerdict === "NOT_YET"
      ? "Not yet"
      : effectiveVerdict === "YES"
        ? "Yes"
        : effectiveVerdict === "NO"
          ? "No"
          : effectiveVerdict
  )

  // Date parts for NumberFlow animation
  const displayDate = $derived(() => {
    const date = hoveredSnapshot ? new Date(hoveredSnapshot.weekStart) : new Date()
    return {
      month: MONTH_NAMES[date.getMonth()],
      day: date.getDate(),
      year: date.getFullYear(),
    }
  })

  // Star rating
  const starRating = $derived((effectiveScore / 100) * 5)
  const stars = $derived(() => {
    const result = []
    const fullStars = Math.floor(starRating)
    const partialFill = (starRating - fullStars) * 100
    for (let i = 1; i <= 5; i++) {
      if (i <= fullStars) {
        result.push({ fill: 100 })
      } else if (i === fullStars + 1 && partialFill > 0) {
        result.push({ fill: partialFill })
      } else {
        result.push({ fill: 0 })
      }
    }
    return result
  })

  // Sentiment color based on verdict
  const sentimentColor = $derived(
    effectiveVerdict === "YES" || effectiveVerdict === "Yes"
      ? "var(--color-primary)"
      : effectiveVerdict === "NO" || effectiveVerdict === "No"
        ? "var(--color-destructive)"
        : "var(--color-warning)"
  )

  // Contribution scores - derive from hovered snapshot or verdictScore prop
  const positiveContribution = $derived(
    hoveredSnapshot?.positiveContribution ?? verdictScore?.positiveContribution ?? 0
  )
  const negativeContribution = $derived(
    hoveredSnapshot?.negativeContribution ?? verdictScore?.negativeContribution ?? 0
  )
  // Neutral contribution: use hovered snapshot value or verdictScore value
  const neutralContribution = $derived(hoveredSnapshot?.neutralContribution ?? verdictScore?.neutralContribution ?? 0)

  // Sentiment description text
  const sentimentText = $derived(
    effectiveVerdict === "YES" || effectiveVerdict === "Yes"
      ? 'Most developers think positively about "vibe-coding" and AI-assisted workflows, '
      : effectiveVerdict === "NO" || effectiveVerdict === "No"
        ? 'Most developers are skeptical about "vibe-coding" and AI-assisted workflows, '
        : 'The developer community is undecided on "vibe-coding" and AI-assisted workflows, '
  )

  // Disarm NumberFlow animations during history hover for performance
  const numberFlowAnimated = $derived(!isHoveringHistory)
  const numberFlowTiming = {
    duration: 300,
    easing: EASE_SWIFT,
  }

  const shouldScaleUp = $derived(moreInfoButtonHovered || moreInfoButtonFocused)

  // Toggle history section expanded state
  function toggleHistory() {
    historyExpanded = !historyExpanded
  }

  // Exiting animation state
  let exiting = $state(false)

  function handleReplayClick() {
    exiting = true
    // Match the duration-300 of the container transition
    setTimeout(() => {
      onReplay?.()
    }, 300)
  }

  // Reset all animation state to initial
  function resetAnimation() {
    entering = true
    exiting = false
    typedLabel = ""
    labelTypingComplete = false
    animationStep = 0
    verdictSlideIn = false
    historyExpanded = false
    moreInfoButtonFocused = false
    moreInfoButtonHovered = false
    // Reset description stream so it re-creates on next play
    descriptionStream?.reset()
    descriptionStream = null
    hasAnimated = false
  }

  // Start the full animation sequence
  function playAnimation() {
    if (hasAnimated) return
    hasAnimated = true
    setTimeout(() => {
      entering = false
      typeLabel()
    }, 50)
  }

  // React to viewport visibility changes
  $effect(() => {
    if (isInViewport && !hasAnimated) {
      playAnimation()
    }
  })

  onMount(() => {
    if (!sectionRef) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          isInViewport = true
        } else {
          // Element is at least 300px outside viewport — destroy and reset
          isInViewport = false
          resetAnimation()
        }
      },
      {
        // Negative margin means the element must be 300px inside the viewport
        // to be "intersecting". Once it's 300px outside, it's "not intersecting".
        rootMargin: "-50px 0px -50px 0px",
      }
    )

    observer.observe(sectionRef)

    return () => {
      observer.disconnect()
    }
  })
</script>

<div class="">
  <section
    bind:this={sectionRef}
    class="terminal-panel p-4 sm:p-6 md:p-8 min-h-80 sm:min-h-100 mx-auto overflow-hidden max-w-2xl transform transition-all duration-300 ease-swift"
    class:scale-75={entering}
    class:opacity-0={entering || exiting}
    class:scale-125={exiting}
    class:scale-100={!entering && !exiting && !shouldScaleUp}
    class:opacity-100={!entering && !exiting}
    class:scale-105={shouldScaleUp && !exiting}
    class:pointer-events-none={exiting}
    onmouseenter={handlePanelEnter}
    aria-label="Articles"
  >
    <!-- Header Title (Left-Top) -->
    <div class="flex items-center gap-1 absolute z-10 transition-opacity duration-300 -ml-2">
      <ChevronRight color="var(--color-accent)" strokeWidth={3} />
      <span class="font-mono font-semibold">
        {typedLabel}
        {#if !labelTypingComplete}
          <span class="cursor"></span>
        {/if}
      </span>
    </div>
    <!-- Date Badge: Only visible when hovering the history chart -->
    <div
      class="absolute top-4 right-4 transition-opacity duration-200 ease-swift"
      class:opacity-0={!isHoveringHistory}
      class:opacity-100={isHoveringHistory}
      class:pointer-events-none={!isHoveringHistory}
    >
      <div class="date-badge font-mono text-xs px-3 py-1 rounded flex gap-1 items-center border">
        {displayDate().month}
        <NumberFlow value={displayDate().day} transformTiming={numberFlowTiming} spinTiming={numberFlowTiming} />
        <NumberFlow
          value={displayDate().year}
          format={{ useGrouping: false }}
          transformTiming={numberFlowTiming}
          spinTiming={numberFlowTiming}
        />
      </div>
    </div>

    <!-- Main Content -->
    <div class="pt-10 sm:pt-10 transition-opacity duration-300 ease-swift" class:opacity-65={isHoveringHistory}>
      <!-- Verdict Answer -->
      {#if animationStep >= 1}
        <div
          class="relative min-h-[clamp(2rem,10vw,5rem)] transition-all ease-swift"
          style="transform: translateY({verdictSlideIn ? '0px' : '20px'}); opacity: {verdictSlideIn
            ? 1
            : 0}; transition-duration: 200ms;"
        >
          {#key effectiveVerdict}
            <div class="font-mono text-[clamp(1.75rem,10vw,4.5rem)] font-bold flex items-center justify-center">
              <span
                class="transition-colors duration-200"
                class:text-accent={effectiveVerdict === "YES" || effectiveVerdict === "Yes"}
                class:text-destructive={effectiveVerdict === "NO" || effectiveVerdict === "No"}
                style:color={sentimentColor}
                style:text-shadow="0 0 12px color-mix(in srgb, {sentimentColor}, transparent 40%), 0 0 24px color-mix(in
                srgb, {sentimentColor}, transparent 60%)"
              >
                {displayText}</span
              ><span class="text-muted-foreground/60 -ml-1">.</span>
            </div>
          {/key}
        </div>
      {/if}

      <!-- Unified Description: Sentiment + Article Count in one line -->
      {#if verdictScore}
        {#if animationStep >= 3}
          <div class="mb-5 text-center sm:mb-4">
            <!-- Combined sentiment + context line with brighter contrast -->
            <p class="font-mono text-sm text-foreground dark:text-foreground">
              {#if isHoveringHistory}
                <!-- When hovering history, show dynamic text that updates with the hovered snapshot -->
                {sentimentText}
                based on the accumulated points of
                <NumberFlow
                  value={effectiveTotalArticles}
                  animated={numberFlowAnimated}
                  transformTiming={numberFlowTiming}
                  spinTiming={numberFlowTiming}
                /> recent articles:
              {:else if descriptionStream}
                {descriptionStream.getVisibleText(
                  0
                )}{#if descriptionStream.isLineComplete(0)}{descriptionStream.getVisibleText(
                    1
                  )}{#if descriptionStream.isLineComplete(1)}<NumberFlow
                      value={effectiveTotalArticles}
                      animated={numberFlowAnimated}
                      transformTiming={numberFlowTiming}
                      spinTiming={numberFlowTiming}
                    /> recent articles:{/if}{/if}
              {:else}
                {sentimentText}
                based on the accumulated points of
                <NumberFlow
                  value={effectiveTotalArticles}
                  animated={numberFlowAnimated}
                  transformTiming={numberFlowTiming}
                  spinTiming={numberFlowTiming}
                /> recent articles:
              {/if}
            </p>
          </div>
        {/if}
        <!-- Contribution Points: Concise inline tags -->
        {#if animationStep >= 4}
          <div
            class="flex flex-wrap items-baseline gap-x-2 sm:gap-x-3 gap-y-2 transition-opacity duration-200 justify-center"
          >
            <span class="text-muted-foreground text-xs font-mono shrink-0">Totals:</span>

            <div class="flex flex-wrap gap-2">
              <!-- Positive -->
              <div
                class="flex items-baseline gap-1.5 border border-primary/30 px-2 py-0.5 rounded bg-primary/10 font-mono text-xs"
              >
                <span class="text-primary font-bold">
                  <NumberFlow
                    value={positiveContribution}
                    animated={numberFlowAnimated}
                    format={{ notation: "compact", signDisplay: "always", maximumFractionDigits: 1 }}
                    transformTiming={numberFlowTiming}
                    spinTiming={numberFlowTiming}
                  />
                </span>
                <span class="font-semibold text-primary/60 opacity-80"
                  >(<NumberFlow
                    value={effectivePositive}
                    animated={numberFlowAnimated}
                    transformTiming={numberFlowTiming}
                    spinTiming={numberFlowTiming}
                  /> GOOD)</span
                >
              </div>

              <!-- Neutral -->
              <div
                class="flex items-baseline gap-1.5 border border-warning/30 px-2 py-0.5 rounded bg-warning/10 font-mono text-xs"
              >
                <span class="text-warning font-bold">
                  <NumberFlow
                    value={neutralContribution}
                    animated={numberFlowAnimated}
                    format={{ notation: "compact", signDisplay: "always", maximumFractionDigits: 1 }}
                    transformTiming={numberFlowTiming}
                    spinTiming={numberFlowTiming}
                  />
                </span>
                <span class="font-semibold text-warning/60 opacity-80"
                  >(<NumberFlow
                    value={effectiveNeutral}
                    animated={numberFlowAnimated}
                    transformTiming={numberFlowTiming}
                    spinTiming={numberFlowTiming}
                  /> NEUTRAL)</span
                >
              </div>

              <!-- Negative -->
              <div
                class="flex items-baseline gap-1.5 border border-destructive/30 px-2 py-0.5 rounded bg-destructive/10 font-mono text-xs"
              >
                <span class="text-destructive font-bold">
                  <NumberFlow
                    value={negativeContribution}
                    animated={numberFlowAnimated}
                    format={{ notation: "compact", signDisplay: "always", maximumFractionDigits: 1 }}
                    transformTiming={numberFlowTiming}
                    spinTiming={numberFlowTiming}
                  />
                </span>
                <span class="font-semibold text-destructive/60 opacity-80"
                  >(<NumberFlow
                    value={effectiveNegative}
                    animated={numberFlowAnimated}
                    transformTiming={numberFlowTiming}
                    spinTiming={numberFlowTiming}
                  /> BAD)</span
                >
              </div>
            </div>
          </div>
        {/if}

        <!-- Star Rating -->
        {#if animationStep >= 5}
          <div class="mt-2 mb-4 sm:mb-6 flex flex-wrap items-baseline gap-x-2 gap-y-2 justify-center">
            <span class="text-muted-foreground text-xs font-mono shrink-0">Rating:</span>
            <div class="flex flex-wrap items-baseline gap-2">
              <span class="font-mono text-sm font-semibold" style="color: {sentimentColor}"
                ><NumberFlow
                  value={starRating}
                  animated={numberFlowAnimated}
                  format={{ minimumFractionDigits: 0, maximumFractionDigits: 1 }}
                  transformTiming={numberFlowTiming}
                  spinTiming={numberFlowTiming}
                />-star developer satisfaction</span
              >

              <div
                class="flex gap-1 items-center shrink-0 translate-y-0.5"
                style="--sentiment-color: {sentimentColor};"
              >
                {#each stars() as star}
                  <div class="relative w-4 h-4" style="--star-fill: {star.fill}%;">
                    <!-- Empty star (gray base) -->
                    <svg viewBox="0 0 16 16" class="absolute w-full h-full fill-muted-foreground/40">
                      <path d="M8 .2l4.9 15.2L0 6h16L3.1 15.4z" />
                    </svg>
                    <!-- Filled star (sentiment color, clipped for partial fill) -->
                    <svg
                      viewBox="0 0 16 16"
                      class="absolute w-full h-full fill-(--sentiment-color) transition-[clip-path,fill] duration-200 ease-swift"
                      style="clip-path: inset(0 calc(100% - var(--star-fill)) 0 0)"
                    >
                      <path d="M8 .2l4.9 15.2L0 6h16L3.1 15.4z" />
                    </svg>
                  </div>
                {/each}
              </div>
            </div>
          </div>
        {/if}
      {/if}
    </div>

    <!-- History Chart Section (Collapsible) -->
    {#if weeklySnapshots && weeklySnapshots.length > 0}
      {#if animationStep >= 5}
        <div class="flex flex-col items-start w-full">
          <!-- History Chart -->
          <div
            class="grid transition-all duration-500 ease-swift overflow-hidden w-full"
            style="grid-template-rows: {historyExpanded ? '1fr' : '0fr'}; opacity: {historyExpanded ? 1 : 0}"
          >
            <div class="min-h-0">
              <!-- History Labels -->
              <div class="text-foreground font-mono text-xs font-semibold">History:</div>
              <div class="pb-6">
                <HistoryChart data={weeklySnapshots} compact={true} onHover={handleChartHover} />
              </div>
            </div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex gap-2 sm:gap-3 flex-col sm:flex-row w-full">
          <AnimatedButton
            label="Articles"
            onclick={scrollToArticles}
            class="flex-1 sm:flex-initial"
            bind:hovered={moreInfoButtonHovered}
            bind:focused={moreInfoButtonFocused}
            bind:ref={moreInfoButtonRef}
          />

          <AnimatedButton
            label="History"
            icon={ChevronDown}
            iconClass={historyExpanded ? "rotate-180" : ""}
            onclick={toggleHistory}
            class="flex-1 sm:flex-initial"
            bind:hovered={historyButtonHovered}
            bind:focused={historyButtonFocused}
            bind:ref={historyButtonRef}
          />

          <AnimatedButton
            label="About"
            onclick={() => scrollToBottom()}
            icon={Info}
            class="flex-1 sm:flex-initial"
            bind:hovered={aboutButtonHovered}
            bind:focused={aboutButtonFocused}
          />

          <AnimatedButton
            label="Replay"
            icon={RotateCcw}
            onclick={handleReplayClick}
            class="flex-1 sm:flex-initial sm:ml-auto"
            bind:hovered={replayButtonHovered}
            bind:focused={replayButtonFocused}
            bind:ref={replayButtonRef}
          />
        </div>
      {/if}
    {/if}
  </section>
</div>
