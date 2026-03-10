<script lang="ts">
  import { ChevronRight } from "@lucide/svelte"
  import { onMount } from "svelte"
  import { useTokenStream } from "$lib/composables/use-token-stream.svelte"
  import AnimatedButton from "$lib/components/ui/animated-button.svelte"
  import { Info } from "@lucide/svelte"

  let {
    onReveal,
    articleCount,
    lastUpdateTimestamp,
    resetTrigger = 0,
  }: {
    onReveal: () => void
    articleCount: number
    lastUpdateTimestamp: number | null
    resetTrigger?: number
  } = $props()

  let visible = $state(true)
  let entering = $state(false)
  let fading = $state(false)
  let typedText = $state("")
  let currentWordIndex = $state(0)
  let charIndexInWord = $state(0)
  let typingComplete = $state(false)
  let goodComplete = $state(false)
  let buttonFocused = $state(false)
  let revealHovered = $state(false)
  let allComplete = $state(false)
  let aboutHovered = $state(false)
  let aboutFocused = $state(false)

  const WORDS = ["Is ", "AI ", "good", " yet?"]

  function numberWithCommas(x: number | string) {
    return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")
  }

  function roundToNearest(n: number, roundTo: number = 100): number {
    return Math.round(n / roundTo) * roundTo
  }

  const roundedCount = $derived(numberWithCommas(roundToNearest(articleCount)))

  // Lines to display - each line appears all at once
  const LINES = $derived([
    `This site analyzes developer sentiment toward AI coding.`,
    `It examines ~${roundedCount} AI-related articles from the past 3 years to see whether HN is leaning toward enthusiasm or skepticism, and which side is louder.`,
  ])

  let tokenStream = $state<ReturnType<typeof useTokenStream> | null>(null)

  function formatDate(timestamp: number): { formatted: string; relative: string } {
    const date = new Date(timestamp * 1000)
    const now = new Date()

    const formatted = date.toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
    })

    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)
    const diffWeeks = Math.floor(diffMs / 604800000)
    const diffMonths = Math.floor(diffMs / 2629800000)
    const diffYears = Math.floor(diffMs / 31557600000)

    let relative: string
    if (diffMins < 1) relative = "just now"
    else if (diffMins < 60) relative = `${diffMins} minutes ago`
    else if (diffHours < 24) relative = `${diffHours} hours ago`
    else if (diffDays < 7) relative = `${diffDays} days ago`
    else if (diffWeeks < 4) relative = `${diffWeeks} weeks ago`
    else if (diffMonths < 12) relative = `${diffMonths} months ago`
    else relative = `${diffYears} years ago`

    return { formatted, relative }
  }

  const formattedUpdate = $derived(lastUpdateTimestamp ? formatDate(lastUpdateTimestamp) : null)

  const updateLine = $derived(
    formattedUpdate ? `Updated: ${formattedUpdate.formatted} (${formattedUpdate.relative})` : null
  )

  function typeNextChar() {
    if (currentWordIndex >= WORDS.length) {
      typingComplete = true
      startLineAnimation()
      return
    }

    const currentWord = WORDS[currentWordIndex]

    if (charIndexInWord < currentWord.length) {
      typedText = typedText + currentWord[charIndexInWord]
      charIndexInWord++

      // Slower typing for "Good"
      const delay = currentWordIndex === 2 ? 220 : 45
      setTimeout(typeNextChar, delay)
    } else {
      // Word complete - mark "Good" as complete for glow effect
      if (currentWordIndex === 2) {
        goodComplete = true
      }
      currentWordIndex++
      charIndexInWord = 0
      setTimeout(typeNextChar, 150)
    }
  }

  function startTyping() {
    setTimeout(typeNextChar, 300)
  }

  function handleReveal() {
    // Call onReveal immediately so parent can pre-render content behind the veil
    onReveal()
    // Start fading the veil (content is now behind it, hidden by visibility:hidden)
    fading = true
    setTimeout(() => {
      visible = false
    }, 50)
  }

  // Reference to caret anchor for initial focus (caret browsing)
  let caretAnchor: HTMLSpanElement | undefined = $state()

  onMount(() => {
    tokenStream = useTokenStream(LINES)
    // Focus caret anchor so caret browsing starts at end of title
    if (caretAnchor) {
      caretAnchor.focus({ preventScroll: true })
    }
  })

  startTyping()

  // Simulate tab key press to focus button shortly after animation completes
  function triggerTabFocus() {
    setTimeout(() => {
      buttonFocused = true
    }, 50)
  }

  // Line-by-line animation - each line appears all at once with a delay between
  function startLineAnimation() {
    tokenStream?.stream(() => {
      allComplete = true
      triggerTabFocus()
    })
  }

  // Build the display text with special rendering for "Good"
  function getRenderedSegments(text: string): { before: string; good: string; after: string } {
    const goodStart = "Is AI ".length
    const goodEnd = goodStart + "good".length

    if (!goodComplete) {
      return { before: text, good: "", after: "" }
    }

    // Only apply special rendering after "Good" is fully typed
    const currentLength = text.length

    if (currentLength <= goodStart) {
      return { before: text, good: "", after: "" }
    }

    if (currentLength <= goodEnd) {
      const beforeText = text.slice(0, goodStart)
      const goodText = text.slice(goodStart)
      return { before: beforeText, good: goodText, after: "" }
    }

    const beforeText = text.slice(0, goodStart)
    const goodText = "good"
    const afterText = text.slice(goodEnd)
    return { before: beforeText, good: goodText, after: afterText }
  }

  let segments = $derived(getRenderedSegments(typedText))

  const shouldScaleUp = $derived(revealHovered || buttonFocused)

  function scrollToBottom() {
    const start = window.scrollY
    const duration = 1500 // 1.5s for a swift but noticeable effect
    let startTime = 0

    function animate(currentTime: number) {
      if (!startTime) startTime = currentTime
      const timeElapsed = currentTime - startTime

      // Calculate target dynamically to handle layout changes
      // Use Math.max of body and docElement to get true scrollHeight across browsers
      const docHeight = Math.max(
        document.body.scrollHeight,
        document.documentElement.scrollHeight,
        document.body.offsetHeight,
        document.documentElement.offsetHeight,
        document.body.clientHeight,
        document.documentElement.clientHeight
      )
      const target = docHeight - window.innerHeight
      const change = target - start

      if (timeElapsed < duration) {
        const progress = timeElapsed / duration
        // Approximation of EASE_SWIFT cubic-bezier(0, 0.7, 0.1, 1)
        const ease = 1 - Math.pow(1 - progress, 5)
        window.scrollTo(0, start + change * ease)
        requestAnimationFrame(animate)
      } else {
        window.scrollTo(0, start + change)
      }
    }
    requestAnimationFrame(animate)
  }

  function handleAbout() {
    handleReveal()
    // Start scrolling immediately
    scrollToBottom()
  }

  let previousResetTrigger = $state(0)

  $effect(() => {
    if (resetTrigger > previousResetTrigger) {
      typedText = ""
      currentWordIndex = 0
      charIndexInWord = 0
      typingComplete = false
      goodComplete = false
      buttonFocused = false
      revealHovered = false
      allComplete = false
      fading = false
      visible = true
      entering = true
      tokenStream = useTokenStream(LINES)
      setTimeout(() => {
        startTyping()
      }, 200)
      setTimeout(() => {
        entering = false
      }, 50)
      previousResetTrigger = resetTrigger
    }
  })
