/**
 * v1.2 Phosphor Scope sound engine. Pure WebAudio synthesis — zero audio assets.
 *
 * Singleton. The AudioContext is created ONLY inside unlockSound(), which is
 * invoked from real user gestures on the landing page. Cues stay silent until
 * the browser permits playback; audio never gates a UI action.
 */
import { v12Effects } from "$lib/state/v12-effects.svelte"

export type KeystrokeKind = "char" | "space" | "enter"

declare global {
  interface Window {
    webkitAudioContext?: new (contextOptions?: AudioContextOptions) => AudioContext
  }
}

let ctx: AudioContext | null = null
let master: GainNode | null = null
let noiseBuffer: AudioBuffer | null = null
let lastHoverAt = 0
let lastScrubAt = 0

function audio(): { ctx: AudioContext; master: GainNode } | null {
  if (!v12Effects.sound || !ctx || !master || ctx.state !== "running" || document.hidden) {
    return null
  }
  return { ctx, master }
}

function jitter(base: number, spread: number): number {
  return base * (1 + (Math.random() * 2 - 1) * spread)
}

/** Create or resume the AudioContext from a user gesture. Safe to call repeatedly. */
export function unlockSound(onReady?: () => void): void {
  if (!v12Effects.sound) return
  try {
    if (!ctx) {
      const AudioCtor = window.AudioContext ?? window.webkitAudioContext
      if (!AudioCtor) return
      ctx = new AudioCtor()
      const compressor = ctx.createDynamicsCompressor()
      compressor.threshold.value = -18
      master = ctx.createGain()
      master.gain.value = 0.7
      master.connect(compressor)
      compressor.connect(ctx.destination)

      const length = Math.floor(ctx.sampleRate * 0.5)
      noiseBuffer = ctx.createBuffer(1, length, ctx.sampleRate)
      const data = noiseBuffer.getChannelData(0)
      for (let i = 0; i < length; i += 1) {
        data[i] = Math.random() * 2 - 1
      }
    }
    if (ctx.state !== "running") {
      void ctx
        .resume()
        .then(() => onReady?.())
        .catch(() => {})
    } else {
      onReady?.()
    }
  } catch {
    ctx = null
    master = null
  }
}

/** Suspend the engine when sound or FX is switched off. */
export function silenceSound(): void {
  if (ctx && ctx.state !== "closed") {
    void ctx.suspend().catch(() => {})
  }
}

interface ToneOptions {
  type: OscillatorType
  freq: number
  attackMs: number
  holdMs?: number
  decayMs: number
  peak: number
  lowpassHz?: number
  endFreq?: number
  endMs?: number
  delayMs?: number
}

interface NoiseBurstOptions {
  holdMs: number
  peak: number
  filterType: BiquadFilterType
  filterHz: number
  decayMs?: number
  q?: number
  delayMs?: number
}

function env(gain: AudioParam, t0: number, attackMs: number, holdMs: number, decayMs: number, peak: number): void {
  const attackEnd = t0 + attackMs / 1000
  gain.setValueAtTime(0.0001, t0)
  gain.linearRampToValueAtTime(peak, attackEnd)
  if (holdMs > 0) gain.setValueAtTime(peak, attackEnd + holdMs / 1000)
  gain.exponentialRampToValueAtTime(0.0001, attackEnd + holdMs / 1000 + decayMs / 1000)
}

function tone(options: ToneOptions): void {
  const a = audio()
  if (!a) return
  const t0 = a.ctx.currentTime + (options.delayMs ?? 0) / 1000
  try {
    const osc = a.ctx.createOscillator()
    osc.type = options.type
    osc.frequency.setValueAtTime(options.freq, t0)
    if (options.endFreq && options.endMs) {
      osc.frequency.exponentialRampToValueAtTime(options.endFreq, t0 + options.endMs / 1000)
    }
    const gain = a.ctx.createGain()
    env(gain.gain, t0, options.attackMs, options.holdMs ?? 0, options.decayMs, options.peak)
    let node: AudioNode = osc
    if (options.lowpassHz) {
      const filter = a.ctx.createBiquadFilter()
      filter.type = "lowpass"
      filter.frequency.value = options.lowpassHz
      node.connect(filter)
      node = filter
    }
    node.connect(gain)
    gain.connect(a.master)
    osc.start(t0)
    osc.stop(t0 + (options.attackMs + (options.holdMs ?? 0) + options.decayMs + 40) / 1000)
  } catch {
    // Audio must never break the page.
  }
}

