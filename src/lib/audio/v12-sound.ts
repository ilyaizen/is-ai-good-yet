/**
 * v1.2 phosphor sound engine. Pure WebAudio synthesis — zero audio assets.
 *
 * Singleton. The AudioContext is created ONLY inside unlock(), which the
 * SOUND control calls from a real user click (autoplay policy). Every cue is
 * a no-op unless sound is on AND FX is on, and every cue is failure-isolated
 * so audio can never break the page.
 *
 * Cue parameters follow the v1.2 direction memo (Phosphor Boot).
 */
import { v12Effects } from "$lib/state/v12-effects.svelte"

type Answer = "YES" | "NOT YET" | "NO"
export type { Answer }

let ctx: AudioContext | null = null
let master: GainNode | null = null
let noiseBuffer: AudioBuffer | null = null
let lastHoverAt = 0
let lastScrubAt = 0

function audio(): { ctx: AudioContext; master: GainNode } | null {
  if (!v12Effects.sound || !v12Effects.fx || !ctx || !master) return null
  return { ctx, master }
}

/** Create the AudioContext from a user gesture. Safe to call repeatedly. */
export function unlockSound(): void {
  if (!v12Effects.fx) return
  try {
    if (!ctx) {
      const AudioCtor =
        window.AudioContext ??
        (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
      if (!AudioCtor) return
      ctx = new AudioCtor()
      const compressor = ctx.createDynamicsCompressor()
      compressor.threshold.value = -18
      master = ctx.createGain()
      master.gain.value = 0.9
      master.connect(compressor)
      compressor.connect(ctx.destination)

      const length = Math.floor(ctx.sampleRate * 0.5)
      noiseBuffer = ctx.createBuffer(1, length, ctx.sampleRate)
      const data = noiseBuffer.getChannelData(0)
      for (let i = 0; i < length; i += 1) {
        data[i] = Math.random() * 2 - 1
      }
    }
    if (ctx.state === "suspended") void ctx.resume()
  } catch {
    ctx = null
    master = null
  }
}

/** Sync the engine when sound is switched off. */
export function silenceSound(): void {
  if (ctx && ctx.state === "running") void ctx.suspend()
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

function env(gain: AudioParam, t0: number, attackMs: number, holdMs: number, decayMs: number, peak: number): void {
  const attackEnd = t0 + attackMs / 1000
  gain.setValueAtTime(0.0001, t0)
  gain.linearRampToValueAtTime(peak, attackEnd)
  if (holdMs > 0) gain.setValueAtTime(peak, attackEnd + holdMs / 1000)
  gain.exponentialRampToValueAtTime(0.0001, attackEnd + holdMs / 1000 + decayMs / 1000)
}

function noiseBurst(holdMs: number, peak: number, filterType: BiquadFilterType, filterHz: number): void {
  const a = audio()
  if (!a || !noiseBuffer) return
  try {
    const source = a.ctx.createBufferSource()
    source.buffer = noiseBuffer
    const filter = a.ctx.createBiquadFilter()
    filter.type = filterType
    filter.frequency.value = filterHz
    const gain = a.ctx.createGain()
    const t0 = a.ctx.currentTime
    env(gain.gain, t0, 2, holdMs, 30, peak)
    source.connect(filter)
    filter.connect(gain)
    gain.connect(a.master)
    source.start(t0)
    source.stop(t0 + (holdMs + 60) / 1000)
  } catch {
    // Audio must never break the page.
  }
}

/** Each boot/loader line and each typed verdict char. lineIndex steps the pitch. */
export function cueTick(lineIndex = 0): void {
  tone({
    type: "square",
    freq: 2100 + ((lineIndex % 8) * 40),
    attackMs: 1,
    decayMs: 14,
    peak: 0.022,
  })
}

/** Device probe answers ok. */
export function cueProbe(): void {
  tone({ type: "square", freq: 1320, attackMs: 2, decayMs: 40, peak: 0.018, lowpassHz: 3500 })
}

/** /dev/hype optimism cache … FAIL */
export function cueFail(): void {
  tone({ type: "square", freq: 220, attackMs: 2, holdMs: 50, decayMs: 60, peak: 0.03, lowpassHz: 1200 })
}

/** Single POST beep once all probes resolve. */
export function cuePost(): void {
  tone({ type: "square", freq: 1000, attackMs: 4, holdMs: 120, decayMs: 50, peak: 0.032, lowpassHz: 3000 })
}

/** Veil-lift gesture: low sine sweep + a breath of lowpassed noise. */
export function cueReveal(): void {
  tone({ type: "sine", freq: 140, endFreq: 42, endMs: 380, attackMs: 5, decayMs: 380, peak: 0.09 })
  noiseBurst(200, 0.035, "lowpass", 900)
}

/** Verdict printed. Pitch direction carries the answer; ×0.7 on the scope. */
export function cueStinger(answer: Answer, quiet = false): void {
  const scale = quiet ? 0.7 : 1
  if (answer === "YES") {
    tone({ type: "square", freq: 440, attackMs: 10, decayMs: 140, peak: 0.045 * scale, lowpassHz: 1800 })
    tone({ type: "square", freq: 659.25, attackMs: 10, decayMs: 200, peak: 0.045 * scale, lowpassHz: 1800, delayMs: 180 })
  } else if (answer === "NO") {
    tone({ type: "square", freq: 329.63, attackMs: 10, decayMs: 140, peak: 0.045 * scale, lowpassHz: 1800 })
    tone({ type: "square", freq: 246.94, attackMs: 10, decayMs: 200, peak: 0.045 * scale, lowpassHz: 1800, delayMs: 180 })
  } else {
    tone({ type: "square", freq: 587.33, attackMs: 10, decayMs: 140, peak: 0.045 * scale, lowpassHz: 1800 })
    tone({ type: "square", freq: 440, attackMs: 10, decayMs: 200, peak: 0.045 * scale, lowpassHz: 1800, delayMs: 180 })
  }
}

/** Row hover/focus and sheet paging. Pitch carries sentiment (−100…+100). */
export function cueHover(sentiment: number): void {
  const now = Date.now()
  if (now - lastHoverAt < 45) return
  lastHoverAt = now
  tone({ type: "triangle", freq: 520 + 2.2 * sentiment, attackMs: 2, decayMs: 28, peak: 0.02 })
}

/** Scope cursor crossing a day. */
export function cueScrub(): void {
  const now = Date.now()
  if (now - lastScrubAt < 32) return
  lastScrubAt = now
  tone({ type: "sine", freq: 1600, attackMs: 1, decayMs: 9, peak: 0.014 })
}

/** FX/SOUND toggles, chips, notable-day buttons. */
export function cueToggle(): void {
  noiseBurst(4, 0.05, "highpass", 2000)
}

/** Details sheet open/close. */
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
  noiseBurst(2, 0.02, "highpass", 3000)
}
