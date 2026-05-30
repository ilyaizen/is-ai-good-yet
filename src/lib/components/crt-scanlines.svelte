<script lang="ts">
  import { onMount } from "svelte"

  let { show = true } = $props<{ show?: boolean }>()

  let contentHeight = $state(0)

  function updateHeight() {
    contentHeight = Math.max(
      document.body.scrollHeight,
      document.documentElement.scrollHeight
    )
  }

  onMount(() => {
    updateHeight()
    const observer = new ResizeObserver(() => updateHeight())
    observer.observe(document.body)
    window.addEventListener("load", updateHeight)
    return () => {
      observer.disconnect()
      window.removeEventListener("load", updateHeight)
    }
  })
</script>

{#if show}
  <!-- Scanlines: scrolls with content. Height matches full document. -->
  <div
    class="crt-scanlines"
    aria-hidden="true"
    style="height: {contentHeight}px;"
  ></div>

  <!-- Vignette: fixed viewport overlay. -->
  <div class="crt-vignette" aria-hidden="true"></div>
{/if}

<style>
  .crt-scanlines {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    z-index: var(--crt-z-index);
    pointer-events: none;

    background-image: linear-gradient(
      to bottom,
      oklch(0 0 0 / var(--crt-scanline-opacity)) 1px,
      transparent 1px
    );
    background-size: 100% 2px;
    background-repeat: repeat-y;

    animation: crt-flicker var(--crt-flicker-speed) linear infinite;
  }

  .crt-vignette {
    position: fixed;
    inset: 0;
    z-index: var(--crt-z-index);
    pointer-events: none;

    background: radial-gradient(
      ellipse at center,
      oklch(0 0 0 / 0) 50%,
      oklch(0 0 0 / var(--crt-vignette-opacity)) 100%
    );
  }

  :global(.dark) .crt-scanlines {
    background-image: linear-gradient(
      to bottom,
      oklch(0 0 0 / var(--crt-scanline-opacity)) 1px,
      transparent 1px
    );
  }

  :global(:not(.dark)) .crt-scanlines {
    background-image: linear-gradient(
      to bottom,
      oklch(0 0 0 / calc(var(--crt-scanline-opacity) * 0.7)) 1px,
      transparent 1px
    );
  }

  @keyframes crt-flicker {
    0%, 100% { opacity: 1; }
    3% { opacity: 0.97; }
    6% { opacity: 1; }
    42% { opacity: 0.98; }
    44% { opacity: 1; }
    78% { opacity: 0.96; }
    80% { opacity: 1; }
  }
</style>
