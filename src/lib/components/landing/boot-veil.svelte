<script lang="ts">
  import { onMount } from "svelte"
  import { v12Effects } from "$lib/state/v12-effects.svelte"
  import {
    cueFail,
    cuePost,
    cueProbe,
    cueReveal,
    cueStinger,
    cueTick,
    type Answer,
  } from "$lib/audio/v12-sound"

  let {
    onReveal,
    articleCount,
    verdict = null,
  }: {
    onReveal: () => void
    articleCount: number
    verdict?: string | null
  } = $props()

  type LogLine = {
    text: string
    status: "none" | "pending" | "ok" | "fail"
    note: string
  }

  const PROBES: Array<{ path: string; note: string; fails?: boolean; failNote?: string }> = [
    { path: "/dev/sentiment", note: "weighting live" },
    { path: "/dev/history", note: "90-day trace" },
    { path: "/dev/hn0", note: "front page" },
    { path: "/dev/scope", note: "afterglow ok" },
    { path: "/dev/quotes", note: "attributed" },
    { path: "/dev/hype", note: "optimism cache", fails: true, failNote: "cleared, continuing" },
  ]

  let lines = $state<LogLine[]>([])
  let progressText = $state("")
  let memCount = $state(0)
  let memLineIndex = $state(-1)
  let spinChar = $state("|")
  let verdictTyped = $state("")
  let readyToReveal = $state(false)
  let lifting = $state(false)
  let warm = $state(false)
  let revealBtn = $state<HTMLButtonElement | null>(null)

  // Generation token: bumping `run` cancels every in-flight sleep in the
  // current sequence (skip, replay, FX-off mid-boot).
  let run = 0
  let lifted = false

  const answer: Answer = (() => {
    const s = (verdict ?? "").trim().toUpperCase()
    if (s === "YES") return "YES"
    if (s === "NO") return "NO"
    return "NOT YET"
  })()

  let liveText = $derived(
    `System boot sequence. ${lines.length} log lines.` +
      (readyToReveal ? ` Verdict: ${answer}. Press "show the answer" to continue.` : "")
  )

  function sleep(ms: number, gen: number): Promise<boolean> {
    const capped = v12Effects.motionOK ? ms : Math.min(ms, 40)
    return new Promise((resolve) => {
      setTimeout(() => resolve(gen === run), capped)
    })
  }

  function push(text: string, gen: number): boolean {
    lines.push({ text, status: "none", note: "" })
    cueTick(lines.length)
    return gen === run
  }

  async function runProgress(gen: number): Promise<boolean> {
    const steps = 12
    if (!v12Effects.motionOK) {
      progressText = `read /corpus/verdict [${"█".repeat(steps)}] 100%`
      return gen === run
    }
    for (let i = 0; i <= steps * 2; i += 1) {
      const t = i / (steps * 2)
      const eased = 1 - Math.pow(1 - t, 3)
      const filled = Math.round(eased * steps)
      const pct = Math.round(eased * 100)
      progressText = `read /corpus/verdict [${"█".repeat(filled)}${"░".repeat(steps - filled)}] ${pct}%`
      if (i % 2 === 0) cueTick(i)
      if (!(await sleep(28, gen))) return false
    }
    return true
  }

  async function runMemoryTest(gen: number): Promise<boolean> {
    memLineIndex = lines.length
    lines.push({ text: "", status: "none", note: "" })
    if (!v12Effects.motionOK) {
      memCount = articleCount
      lines[memLineIndex].text = `corpus memory test · ${articleCount.toLocaleString("en-US")} articles`
      return gen === run
    }
    const total = 420
    for (let i = 0; i <= total / 25; i += 1) {
      const t = i / (total / 25)
      const eased = 1 - Math.pow(1 - t, 3)
      memCount = Math.round(eased * articleCount)
      lines[memLineIndex].text = `corpus memory test · ${memCount.toLocaleString("en-US")} articles`
      if (!(await sleep(25, gen))) return false
    }
    memCount = articleCount
    lines[memLineIndex].text = `corpus memory test · ${articleCount.toLocaleString("en-US")} articles`
    return true
  }

  async function runProbes(gen: number): Promise<boolean> {
    for (const probe of PROBES) {
      const index = lines.length
      lines.push({ text: `probe ${probe.path}`, status: "pending", note: probe.note })
      if (!(await sleep(probe.fails ? 150 : 90, gen))) return false
      if (gen !== run) return false
      if (probe.fails) {
        lines[index].status = "fail"
        lines[index].note = `${probe.note} · ${probe.failNote ?? ""}`
        cueFail()
      } else {
        lines[index].status = "ok"
        cueProbe()
      }
      if (!(await sleep(probe.fails ? 110 : 50, gen))) return false
    }
    cuePost()
    return true
  }

  async function runCompile(gen: number): Promise<boolean> {
    const index = lines.length
    lines.push({ text: "compiling verdict", status: "none", note: "" })
    if (!v12Effects.motionOK) {
      lines[index].text = "compiling verdict · done"
      return gen === run
    }
    const frames = ["|", "/", "-", "\\"]
    for (let i = 0; i < 12; i += 1) {
      spinChar = frames[i % frames.length]
      lines[index].text = `compiling verdict ${spinChar}`
      if (!(await sleep(70, gen))) return false
    }
    lines[index].text = "compiling verdict · done"
    return true
  }

  async function typeVerdict(gen: number): Promise<boolean> {
    const full = `VERDICT: ${answer}.`
    if (!v12Effects.motionOK) {
      verdictTyped = full
      return gen === run
    }
    for (let i = 1; i <= full.length; i += 1) {
      verdictTyped = full.slice(0, i)
      cueTick(i)
      if (!(await sleep(55, gen))) return false
    }
    return true
  }

  async function startBoot(): Promise<void> {
    const gen = ++run
    lines = []
    progressText = ""
    memCount = 0
    memLineIndex = -1
    verdictTyped = ""
    readyToReveal = false

    if (warm) {
      if (!push("warm start · verdict cached", gen)) return
      if (!(await sleep(140, gen))) return
    } else {
      if (!push("mount /corpus ......... ok", gen)) return
      if (!(await sleep(160, gen))) return
      if (!push("read /corpus/verdict", gen)) return
      if (!(await runProgress(gen))) return
      if (!(await sleep(80, gen))) return
      if (!(await runMemoryTest(gen))) return
      if (!(await sleep(90, gen))) return
    }
    if (!(await runProbes(gen))) return
    if (!(await sleep(120, gen))) return
    if (!(await runCompile(gen))) return
    if (!(await sleep(110, gen))) return
    if (!(await typeVerdict(gen))) return
    cueStinger(answer)
    if (!(await sleep(140, gen))) return
    if (gen !== run) return
    readyToReveal = true
  }

  function lift(instant = false): void {
    if (lifted) return
    lifted = true
    if (!instant && v12Effects.fx) cueReveal()
    lifting = true
    onReveal()
  }

  function skip(): void {
    if (lifted) return
    run += 1
    lift(true)
  }

  function handleKeydown(event: KeyboardEvent): void {
    if (event.metaKey || event.ctrlKey || event.altKey) return
    if (event.key === "Escape") {
      skip()
    } else if (event.key === "r" || event.key === "R") {
      // Re-scan: restart the boot from scratch.
      warm = false
      void startBoot()
    }
  }

  // FX switched off mid-boot: cancel and lift instantly, no ceremony.
  $effect(() => {
    if (!v12Effects.fx && !lifted && lines.length > 0) {
      run += 1
      lift(true)
    }
  })

  $effect(() => {
    if (readyToReveal) {
      revealBtn?.focus()
    }
  })

  onMount(() => {
    v12Effects.init()
    warm = localStorage.getItem("isAiGoodYetRevealed") === "true"
    void startBoot()
  })
