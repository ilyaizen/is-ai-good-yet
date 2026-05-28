import { scrollBus } from "./scroll-bus.svelte";

const SMOOTH_FACTOR = 0.085;
const WHEEL_MULTIPLIER = 0.8;
const TOUCH_MULTIPLIER = 0.9;
const TOUCH_INERTIA = 18;

export function useSmoothScroll() {
  let scroll = $state(0);
  let progress = $state(0);
  let velocity = $state(0);
  let ready = $state(false);

  let currentScroll = 0;
  let targetScroll = 0;
  let rafId = 0;
  let resizeT: ReturnType<typeof setTimeout> | null = null;
  let wrapperEl: HTMLElement | null = null;
  let maxScroll = 0;
  let isTouching = false;
  let lastTouchY = 0;
  let lastTouchTime = 0;
  let touchVelocity = 0;
  let viewport = 0;

  function lerp(start: number, end: number, factor: number) {
    return start + (end - start) * factor;
  }

  function applyTransform() {
    if (!wrapperEl) return;
    wrapperEl.style.transform = `translate3d(0, ${-currentScroll}px, 0)`;
  }

  function updateState() {
    scroll = currentScroll;
    progress = maxScroll > 0 ? Math.min(1, Math.max(0, currentScroll / maxScroll)) : 0;
  }

  function measure() {
    if (!wrapperEl) return;
    viewport = window.innerHeight;
    maxScroll = Math.max(0, wrapperEl.scrollHeight - viewport);
    // Clamp target after resize
    targetScroll = Math.max(0, Math.min(targetScroll, maxScroll));
    applyTransform();
    updateState();
  }

  function scrollTo(y: number) {
    targetScroll = Math.max(0, Math.min(y, maxScroll));
  }

  function init() {
    wrapperEl = document.querySelector("#smooth-scroll") as HTMLElement | null;
    if (!wrapperEl) return;

    function animate() {
      const previousScroll = currentScroll;
      currentScroll = lerp(currentScroll, targetScroll, SMOOTH_FACTOR);
      velocity = currentScroll - previousScroll;
      scrollBus.setDelta(velocity);

      // Snap when close enough
      if (Math.abs(currentScroll - targetScroll) < 0.2) {
        currentScroll = targetScroll;
      }

      applyTransform();
      updateState();
      rafId = requestAnimationFrame(animate);
    }

    function onWheel(event: WheelEvent) {
      if (event.target instanceof Element && event.target.closest("[data-lenis-prevent]")) {
        return;
      }
      event.preventDefault();
      targetScroll = Math.max(0, Math.min(targetScroll + event.deltaY * WHEEL_MULTIPLIER, maxScroll));
    }

    function onTouchStart(event: TouchEvent) {
      isTouching = true;
      lastTouchY = event.touches[0].clientY;
      lastTouchTime = Date.now();
      touchVelocity = 0;
    }

    function onTouchMove(event: TouchEvent) {
      if (!isTouching) return;
      if (event.target instanceof Element && event.target.closest("[data-lenis-prevent]")) {
        return;
      }
      event.preventDefault();
      const nextY = event.touches[0].clientY;
      const delta = (lastTouchY - nextY) * TOUCH_MULTIPLIER;
      targetScroll = Math.max(0, Math.min(targetScroll + delta, maxScroll));

      const nextTime = Date.now();
      const timeDelta = nextTime - lastTouchTime;
      if (timeDelta > 0) touchVelocity = (delta / timeDelta) * TOUCH_INERTIA;
      lastTouchY = nextY;
      lastTouchTime = nextTime;
    }

    function onTouchEnd() {
      isTouching = false;
      targetScroll = Math.max(0, Math.min(targetScroll + touchVelocity * TOUCH_INERTIA, maxScroll));
    }

    measure();
    rafId = requestAnimationFrame(animate);

    const ro = new ResizeObserver(() => {
      if (resizeT) clearTimeout(resizeT);
      resizeT = setTimeout(measure, 80);
    });
    if (wrapperEl) ro.observe(wrapperEl);
    window.addEventListener("resize", measure);
    window.addEventListener("wheel", onWheel, { passive: false });
    window.addEventListener("touchstart", onTouchStart, { passive: true });
    window.addEventListener("touchmove", onTouchMove, { passive: false });
    window.addEventListener("touchend", onTouchEnd);

    ready = true;

    return () => {
      cancelAnimationFrame(rafId);
      scrollBus.setDelta(0);
      ro.disconnect();
      window.removeEventListener("resize", measure);
      window.removeEventListener("wheel", onWheel);
      window.removeEventListener("touchstart", onTouchStart);
      window.removeEventListener("touchmove", onTouchMove);
      window.removeEventListener("touchend", onTouchEnd);
    };
  }

  return {
    get scroll() { return scroll; },
    get progress() { return progress; },
    get velocity() { return velocity; },
    get ready() { return ready; },
    init,
    scrollTo
  };
}