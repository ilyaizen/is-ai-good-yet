import Lenis from "@studio-freight/lenis";
import { scrollPosition } from "$lib/composables/scrollStore";

let lenis: Lenis | null = null;

export function initLenis(): Lenis {
  lenis = new Lenis({
    duration: 2.0,
    easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    orientation: "vertical" as const,
    gestureOrientation: "vertical" as const,
    smoothWheel: true,
    wheelMultiplier: 0.6,
    touchMultiplier: 1.5,
  });

  // Publish absolute scroll position (DRY) — consumed by the 3D scene to drive
  // rotation as a pure function of position, so drag jumps don't spin the scene.
  lenis.on("scroll", ({ scroll }: { scroll: number }) => {
    scrollPosition.set(scroll);
  });

  // Lenis 1.0.x has no autoRaf — must drive it manually or nothing scrolls.
  function raf(time: number) {
    lenis?.raf(time);
    requestAnimationFrame(raf);
  }
  requestAnimationFrame(raf);

  return lenis;
}

export function getLenis(): Lenis | null {
  return lenis;
}

/** Scroll to a pixel offset */
export function scrollTo(y: number) {
  if (!lenis) return;
  lenis.scrollTo(y, { immediate: false });
}

/** Scroll to top */
export function scrollToTop(options: { onComplete?: () => void } = {}) {
  if (!lenis) return;
  lenis.scrollTo(0, { onComplete: options.onComplete });
}

/** Scroll to bottom */
export function scrollToBottom(options: { onComplete?: () => void } = {}) {
  if (!lenis || typeof document === "undefined") return;
  const docHeight = Math.max(
    document.body.scrollHeight,
    document.documentElement.scrollHeight
  );
  lenis.scrollTo(docHeight - window.innerHeight, {
    onComplete: options.onComplete,
  });
}

/** Scroll to an element */
export function scrollToElement(el: HTMLElement) {
  if (!lenis) return;
  lenis.scrollTo(el);
}

/** Scroll to an element by ID */
export function scrollToId(id: string) {
  if (typeof document === "undefined") return;
  const el = document.getElementById(id.replace(/^#/, ""));
  if (el) scrollToElement(el);
}

/** Anchor click handler */
export function handleAnchorClick(e: MouseEvent, hash: string) {
  e.preventDefault();
  const id = hash.replace(/^#/, "");

  if (typeof window !== "undefined" && window.location.pathname !== "/") {
    window.location.href = "/#" + id;
    return;
  }

  scrollToId(id);
}

/** Destroy the Lenis instance */
export function destroyLenis() {
  if (lenis) {
    lenis.destroy();
    lenis = null;
  }
}
