<script lang="ts">
  let { visible = true }: { visible?: boolean } = $props()
</script>

<!--
  v1.2 boot loader — replaces comprehensive-loader.svelte for the landing.
  CSS-only fetch-log panel: the progress fill animates via a transition, so
  FX-off and prefers-reduced-motion degrade to a static full bar with no JS.
-->
<div class="boot-loader" class:hidden={!visible} aria-hidden={!visible}>
  <div class="panel">
    <div class="line">
      <span class="cmd">mount /corpus</span>
      <span class="ok">ok</span>
    </div>
    <div class="line">
      <span class="cmd">read /corpus/verdict</span>
      <span class="track" role="progressbar" aria-label="Loading data">
        <span class="fill"></span>
      </span>
    </div>
  </div>
</div>

<style>
  .boot-loader {
    position: fixed;
    inset: 0;
    z-index: 100;
    background: var(--phosphor-screen, var(--terminal-bg-overlay));
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 1;
    transition:
      opacity 300ms var(--ease-swift),
      visibility 300ms var(--ease-swift);
  }

  .boot-loader.hidden {
    opacity: 0;
    visibility: hidden;
  }

  .panel {
    min-width: 18rem;
    max-width: 24rem;
    padding: 1.5rem 2rem;
    border: 1px solid var(--phosphor-border);
    background: var(--terminal-bg);
    font-family: var(--font-mono);
    color: var(--phosphor-muted);
  }

  .line {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    font-size: 0.8125rem;
    line-height: 1.9;
  }

  .cmd {
    color: var(--phosphor-text);
  }

  .ok {
    color: var(--phosphor-beam);
  }

  .track {
    flex: 1;
    height: 0.5rem;
    overflow: hidden;
    border: 1px solid var(--phosphor-border);
  }

  .fill {
    display: block;
    height: 100%;
    width: 100%;
    background: var(--phosphor-beam);
    transform-origin: left center;
    animation: fill-bar 420ms var(--ease-swift) both;
  }

  @keyframes fill-bar {
    from {
      transform: scaleX(0);
    }
    to {
      transform: scaleX(1);
    }
  }

  :global(html.fx-off) .fill {
    animation: none;
  }

  @media (prefers-reduced-motion: reduce) {
    .fill {
      animation: none;
    }
  }
</style>
