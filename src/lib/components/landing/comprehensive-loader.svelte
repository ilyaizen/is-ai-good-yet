<script lang="ts">
  import { ChevronRight } from "lucide-svelte"

  let { visible = true }: { visible?: boolean } = $props()
</script>

<div class="loader-overlay" class:hidden={!visible}>
  <div class="terminal-panel loader-panel">
    <div class="loader-content">
      <div class="loader-header">
        <ChevronRight color="var(--color-accent)" strokeWidth={3} />
        <span class="font-mono font-semibold">Loading:</span>
      </div>

      <div class="spinner-container">
        <div class="spinner"></div>
      </div>

      <div class="loader-text">
        <span class="font-mono text-sm text-muted-foreground">Initializing data pipeline...</span>
        <span class="cursor blink"></span>
      </div>
    </div>
  </div>
</div>

<style>
  .loader-overlay {
    position: fixed;
    inset: 0;
    z-index: 100;
    background: var(--terminal-bg-overlay);
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 1;
    transition:
      opacity 400ms var(--ease-swift),
      visibility 400ms var(--ease-swift);
  }

  .loader-overlay.hidden {
    opacity: 0;
    visibility: hidden;
  }

  .loader-panel {
    min-width: 20rem;
    padding: 3rem 4rem;
    animation: panel-scale-in 400ms var(--ease-swift);
  }

  @keyframes panel-scale-in {
    from {
      opacity: 0;
      transform: scale(0.9);
    }
    to {
      opacity: 1;
      transform: scale(1);
    }
  }

  .loader-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2rem;
  }

  .loader-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--terminal-text);
  }

  .spinner-container {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 4rem;
  }

  .spinner {
    width: 3rem;
    height: 3rem;
    border: 3px solid var(--terminal-border-subtle);
    border-top-color: var(--terminal-accent);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    box-shadow: 0 0 12px var(--terminal-accent-glow);
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .loader-text {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    color: var(--terminal-text-muted);
  }

  .cursor {
    display: inline-block;
    width: 10px;
    height: 1.2em;
    background-color: var(--terminal-cursor);
    vertical-align: text-bottom;
  }

  @keyframes blink {
    0%,
    50% {
      opacity: 1;
    }
    51%,
    100% {
      opacity: 0;
    }
  }
</style>
