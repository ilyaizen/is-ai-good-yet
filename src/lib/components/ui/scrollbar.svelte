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
    const maxScroll = Math.max(
      0,
      document.body.scrollHeight - window.innerHeight
    );
    lenis.scrollTo(ratio * maxScroll, { immediate: false });
  }

  function onPointerDown(e: PointerEvent) {
    dragging = true;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    moveToPointer(e);
  }

  function onPointerMove(e: PointerEvent) {
    if (!dragging) return;
    moveToPointer(e);
  }

  function onPointerUp() {
    dragging = false;
  }

  const thumbTransform = $derived(() => {
    const p = Math.max(0, Math.min(1, progress));
    return `transform: translateY(calc(${p * 100}% * (1 - ${THUMB_RATIO})));
            height: ${THUMB_RATIO * 100}%;`;
  });
</script>

<div class="scrollbar-track" bind:this={trackRef} onpointerdown={onPointerDown} role="presentation">
  <div
    class="scrollbar-thumb"
    class:is-dragging={dragging}
    role="slider"
    tabindex="0"
    aria-orientation="vertical"
    aria-valuemin={0}
    aria-valuemax={100}
    aria-valuenow={Math.round(progress * 100)}
    aria-label="Scroll position"
    onpointerdown={onPointerDown}
    onpointermove={onPointerMove}
    onpointerup={onPointerUp}
    onpointercancel={onPointerUp}
    style={thumbTransform()}
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
  }

  .scrollbar-thumb:hover,
  .scrollbar-thumb.is-dragging {
    opacity: 0.7;
    width: 8px;
    cursor: grabbing;
  }

  .scrollbar-track:hover .scrollbar-thumb {
    opacity: 0.5;
  }
</style>
