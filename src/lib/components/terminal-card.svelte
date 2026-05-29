<script lang="ts">
  import { onMount, type Snippet } from "svelte"

  interface Props {
    title?: string
    typingText?: string
    typingSpeed?: number
    class?: string
    children?: Snippet
  }

  let {
    title = "analysis.py — fish",
    typingText = "> Initializing sentiment analysis...\n> Loading HN_2025_Dataset.csv... [OK]\n> Filtering for 'dev' keywords... [OK]\n> Analyzing 10,423 comments...\n> \n> RESULT: Sentiment is shifting.\n> Developers see utility but fear dependency.\n> \n> Status: ANALYSIS COMPLETE.",
    typingSpeed = 30,
    class: className = "",
    children,
  }: Props = $props()

  let displayedText = $state("")
  let typeIndex = $state(0)

  onMount(() => {
    const timeout = setTimeout(() => {
      const interval = setInterval(() => {
        if (typeIndex < typingText.length) {
          displayedText += typingText[typeIndex]
          typeIndex++
        } else {
          clearInterval(interval)
        }
      }, typingSpeed)

      return () => clearInterval(interval)
    }, 800)

    return () => clearTimeout(timeout)
  })
</script>

<div class="terminal-card {className}" role="region" aria-label="Terminal animation showing analysis status">
  <div class="terminal-header">
    <div class="dot red"></div>
    <div class="dot yellow"></div>
    <div class="dot green"></div>
    <span class="terminal-title">{title}</span>
  </div>
  <div class="terminal-body">
    {#if children}
      {@render children()}
    {:else}
      <span>{@html displayedText.replace(/\n/g, "<br/>")}</span><span class="cursor"></span>
    {/if}
  </div>
</div>

<style>
  .terminal-card {
    background: oklch(0.13 0.008 250 / 0.65);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    overflow: hidden;
    box-shadow: 0 20px 50px -10px rgba(0, 0, 0, 0.5);
    font-family: var(--font-mono);
    position: relative;
  }

  :not(.dark) .terminal-card {
    background: oklch(1 0 0 / 0.6);
  }

  .terminal-header {
    background: rgba(255, 255, 255, 0.03);
    padding: 0.6rem 0.8rem;
    display: flex;
    align-items: center;
    border-bottom: 1px solid var(--color-border);
    gap: 0.5rem;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .dot.red {
    background: #ef4444;
  }

  .dot.yellow {
    background: #f59e0b;
  }

  .dot.green {
    background: var(--color-primary);
  }

  .terminal-title {
    margin-left: auto;
    margin-right: auto;
    color: var(--color-text-muted);
    font-size: 0.75rem;
  }

  .terminal-body {
    padding: 1rem;
    color: var(--color-text-primary);
    min-height: 180px;
    position: relative;
    font-size: 0.8rem;
  }

  .terminal-header {
    background: rgba(255, 255, 255, 0.03);
    padding: 0.75rem 1rem;
    display: flex;
    align-items: center;
    border-bottom: 1px solid var(--color-border);
    gap: 0.5rem;
  }

  .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }

  .dot.red {
    background: #ef4444;
  }
  .dot.yellow {
    background: #f59e0b;
  }
  .dot.green {
    background: var(--color-primary);
  }

  .terminal-title {
    margin-left: auto;
    margin-right: auto;
    color: var(--color-text-muted);
    font-size: 0.8rem;
  }

  .terminal-body {
    padding: 1.5rem;
    color: var(--color-text-primary);
    min-height: 250px;
    position: relative;
  }

  .cursor {
    display: inline-block;
    width: 10px;
    height: 1.2em;
    background-color: var(--color-primary);
    vertical-align: text-bottom;
    animation: blink 1s step-end infinite;
  }

  @keyframes blink {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0;
    }
  }
</style>
