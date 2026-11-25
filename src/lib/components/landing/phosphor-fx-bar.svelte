<script lang="ts">
  import { cueToggle, silenceSound, unlockSound } from "$lib/audio/v12-sound"
  import { v12Effects } from "$lib/state/v12-effects.svelte"

  let {
    onReplay,
    replayDisabled = false,
  }: {
    onReplay: () => void
    replayDisabled?: boolean
  } = $props()

  function toggleFx(): void {
    if (v12Effects.fx) {
      v12Effects.setFx(false)
      silenceSound()
    } else {
      v12Effects.setFx(true)
      unlockSound(cueToggle)
    }
  }

  function toggleSound(): void {
    if (!v12Effects.fx) return
    if (v12Effects.sound) {
      v12Effects.setSound(false)
      silenceSound()
    } else {
      v12Effects.setSound(true)
      unlockSound(cueToggle)
    }
  }

  function triggerReplay(): void {
    if (!v12Effects.fx || replayDisabled) return
    unlockSound(cueToggle)
    onReplay()
  }
</script>

<div class="fx-bar" role="group" aria-label="Display, audio, and replay controls">
  <button
    type="button"
    class="fx-btn"
    aria-pressed={v12Effects.fx}
    onclick={toggleFx}
    title="Toggle visual effects and interaction sounds"
  >
    Effects <b aria-hidden="true">{v12Effects.fx ? "On" : "Off"}</b>
  </button>
  <button
    type="button"
    class="fx-btn"
    aria-pressed={v12Effects.crt}
    disabled={!v12Effects.fx}
    onclick={() => v12Effects.setCrt(!v12Effects.crt)}
  >
    CRT <b aria-hidden="true">{v12Effects.crt ? "On" : "Off"}</b>
  </button>
  <button
    type="button"
    class="fx-btn"
    aria-pressed={v12Effects.sound}
    disabled={!v12Effects.fx}
    onclick={toggleSound}
    title={v12Effects.fx ? "Toggle synthesized interaction audio (session only)" : "Enable FX first to use sound"}
  >
    Sound <b aria-hidden="true">{v12Effects.sound ? "On" : "Off"}</b>
  </button>
  <button
    type="button"
    class="fx-btn"
    disabled={!v12Effects.fx || replayDisabled}
    onclick={triggerReplay}
    title={v12Effects.fx ? "Replay intro prompt (R)" : "Enable FX first to replay intro"}
  >
    Replay intro
  </button>
</div>

<style>
  .fx-bar {
    display: inline-flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.35rem;
    font-family: var(--font-mono);
    font-size: 0.72rem;
  }

  .fx-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    min-height: 1.9rem;
    padding: 0 0.55rem;
    border: 1px solid var(--td-rule);
    background: var(--td-surface);
    color: var(--td-muted);
    font: inherit;
    letter-spacing: 0.04em;
    cursor: pointer;
    white-space: nowrap;
    transition:
      border-color 140ms var(--ease-swift),
      color 140ms var(--ease-swift),
      background-color 140ms var(--ease-swift);
  }

  .fx-btn b {
    font-weight: 700;
    color: var(--td-ink);
  }

  .fx-btn:hover:not(:disabled),
  .fx-btn:focus-visible {
    border-color: var(--td-accent);
    color: var(--td-ink);
  }

  .fx-btn[aria-pressed="true"] {
    border-color: var(--td-accent);
    background: var(--td-hover);
  }

  .fx-btn[aria-pressed="true"] b {
    color: var(--td-accent);
  }

  .fx-btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .fx-btn:focus-visible {
    outline: 2px solid var(--td-accent);
    outline-offset: 2px;
  }

  :global(html.fx-off) .fx-btn {
    transition: none;
  }

  @media (prefers-reduced-motion: reduce) {
    .fx-btn {
      transition: none;
    }
  }
</style>
