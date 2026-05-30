<script lang="ts">
  import { getLenis } from "$lib/scroll";
  import { onMount } from "svelte";

  interface Props {
    /** Scroll progress 0..1 (from Lenis). */
    progress: number;
  }

  let { progress = 0 }: Props = $props();

  let dragging = $state(false);
  let trackRef: HTMLDivElement | null = $state(null);
  // Thumb height as a fraction of the track = viewport / document height.
  let thumbRatio = $state(0.15);

  const MIN_THUMB = 0.06;

  function measure() {
    const docHeight = document.documentElement.scrollHeight;
    const view = window.innerHeight;
    thumbRatio =
      docHeight > 0 ? Math.max(MIN_THUMB, Math.min(1, view / docHeight)) : 1;
  }

  onMount(() => {
    measure();
    window.addEventListener("resize", measure);
    // Document height changes after load (lazy data, images) — keep thumb sized.
    const ro = new ResizeObserver(measure);
    ro.observe(document.documentElement);
    return () => {
      window.removeEventListener("resize", measure);
      ro.disconnect();
    };
  });

  function moveToPointer(e: PointerEvent) {
    if (!trackRef) return;
    const lenis = getLenis();
    if (!lenis) return;
    const rect = trackRef.getBoundingClientRect();
    // Map cursor to thumb-center travel so the thumb follows the pointer 1:1.
    const usable = rect.height * (1 - thumbRatio);
    const offset = e.clientY - rect.top - (rect.height * thumbRatio) / 2;
    const ratio = usable > 0 ? Math.max(0, Math.min(1, offset / usable)) : 0;
    const limit = document.documentElement.scrollHeight - window.innerHeight;
    lenis.scrollTo(ratio * limit, { immediate: true });
  }

  function onPointerDown(e: PointerEvent) {
    dragging = true;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    moveToPointer(e);
  }

  function onPointerMove(e: PointerEvent) {
    if (dragging) moveToPointer(e);
  }

  function onPointerUp() {
    dragging = false;
  }

  const thumbStyle = $derived(() => {
    const p = Math.max(0, Math.min(1, progress));
    const travel = p * (1 - thumbRatio);
    return `transform: translateY(${travel * 100}%); height: ${thumbRatio * 100}%;`;
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