function noiseBurst(options: NoiseBurstOptions): void {
  const a = audio()
  if (!a || !noiseBuffer) return
  const decayMs = options.decayMs ?? 30
  const q = options.q ?? 1
  const t0 = a.ctx.currentTime + (options.delayMs ?? 0) / 1000
  try {
    const source = a.ctx.createBufferSource()
    source.buffer = noiseBuffer
    const filter = a.ctx.createBiquadFilter()
    filter.type = options.filterType
    filter.Q.value = q
    filter.frequency.value = options.filterHz
    const gain = a.ctx.createGain()
    env(gain.gain, t0, 1, options.holdMs, decayMs, options.peak)
    source.connect(filter)
    filter.connect(gain)
    gain.connect(a.master)
    source.start(t0)
    source.stop(t0 + (options.holdMs + decayMs + 5) / 1000)
  } catch {
    // Audio must never break the page.
  }
}

/** Synthesized mechanical/terminal keyboard keystroke for the intro prompt. */
export function cueKeystroke(kind: KeystrokeKind = "char"): void {
  if (kind === "enter") {
    noiseBurst({ holdMs: 0, peak: 0.058, filterType: "bandpass", filterHz: 2350, decayMs: 17, q: 2.0 })
    tone({ type: "triangle", freq: 225, endFreq: 66, endMs: 28, attackMs: 1, decayMs: 28, peak: 0.075 })
    noiseBurst({ holdMs: 0, peak: 0.024, filterType: "bandpass", filterHz: 3450, decayMs: 9, q: 2.5, delayMs: 18 })
    return
  }
  if (kind === "space") {
    noiseBurst({ holdMs: 0, peak: 0.048, filterType: "bandpass", filterHz: jitter(1650, 0.08), decayMs: 22, q: 1.6 })
    tone({ type: "triangle", freq: jitter(180, 0.08), endFreq: 68, endMs: 24, attackMs: 1, decayMs: 24, peak: 0.068 })
    return
  }
  noiseBurst({ holdMs: 0, peak: 0.042, filterType: "bandpass", filterHz: jitter(3150, 0.12), decayMs: 13, q: 2.2 })
  tone({
    type: "triangle",
    freq: jitter(270, 0.12),
    endFreq: jitter(105, 0.1),
    endMs: 16,
    attackMs: 1,
    decayMs: 16,
    peak: 0.05,
  })
}

/** Soft CRT beam collapse when the intro veil lifts. */
export function cueReveal(): void {
  tone({ type: "sine", freq: 210, endFreq: 64, endMs: 280, attackMs: 4, decayMs: 280, peak: 0.095 })
  noiseBurst({ holdMs: 0, peak: 0.075, filterType: "lowpass", filterHz: 480, decayMs: 110 })
}

/** Row hover/focus and dialog paging. Pitch carries sentiment (-100...+100). */
export function cueHover(sentiment: number): void {
  const now = Date.now()
  if (now - lastHoverAt < 45) return
  lastHoverAt = now
  tone({ type: "triangle", freq: 520 + 2.2 * sentiment, attackMs: 2, decayMs: 28, peak: 0.02 })
}

/** Scope cursor crossing a recorded week. */
export function cueScrub(): void {
  const now = Date.now()
  if (now - lastScrubAt < 32) return
  lastScrubAt = now
  tone({ type: "sine", freq: 1600, attackMs: 1, decayMs: 9, peak: 0.014 })
}

/** FX/SOUND switches, range pills, filters, and pager buttons. */
export function cueToggle(): void {
  noiseBurst({ holdMs: 4, peak: 0.05, filterType: "highpass", filterHz: 2000 })
}

/** Story inspection dialog open/close. */
export function cueSheet(open: boolean): void {
  tone({
    type: "sine",
    freq: open ? 220 : 330,
    endFreq: open ? 330 : 196,
    endMs: 70,
    attackMs: 4,
    decayMs: 70,
    peak: open ? 0.03 : 0.025,
  })
  noiseBurst({ holdMs: 2, peak: 0.02, filterType: "highpass", filterHz: 3000 })
}