</script>

<svelte:window onkeydown={handleKeydown} />

<!--
  v1.2 boot veil: the nightly pipeline run staged as a machine booting.
  Replaces verdict-veil.svelte for the landing route with the same contract.
  Esc / click skips; R replays; FX off cancels the boot and lifts instantly.
-->
<div
  class="boot-veil"
  class:lifting
  onclick={skip}
  role="presentation"
>
  <div class="screen" role="dialog" aria-modal="true" aria-label="System boot">
    <p class="sr-only" aria-live="polite">{liveText}</p>

    <div class="log" aria-hidden="true">
      {#each lines as line, i (i)}
        <div class="log-line">
          <span class="log-text" class:glow={line.status === "ok"}>{line.text}</span>
          {#if line.status === "pending"}
            <span class="log-status pending">··</span>
          {:else if line.status === "ok"}
            <span class="log-status ok">ok</span>
            {#if line.note}
              <span class="log-note">{line.note}</span>
            {/if}
          {:else if line.status === "fail"}
            <span class="log-status fail">FAIL</span>
            {#if line.note}
              <span class="log-note">{line.note}</span>
            {/if}
          {:else if line.note}
            <span class="log-note">{line.note}</span>
          {/if}
        </div>
      {/each}

      {#if progressText}
        <div class="log-line">
          <span class="log-text glow">{progressText}</span>
        </div>
      {/if}

      {#if memLineIndex >= 0 && lines[memLineIndex]}
        <div class="log-line">
          <span class="log-text">{lines[memLineIndex].text}</span>
        </div>
      {/if}

      {#if verdictTyped}
        <div class="verdict-line">
          <span class="verdict-text glow">{verdictTyped}</span>
          {#if !readyToReveal}
            <span class="caret"></span>
          {/if}
        </div>
      {/if}
    </div>

    {#if readyToReveal}
      <div class="prompt-row" aria-hidden="false">
        <span class="prompt" aria-hidden="true">guest@is-ai-good-yet:~$</span>
        <button
          bind:this={revealBtn}
          class="reveal-btn"
          onclick={(event) => {
            event.stopPropagation()
            lift()
          }}
        >
          show the answer
        </button>
        <span class="hint" aria-hidden="true">esc skip · r replay</span>
      </div>
    {/if}
  </div>
</div>

<style>
  .boot-veil {
    position: fixed;
    inset: 0;
    z-index: 50;
    background: var(--phosphor-screen);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1.25rem;
    cursor: pointer;
  }

  .boot-veil.lifting {
    pointer-events: none;
    animation: crt-off 460ms var(--ease-swift) forwards;
  }

  :global(html.fx-off) .boot-veil.lifting {
    animation-name: veil-fade;
  }

  @keyframes crt-off {
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

  @media (prefers-reduced-motion: reduce) {
    .boot-veil.lifting {
      animation-name: veil-fade;
      animation-duration: 200ms;
    }
  }

  .screen {
    width: 100%;
    max-width: 42rem;
    max-height: 100%;
    overflow: hidden;
    font-family: var(--font-mono);
    color: var(--phosphor-text);
    cursor: default;
  }

  .log {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    font-size: 0.8125rem;
    line-height: 1.7;
  }

  .log-line {
    display: flex;
    align-items: baseline;
    gap: 0.6rem;
    white-space: pre-wrap;
    min-height: 1.38rem;
  }

  .log-text {
    color: var(--phosphor-muted);
  }

  .log-text.glow {
    color: var(--phosphor-text);
  }

  .glow {
    text-shadow: 0 0 6px var(--phosphor-glow);
  }

  .log-status {
    flex: none;
  }

  .log-status.pending {
    color: var(--phosphor-faint);
  }

  .log-status.ok {
    color: var(--phosphor-beam);
  }

  .log-status.fail {
    background: var(--phosphor-beam);
    color: var(--phosphor-screen);
    padding: 0 0.35rem;
  }

  .log-note {
    color: var(--phosphor-faint);
    font-size: 0.75rem;
  }

  .verdict-line {
    margin-top: 0.9rem;
    font-size: 1.25rem;
    letter-spacing: 0.02em;
    display: flex;
    align-items: baseline;
  }

  .verdict-text {
    color: var(--phosphor-bright);
  }

  .caret {
    display: inline-block;
    width: 0.55em;
    height: 1.1em;
    margin-left: 0.15rem;
    background: var(--phosphor-beam);
    animation: caret-blink 1s step-end infinite;
  }

  :global(html.fx-off) .caret {
    animation: none;
    opacity: 0.6;
  }

  @keyframes caret-blink {
    0%,
    50% {
      opacity: 1;
    }
    51%,
    100% {
      opacity: 0;
    }
  }

  .prompt-row {
    margin-top: 1.4rem;
    display: flex;
    align-items: center;
    gap: 0.9rem;
    flex-wrap: wrap;
    font-size: 0.8125rem;
  }

  .prompt {
    color: var(--phosphor-faint);
  }

  .reveal-btn {
    font-family: var(--font-mono);
    font-size: 0.8125rem;
    color: var(--phosphor-bright);
    background: transparent;
    border: 1px solid var(--phosphor-border);
    padding: 0.45rem 1.1rem;
    cursor: pointer;
    transition:
      background-color 90ms var(--ease-swift),
      border-color 90ms var(--ease-swift);
  }

  .reveal-btn:hover {
    background: var(--phosphor-glow);
    border-color: var(--phosphor-beam);
  }

  .reveal-btn:focus-visible {
    outline: 1px solid var(--phosphor-beam);
    outline-offset: 2px;
  }

  .hint {
    color: var(--phosphor-faint);
    font-size: 0.6875rem;
  }

  @media (prefers-reduced-motion: reduce) {
    .reveal-btn {
      transition: none;
    }
  }
</style>
