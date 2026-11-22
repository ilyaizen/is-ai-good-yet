/**
 * v1.2 effects toggle: master FX switch + session sound switch.
 *
 * - `fx` persists in localStorage ("v12.fx") and is applied pre-paint by the
 *   inline bootstrap in app.html (adds `fx-off` to <html> before first paint),
 *   so a returning effects-off visitor never sees the intro, flicker, or glow.
 * - `sound` is deliberately session-only: OFF on every load (autoplay policy),
 *   and the AudioContext is only creatable from a real user gesture.
 * - `prefers-reduced-motion` is tracked live and always respected, independent
 *   of the FX switch.
 */
import { browser } from "$app/environment"

const FX_KEY = "v12.fx"

class V12Effects {
  fx = $state(true)
  sound = $state(false)
  reducedMotion = $state(false)
  private initialized = false

  /** Typewriters, dialog slide, intro collapse. */
  get motionOK(): boolean {
    return this.fx && !this.reducedMotion
  }

  /** Scanlines, flicker, vignette, caret blink, verdict glow. */
  get ambientOK(): boolean {
    return this.fx && !this.reducedMotion
  }

  init(): void {
    if (!browser || this.initialized) return
    this.initialized = true
    try {
      this.fx = localStorage.getItem(FX_KEY) !== "off"
    } catch {
      this.fx = true
    }
    const media = window.matchMedia("(prefers-reduced-motion: reduce)")
    this.reducedMotion = media.matches
    this.applyDocumentClass()
    media.addEventListener("change", (event) => {
      this.reducedMotion = event.matches
    })
  }

  setFx(on: boolean): void {
    this.fx = on
    try {
      localStorage.setItem(FX_KEY, on ? "on" : "off")
    } catch {
      // Private mode: fall back to session-only state.
    }
    this.applyDocumentClass()
    if (!on) {
      this.sound = false
      if (browser) {
        document.documentElement.classList.remove("v12-veil-pending")
      }
    }
  }

  setSound(on: boolean): void {
    this.sound = on && this.fx
  }

  private applyDocumentClass(): void {
    if (!browser) return
    document.documentElement.classList.toggle("fx-off", !this.fx)
  }
}

export const v12Effects = new V12Effects()
