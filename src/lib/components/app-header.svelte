<script lang="ts">
  import { onMount } from "svelte"
  import { scrollToTop } from "$lib/scroll"
  import { ChevronRight } from "lucide-svelte"
  import ThemeToggle from "$lib/components/theme-toggle.svelte"

  type HeaderMode = "default" | "animated"

  let {
    mode = "default" as HeaderMode,
    visible = true,
  }: {
    mode?: HeaderMode
    visible?: boolean
  } = $props()

  let logoWords = $state<string[]>([])
  let currentWordIndex = $state(0)
  const words = ["is", "AI", "good", "yet?"]

  // Animated mode: header slides in when visible becomes true
  const isAnimatedMode = $derived(mode === "animated")

  // Keyboard handler for accessibility
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault()
      scrollToTop()
    }
  }

  // Typing animation speed (faster for swift animation)
  const TYPING_DELAY_MS = 50

  // Replay typing animation when visibility changes in animated mode
  $effect(() => {
    if (!isAnimatedMode) return

    if (visible) {
      // Reset and start typing animation when becoming visible
      logoWords = []
      currentWordIndex = 0
      let index = 0

      const typeNextWord = () => {
        if (index < words.length) {
          logoWords = [...logoWords, words[index]]
          index++
          setTimeout(typeNextWord, TYPING_DELAY_MS)
        }
      }
      // Small initial delay to sync with slide-in animation
      setTimeout(typeNextWord, 100)
    } else {
      // Reset when hidden so animation replays next time
      logoWords = []
      currentWordIndex = 0
    }
  })

  onMount(() => {
    if (!isAnimatedMode) {
      // Default mode: type animation on mount
      const typeNextWord = () => {
        if (currentWordIndex < words.length) {
          logoWords = [...logoWords, words[currentWordIndex]]
          currentWordIndex++
          setTimeout(typeNextWord, 80)
        }
      }
      typeNextWord()
    }
  })
</script>

<div
  role="banner"
  class="site-header bg-card"
  class:site-header--animated={isAnimatedMode}
  class:site-header--visible={isAnimatedMode && visible}
  class:site-header--hidden={isAnimatedMode && !visible}>
  <div class="header-content-wrapper max-w-5xl mx-auto w-full">
    <div class="header-content w-full">
      <button
        type="button"
        class="logo-container"
        onclick={() => scrollToTop()}
        onkeydown={handleKeyDown}
        aria-label="Scroll to top">
        <ChevronRight size={24} strokeWidth={3.5} class="logo-icon" />
        <div class="logo-text-wrapper">
          <span class="logo-text font-mono font-bold -ml-2">
            {#each logoWords as word, i}
              <span class="word {word === 'good' ? 'highlight' : ''}"
                >{word === "good" ? `\u201C${word}\u201D` : word}</span>
              <span class="space">{i < logoWords.length - 1 ? " " : ""}</span>
            {/each}
          </span>
          {#if !isAnimatedMode}
            <span class="cursor"></span>
          {/if}
        </div>
      </button>

      <nav class="desktop-nav">
        <ul class="nav-list">
          <li><a href="#home" class="nav-link">home</a></li>
          <li><a href="#details" class="nav-link">details</a></li>
          <li><a href="#articles" class="nav-link">articles</a></li>
        </ul>
      </nav>

      <div class="header-actions">
        <ThemeToggle />
      </div>
    </div>
  </div>
</div>

<style>
  /*
   * Animated mode styles:
   * - Header starts translated up (hidden above viewport)
   * - Uses position:fixed so it doesn't take up layout space initially
   * - Transitions to visible with slide-down animation
   */
  .site-header--animated {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 50;
    transform: translateY(-100%);
    transition: transform 400ms var(--ease-swift);
  }

  .site-header--animated.site-header--visible {
    transform: translateY(0);
  }

  .site-header--animated.site-header--hidden {
    transform: translateY(-100%);
  }

  /* Logo container button styles */
  .logo-container {
    cursor: pointer;
    transition: opacity 300ms cubic-bezier(0, 0.7, 0.1, 1);
  }

  .logo-container:hover {
    opacity: 0.8;
  }

  .logo-container:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }
</style>
