import { writable } from "svelte/store"

// Absolute scroll position in pixels (from Lenis). Single source of truth.
// Drives sphere rotation as a pure function of position — no delta accumulation,
// so programmatic jumps (scrollbar drag) snap instead of spinning the scene.
export const scrollPosition = writable(0)
