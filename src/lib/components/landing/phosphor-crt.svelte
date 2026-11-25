<script lang="ts">
  import { devicePixelRatio } from "svelte/reactivity/window";
  import { v12Effects } from "$lib/state/v12-effects.svelte";

  const filterId = $props.id();
  const dpr = $derived(devicePixelRatio.current ?? 1);
  // Whole device pixels keep neighboring raster lines even at fractional browser zoom.
  const row = $derived(Math.max(1, Math.round(dpr)) / dpr);
</script>

{#if v12Effects.crt}
  <svg class="crt-defs" width="0" height="0" aria-hidden="true" focusable="false">
    <defs>
      <filter id={filterId} color-interpolation-filters="sRGB" x="0%" y="0%" width="100%" height="100%">
        <!-- Keep green registered and most of each outer beam in place so small type stays sharp. -->
        <feColorMatrix in="SourceGraphic" values=".72 0 0 0 0  0 1 0 0 0  0 0 .72 0 0  0 0 0 1 0" result="core" />
        <feOffset in="SourceGraphic" dx="-1" result="left" />
        <feColorMatrix in="left" values=".28 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" result="red" />
        <feOffset in="SourceGraphic" dx="1" result="right" />
        <feColorMatrix in="right" values="0 0 0 0 0  0 0 0 0 0  0 0 .28 0 0  0 0 0 1 0" result="blue" />
        <feComposite in="red" in2="blue" operator="arithmetic" k2="1" k3="1" result="fringe" />
        <feComposite in="core" in2="fringe" operator="arithmetic" k2="1" k3="1" />
      </filter>
    </defs>
  </svg>
  <div class="crt-layer crt-raster" aria-hidden="true" style:--row={`${row}px`}></div>
  <div class="crt-layer crt-glass" aria-hidden="true" style:--registration={`url(#${filterId})`}></div>
{/if}

<style>
  .crt-defs {
    position: absolute;
    pointer-events: none;
  }

  .crt-layer {
    position: fixed;
    inset: 0;
    z-index: 55;
    pointer-events: none;
  }

  .crt-raster {
    background: repeating-linear-gradient(
      to bottom,
      var(--palette-gray-950) 0 var(--row),
      var(--palette-gray-400) var(--row) calc(2 * var(--row))
    );
    mix-blend-mode: hard-light;
    opacity: 0.19;
  }

  .crt-glass {
    background: radial-gradient(ellipse at center, transparent 52%, var(--phosphor-vignette) 100%);
  }

  /* Small screens keep the physical raster, not the extra full-screen color pass. */
  @media (min-width: 48rem) and (prefers-reduced-motion: no-preference) {
    .crt-glass {
      backdrop-filter: var(--registration) saturate(1.1) contrast(1.03) brightness(1.06);
    }
  }

  :global(html.fx-off) .crt-layer {
    display: none;
  }

  @media print, (forced-colors: active), (prefers-contrast: more) {
    .crt-layer {
      display: none;
    }
  }
</style>
