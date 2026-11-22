<script lang="ts">
  import { onMount } from "svelte"
  import { cueKeystroke, cueReveal, unlockSound } from "$lib/audio/v12-sound"
  import { v12Effects } from "$lib/state/v12-effects.svelte"

  const QUESTION = "is ai \u201cgood\u201d yet?"
  const GOOD_START = 6
  const GOOD_END = 11

  let {
    onReveal,
    onComplete,
  }: {
    onReveal: () => void
    onComplete: () => void
  } = $props()

  let phase = $state<"typing" | "ready" | "lifting" | "done">("typing")
  let typed = $state("")
  let skipButton = $state<HTMLButtonElement>()
  let revealButton = $state<HTMLButtonElement>()
  let replayButton = $state<HTMLButtonElement>()

  let runId = 0
  let liftTimer: ReturnType<typeof setTimeout> | undefined

  function sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms))
  }

  function charDelayMs(ch: string, index: number): number {
    if (ch === " ") return 110
    if (index >= GOOD_START && index <= GOOD_END) return 95
    return 56 + ((index * 19) % 24)
  }

  async function typeQuestion(): Promise<void> {
    const run = ++runId
    phase = "typing"
    typed = ""

    if (!v12Effects.fx) {
      reveal()
      return
    }

    if (!v12Effects.motionOK) {
      typed = QUESTION
      phase = "ready"
      return
    }

    await sleep(160)
    if (run !== runId) return

    for (let i = 0; i < QUESTION.length; i += 1) {
      if (!v12Effects.motionOK) {
        typed = QUESTION
        phase = "ready"
        return
      }
      const ch = QUESTION[i]
      typed += ch
      cueKeystroke(ch === " " ? "space" : "char")
      await sleep(charDelayMs(ch, i))
      if (run !== runId) return
    }

    await sleep(160)
    if (run !== runId) return
    cueKeystroke("enter")

    await sleep(140)
    if (run !== runId) return
    phase = "ready"
  }

  function replayWithSound(): void {
    if (phase === "lifting" || phase === "done" || !v12Effects.fx) return
    v12Effects.setSound(true)
    unlockSound(() => {
      void typeQuestion()
    })
  }

  function reveal(): void {
    if (phase === "lifting" || phase === "done") return
    runId += 1
    if (!v12Effects.fx) {
      onReveal()
      phase = "done"
      onComplete()
      return
    }
    cueReveal()
    onReveal()
    phase = "lifting"
    clearTimeout(liftTimer)
    liftTimer = setTimeout(() => {
      phase = "done"
      onComplete()
    }, v12Effects.motionOK ? 420 : 180)
  }

  function onKey(event: KeyboardEvent): void {
    if (phase === "lifting" || phase === "done" || event.altKey || event.ctrlKey || event.metaKey) return
    if (event.key === "Escape") {
      event.preventDefault()
      reveal()
      return
    }
    if (event.key === "Enter" && !(event.target instanceof HTMLButtonElement)) {
      event.preventDefault()
      reveal()
      return
    }
    if (event.key.toLowerCase() === "r" && !event.repeat) {
      event.preventDefault()
      if (v12Effects.sound) {
        unlockSound(() => {
          void typeQuestion()
        })
      } else {
        void typeQuestion()
      }
      return
    }
    if (event.key === "Tab") {
      event.preventDefault()
      if (phase === "typing") {
        skipButton?.focus()
      } else if (document.activeElement === revealButton) {
        replayButton?.focus()
      } else {
        revealButton?.focus()
      }
    }
  }

  $effect(() => {
    if (!v12Effects.fx && phase !== "done") {
      reveal()
    }
  })

  $effect(() => {
    if (phase === "typing") {
      skipButton?.focus({ preventScroll: true })
    } else if (phase === "ready") {
      revealButton?.focus({ preventScroll: true })
    }
  })

  onMount(() => {
    void typeQuestion()
    return () => {
      runId += 1
      clearTimeout(liftTimer)
    }
  })
</script>

<svelte:window onkeydown={onKey} />

