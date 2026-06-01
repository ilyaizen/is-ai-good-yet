<script lang="ts">
  import { onMount } from "svelte"
  import { page } from "$app/state"
  import { scrollToTop, handleAnchorClick } from "$lib/scroll"
  import { ChevronRight } from "@lucide/svelte"
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
  const words = ["Is", "AI", "Good", "Yet?"]

  const isAnimatedMode = $derived(mode === "animated")
  const isHomepage = $derived(page.url.pathname === "/")
  const isAdminRoute = $derived(page.url.pathname.startsWith("/admin"))

  const navLinks = $derived(
    isAdminRoute
      ? [
          { href: "/#home", label: "Home" },
          { href: "/#details", label: "Details" },
          { href: "/#articles-table", label: "Articles" },
          { href: "/lab/threejs-page-transition", label: "Lab" },
          { href: "/admin", label: "Admin" },
          { href: "/admin/pipeline-control", label: "Control" },
        ]
      : [
          { href: "#home", label: "Home" },
          { href: "#details", label: "Details" },
          { href: "#articles-table", label: "Articles" },
          { href: "/lab/threejs-page-transition", label: "Lab" },
        ]
  )

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault()
      if (isHomepage) scrollToTop()
      else window.location.assign("/")
    }
  }

  const TYPING_DELAY_MS = 50

  $effect(() => {
    if (!isAnimatedMode) return

    if (visible) {
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
      setTimeout(typeNextWord, 100)
    } else {
      logoWords = []
      currentWordIndex = 0
    }
  })

  onMount(() => {
    if (!isAnimatedMode) {
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
  class:site-header--hidden={isAnimatedMode && !visible}
>
  <div class="header-content-wrapper max-w-5xl mx-auto w-full">
    <div class="header-content w-full">
      {#if isHomepage}
        <button
          type="button"
          class="logo-container"
          onclick={() => scrollToTop()}
          onkeydown={handleKeyDown}
          aria-label="Scroll to top"
        >
          <ChevronRight size={24} strokeWidth={3.5} class="logo-icon" />
          <div class="logo-text-wrapper">
            <span class="logo-text font-mono font-bold -ml-2">
              {#each logoWords as word, i}
                <span class="word {word === 'Good' ? 'highlight' : ''}"
                  >{word === "Good" ? `\u201C${word}\u201D` : word}</span
                >
                <span class="space">{i < logoWords.length - 1 ? " " : ""}</span>
              {/each}
            </span>
            {#if !isAnimatedMode}
              <span class="cursor"></span>
            {/if}
          </div>
        </button>
      {:else}
        <a href="/" class="logo-container" aria-label="Go to homepage">
          <ChevronRight size={24} strokeWidth={3.5} class="logo-icon" />
          <div class="logo-text-wrapper">
            <span class="logo-text font-mono font-bold -ml-2">
              {#each logoWords as word, i}
                <span class="word {word === 'Good' ? 'highlight' : ''}"
                  >{word === "Good" ? `\u201C${word}\u201D` : word}</span
                >
                <span class="space">{i < logoWords.length - 1 ? " " : ""}</span>
              {/each}
            </span>
            {#if !isAnimatedMode}
              <span class="cursor"></span>
            {/if}
          </div>
        </a>
      {/if}

      <nav class="desktop-nav">
        <ul class="nav-list">
          {#each navLinks as link}
            <li><a href={link.href} class="nav-link" onclick={(e) => handleAnchorClick(e, link.href)}>{link.label}</a></li>
          {/each}
        </ul>
      </nav>

      <div class="header-actions">
        <ThemeToggle />
      </div>
    </div>
  </div>
</div>

<style>
  .site-header {
    border-bottom: 1px solid oklch(from var(--primary) l c h / 0.3);
  }

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
