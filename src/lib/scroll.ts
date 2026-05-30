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

  lenis.on("scroll", ({ scroll }: { scroll: number }) => {
    scrollPosition.set(scroll);
  });

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

/** Scroll to a pixel offset — Lenis if available, native fallback */
export function scrollTo(y: number) {
  if (lenis) {
    lenis.scrollTo(y, { immediate: false });
  } else {
    window.scrollTo({ top: y });
  }
}

/** Scroll to top — Lenis if available, native fallback */
export function scrollToTop(options: { onComplete?: () => void } = {}) {
  if (lenis) {
    lenis.scrollTo(0, { onComplete: options.onComplete });
  } else {
    window.scrollTo({ top: 0 });
    options.onComplete?.();
  }
}

/** Scroll to bottom — Lenis if available, native fallback */
export function scrollToBottom(options: { onComplete?: () => void; duration?: number } = {}) {
  if (lenis) {
    const docHeight = Math.max(
      document.body.scrollHeight,
      document.documentElement.scrollHeight
    );
    lenis.scrollTo(docHeight - window.innerHeight, {
      onComplete: options.onComplete,
    });
  } else {
    const docHeight = Math.max(
      document.body.scrollHeight,
      document.documentElement.scrollHeight
    );
    window.scrollTo({ top: docHeight - window.innerHeight });
    options.onComplete?.();
  }
}

/** Scroll to an element — Lenis if available, native fallback */
export function scrollToElement(el: HTMLElement) {
  if (lenis) {
    lenis.scrollTo(el);
  } else {
    el.scrollIntoView();
  }
}

/** Scroll to an element by ID — Lenis if available, native fallback */
export function scrollToId(id: string) {
  if (typeof document === "undefined") return;
  const hash = id.includes("#") ? id.slice(id.indexOf("#") + 1) : id;
  const el = document.getElementById(hash.replace(/^#/, ""));
  if (el) scrollToElement(el);
}

/** Anchor click handler — Lenis if available, native fallback */
export function handleAnchorClick(e: MouseEvent, href: string) {
  if (typeof window === "undefined") return;

  const target = new URL(href, window.location.href);
  if (!target.hash) return;

  const isSamePage = target.pathname === window.location.pathname;
  if (!isSamePage) return;

  e.preventDefault();
  scrollToId(target.hash);
}

/** Destroy the Lenis instance */
export function destroyLenis() {
  if (lenis) {
    lenis.destroy();
    lenis = null;
  }
}
