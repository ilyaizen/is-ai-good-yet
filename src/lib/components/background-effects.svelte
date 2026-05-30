<script lang="ts">
  interface Props {
    showCrt?: boolean
  }

  let { showCrt = true }: Props = $props()
</script>

<div class="bg-grid" aria-hidden="true"></div>
<div class="bg-vignette" aria-hidden="true"></div>
{#if showCrt}
  <div class="crt-overlay" aria-hidden="true"></div>
{/if}

<style>
  .bg-grid {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-image: radial-gradient(var(--color-dot) 1px, transparent 1px);
    background-size: 24px 24px;
    z-index: -2;
    opacity: 0.18;
    pointer-events: none;
  }

  .bg-vignette {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: radial-gradient(circle at center, transparent 0%, var(--color-bg) 100%);
    z-index: -1;
    pointer-events: none;
  }

  .crt-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(black 50%, rgba(0, 0, 0, 0.1) 50%);
    background-size: 100% 4px;
    pointer-events: none;
    z-index: 9999;
    opacity: 0.18;
  }

  @media (prefers-reduced-motion: reduce) {
    .crt-overlay {
      display: none;
    }
  }
</style>
