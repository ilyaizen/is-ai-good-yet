import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import { onDestroy } from "svelte"
import type { Snippet } from "svelte"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export type WithElementRef<T, E extends HTMLElement = HTMLElement> = T & {
  ref?: E | null
}

// Types needed by shadcn-svelte components
export type WithoutChild<T> = Omit<T, "child">
export type WithoutChildren<T> = Omit<T, "children">
export type WithoutChildrenOrChild<T> = Omit<T, "children" | "child">
export type WithChildren<T> = T & { children?: Snippet }

// IsMobile utility class for responsive components
export class IsMobile {
  current = $state(false)
  #mediaQuery: MediaQueryList | null = null

  constructor() {
    this.#mediaQuery = window.matchMedia("(max-width: 768px)")
    this.current = this.#mediaQuery.matches
    this.#mediaQuery.addEventListener("change", this.#handleMediaQueryChange)
    onDestroy(() => {
      this.#mediaQuery?.removeEventListener("change", this.#handleMediaQueryChange)
    })
  }

  #handleMediaQueryChange = (e: MediaQueryListEvent) => {
    this.current = e.matches
  }
}
