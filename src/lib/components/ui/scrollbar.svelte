<script lang="ts">
  import { onMount } from "svelte";

  interface Props {
    progress: number;
  }

  let { progress = 0 }: Props = $props();

  let dragging = $state(false);
  let trackRef: HTMLDivElement | null = $state(null);

  function onPointerDown(e: PointerEvent) {
    dragging = true;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    onPointerMove(e);
  }

  function onPointerMove(e: PointerEvent) {
    if (!dragging || !trackRef) return;
    const rect = trackRef.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
    // Dispatch a custom event the layout can listen to
    trackRef.dispatchEvent(
      new CustomEvent("scroll-to-ratio", { detail: ratio, bubbles: true })
    );
  }

  function onPointerUp(e: PointerEvent) {
    dragging = false;
    (e.target as HTMLElement).releasePointerCapture(e.pointerId);
  }
</script>

<div class="scrollbar-track" bind:this={trackRef} onpointerdown={onPointerDown} role="presentation">
  <div
    class="scrollbar-thumb"
    class:is-dragging={dragging}
    role="scrollbar"
    aria-orientation="vertical"
    aria-valuemin={0}
    aria-valuemax={100}
    aria-valuenow={Math.round(progress * 100)}
    onpointerdown={onPointerDown}
    onpointermove={onPointerMove}
    onpointerup={onPointerUp}
    onpointercancel={onPointerUp}
    style="top: {progress * 100}%;"
  ></div>
</div>

<style>
  .scrollbar-track {
    position: fixed;
    top: 0;
    right: 0;
    width: 6px;
    height: 100vh;
    z-index: 9999;
    cursor: pointer;
    background: transparent;
  }

  .scrollbar-thumb {
    position: absolute;
    right: 0;
    width: 6px;
    min-height: 40px;
    border-radius: 3px;
    background: var(--color-text-secondary, #666);
    opacity: 0.35;
    transition: opacity 0.15s ease, width 0.15s ease;
    cursor: grab;
    will-change: top;
  }

  .scrollbar-thumb:hover,
  .scrollbar-thumb.is-dragging {
    opacity: 0.6;
    width: 8px;
    cursor: grabbing;
  }

  .scrollbar-track:hover .scrollbar-thumb {
    opacity: 0.5;
  }
</style>
