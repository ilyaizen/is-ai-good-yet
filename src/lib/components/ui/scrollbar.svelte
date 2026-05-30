<script lang="ts">
  import { getLenis } from "$lib/scroll";

  interface Props {
    progress: number;
  }

  let { progress = 0 }: Props = $props();

  let dragging = $state(false);
  let trackRef: HTMLDivElement | null = $state(null);
  const THUMB_RATIO = 0.12;

  function moveToPointer(e: PointerEvent) {
    if (!trackRef) return;
    const rect = trackRef.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
    const lenis = getLenis();
    if (!lenis) return;
    const docHeight = Math.max(
      0,
      document.documentElement.scrollHeight - window.innerHeight
    );
    lenis.scrollTo(ratio * docHeight);
  }

  function onPointerDown(e: PointerEvent) {
    dragging = true;
    const target = e.currentTarget as HTMLElement;
    target.setPointerCapture(e.pointerId);
    moveToPointer(e);
  }

  function onPointerMove(e: PointerEvent) {
    if (!dragging) return;
    moveToPointer(e);
  }

  function onPointerUp() {
    dragging = false;
  }

  const thumbStyle = $derived(() => {
    const p = Math.max(0, Math.min(1, progress));
    const travelRatio = p * (1 - THUMB_RATIO);
    return `transform: translateY(${travelRatio * 100}%);
            height: ${THUMB_RATIO * 100}%;`;
  });
</script>

<div
  class="scrollbar-track"
  bind:this={trackRef}
  role="slider"
  tabindex="0"
  aria-label="Page scroll position"
  aria-orientation="vertical"
  aria-valuemin={0}
  aria-valuemax={100}
  aria-valuenow={Math.round(progress * 100)}
  onpointerdown={onPointerDown}
  onpointermove={onPointerMove}
  onpointerup={onPointerUp}
  onpointercancel={onPointerUp}
>
  <div
    class="scrollbar-thumb"
    class:is-dragging={dragging}
    style={thumbStyle()}
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
    top: 0;
    right: 0;
    width: 6px;
    border-radius: 3px;
    background: var(--color-text-secondary, rgba(255, 255, 255, 0.25));
    opacity: 0.35;
    transition: opacity 0.15s ease, width 0.15s ease;
    cursor: grab;
    will-change: transform;
    pointer-events: none;
  }

  .scrollbar-thumb.is-dragging {
    opacity: 0.7;
    width: 8px;
    cursor: grabbing;
  }

  .scrollbar-track:hover .scrollbar-thumb {
    opacity: 0.5;
  }
</style>
