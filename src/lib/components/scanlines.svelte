<script lang="ts">
  import { onMount } from "svelte"

  let el = $state<HTMLDivElement | null>(null)
  let docHeight = $state("100vh")

  function updateHeight() {
    docHeight = `${document.documentElement.scrollHeight}px`
  }

  onMount(() => {
    updateHeight()
    const ro = new ResizeObserver(updateHeight)
    ro.observe(document.body)
    window.addEventListener("load", updateHeight)
    return () => {
      ro.disconnect()
      window.removeEventListener("load", updateHeight)
    }
  })
</script>

<div
  bind:this={el}
  class="scanlines"
  aria-hidden="true"
  style="height: {docHeight};"
></div>

<style>
  .scanlines {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    z-index: 60;
    pointer-events: none;

    background-image: linear-gradient(
      to bottom,
      oklch(0 0 0 / 0.12) 1px,
      transparent 1px
    );
    background-size: 100% 2px;
  }
</style>