{#if phase !== "done"}
  <div
    class="veil dir-phosphor"
    class:lifting={phase === "lifting"}
    role="dialog"
    aria-modal="true"
    aria-labelledby="veil-heading"
  >
    <div class="veil-scan" aria-hidden="true"></div>

    <div class="veil-stage" inert={phase === "lifting" || undefined}>
      <h1 id="veil-heading" class="sr-only">Is AI &ldquo;Good&rdquo; Yet?</h1>
      <p class="sr-only" aria-live="polite">
        {#if phase === "typing"}
          Typing question: Is AI good yet? Press Escape to skip.
        {:else if phase === "ready"}
          Ready. Choose show the answer or replay with typing sound.
        {/if}
      </p>

      <p class="veil-kicker">is-ai-good-yet <span>// hacker news &middot; ai coding</span></p>

      <p class="veil-prompt" aria-hidden="true">
        <span class="veil-sigil">&gt;</span>
        <span class="veil-text">{typed.slice(0, GOOD_START)}</span>
        <span class="veil-text veil-good">{typed.slice(GOOD_START, GOOD_END + 1)}</span>
        <span class="veil-text">{typed.slice(GOOD_END + 1)}</span>
        <span class="veil-caret"></span>
      </p>

      <div class="veil-actions">
        {#if phase === "typing"}
          <button
            bind:this={skipButton}
            type="button"
            class="veil-btn veil-btn-quiet"
            onclick={reveal}
          >
            skip &middot; esc
          </button>
        {:else}
          <button
            bind:this={revealButton}
            type="button"
            class="veil-btn veil-btn-primary"
            onclick={reveal}
          >
            show the answer
          </button>
          <button
            bind:this={replayButton}
            type="button"
            class="veil-btn"
            onclick={replayWithSound}
          >
            {v12Effects.sound ? "replay" : "replay with sound"}
          </button>
        {/if}
      </div>

      <p class="veil-hint" aria-hidden="true">enter reveal &middot; esc skip &middot; r replay</p>
    </div>
  </div>
{/if}

<style>
  .veil {
    position: fixed;
    inset: 0;
    z-index: 50;
    display: grid;
    place-items: center;
    padding: clamp(1rem, 4vw, 2.5rem);
    background: var(--td-ground);
    color: var(--td-ink);
    font-family: var(--font-mono);
    transform-origin: center center;
  }

  .veil.lifting {
    pointer-events: none;
    animation: veil-crt-off 420ms var(--ease-swift) forwards;
  }

  .veil-scan {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: repeating-linear-gradient(
      to bottom,
      transparent 0 2px,
      var(--td-scanline) 2px 3px
    );
    opacity: 0.28;
  }

  .veil-stage {
    position: relative;
    z-index: 1;
    width: min(100%, 44rem);
    border: 1px solid var(--td-rule);
    background: var(--td-surface);
    padding: clamp(1.25rem, 4vw, 2.25rem);
    display: grid;
    gap: 1.25rem;
  }

  .veil-kicker {
    margin: 0;
    font-size: 0.78rem;
    color: var(--td-muted);
  }

  .veil-kicker span {
    color: var(--td-faint);
  }

  .veil-prompt {
    margin: 0;
    min-height: 2.6em;
    font-size: clamp(1.35rem, 4.6vw, 2.5rem);
    line-height: 1.2;
    font-weight: 700;
    letter-spacing: -0.025em;
    color: var(--terminal-text);
    text-shadow: 0 0 0.35em var(--td-glow);
  }

  .veil-text.veil-good {
    color: var(--td-accent);
    text-shadow: 0 0 0.35em var(--td-glow);
  }

  .veil-sigil {
    color: var(--td-accent);
  }

  .veil-caret {
    display: inline-block;
    width: 0.55em;
    height: 1.05em;
    background: var(--td-accent);
    animation: veil-blink 1s steps(1) infinite;
  }

  .veil-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.65rem;
  }

  .veil-btn {
    min-height: 2.35rem;
    padding: 0 0.95rem;
    border: 1px solid var(--td-rule);
    background: var(--td-ground);
    color: var(--td-ink);
    font: inherit;
    font-size: 0.82rem;
    cursor: pointer;
    transition:
      background-color 140ms var(--ease-swift),
      border-color 140ms var(--ease-swift),
      color 140ms var(--ease-swift);
  }

  .veil-btn-primary {
    border-color: var(--td-accent);
    background: var(--td-accent);
    color: var(--td-ground);
    font-weight: 700;
  }

  .veil-btn-quiet {
    color: var(--td-muted);
  }

  .veil-btn:hover,
  .veil-btn:focus-visible {
    border-color: var(--td-accent);
    background: var(--td-hover);
    color: var(--td-ink-bright);
  }

  .veil-btn-primary:hover,
  .veil-btn-primary:focus-visible {
    background: var(--td-raised);
    color: var(--td-accent);
  }

  .veil-btn:focus-visible {
    outline: 2px solid var(--td-accent);
    outline-offset: 2px;
  }

  .veil-hint {
    margin: 0;
    font-size: 0.72rem;
    color: var(--td-faint);
  }

  @keyframes veil-blink {
    0%,
    50% {
      opacity: 1;
    }
    51%,
    100% {
      opacity: 0;
    }
  }

  @keyframes veil-crt-off {
    0% {
      transform: scale(1, 1);
      opacity: 1;
    }
    55% {
      transform: scale(1, 0.004);
      opacity: 1;
    }
    100% {
      transform: scale(0, 0.004);
      opacity: 0;
    }
  }

  @keyframes veil-fade {
    to {
      opacity: 0;
    }
  }

  :global(html.fx-off) .veil {
    display: none;
  }

  @media (prefers-reduced-motion: reduce) {
    .veil.lifting {
      animation-name: veil-fade;
      animation-duration: 180ms;
    }

    .veil-scan {
      display: none;
    }

    .veil-prompt {
      text-shadow: none;
    }

    .veil-caret {
      animation: none;
      opacity: 0.65;
    }

    .veil-btn {
      transition: none;
    }
  }
</style>