</script>

{#if visible}
  <div
    class="fixed inset-0 z-50 flex items-center max-w-2xl mx-auto transition-all duration-300 ease-swift"
    class:opacity-0={fading || entering}
    class:scale-125={fading}
    class:scale-110={entering}
    class:pointer-events-none={fading}>
    <div class="w-full px-4 sm:px-6 md:px-8">
      <div class="terminal-panel flex min-h-72 sm:min-h-80 flex-col p-4 sm:p-6 md:p-8" class:scale-up={shouldScaleUp}>
        <div class="flex items-center gap-1 mb-3 sm:mb-4">
          <ChevronRight color="var(--color-accent)" strokeWidth={3} />
          <span class="font-mono text-lg font-semibold -ml-1"
            >{segments.before}{#if segments.good}<span class="glow-text">“{segments.good}”</span
              >{/if}{segments.after}{#if !typingComplete}
              <span class="cursor"></span>{/if}<span
              bind:this={caretAnchor}
              class="absolute w-0 h-0 overflow-hidden outline-none"
              tabindex="-1">&#8203;</span
            ></span>
        </div>

        <!-- Content -->
        <div class="font-mono px-1 sm:px-2 pt-2">
          {#if typingComplete}
            {#each LINES as line, i}
              {#if tokenStream && tokenStream.getVisibleText(i) !== ""}
                <p class="text-xs sm:text-sm mb-3 sm:mb-4 leading-relaxed text-muted-foreground">
                  {tokenStream.getVisibleText(i)}
                </p>
              {/if}
            {/each}
            {#if updateLine && allComplete}
              <p class="text-xs sm:text-sm mb-3 sm:mb-4 leading-relaxed text-muted-foreground/70">
                {updateLine}
              </p>
            {/if}
          {/if}
        </div>

        <!-- Buttons -->
        {#if allComplete}
          <div class="flex gap-2 sm:gap-3 flex-col sm:flex-row w-full sm:w-auto px-1 sm:px-2 pt-4">
            <AnimatedButton
              label="Answer"
              onclick={handleReveal}
              class="flex-1 sm:flex-initial"
              bind:hovered={revealHovered}
              bind:focused={buttonFocused} />

            <AnimatedButton
              label="About"
              onclick={handleAbout}
              icon={Info}
              class="flex-1 sm:flex-initial"
              bind:hovered={aboutHovered}
              bind:focused={aboutFocused} />
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .ease-swift {
    transition-timing-function: cubic-bezier(0, 0.7, 0.1, 1);
  }
</style>
