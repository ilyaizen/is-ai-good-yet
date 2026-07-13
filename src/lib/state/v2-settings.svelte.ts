import type { V2Dimension } from "$lib/types/v2";

export type V2TimeWindow = "24h" | "7d" | "30d" | "90d" | "12m" | "all";
export type V2Density = "compact" | "comfortable" | "expanded";
export type V2Sort = "newest" | "influence" | "divergence" | "polarization";

export interface V2Settings {
  version: 1;
  dimensions: Record<V2Dimension, boolean>;
  timeWindow: V2TimeWindow;
  scoreMin: number;
  scoreMax: number;
  confidenceMin: number;
  conflictsOnly: boolean;
  density: V2Density;
  sort: V2Sort;
  previewImages: boolean;
  scanlineOpacity: number;
  vignetteStrength: number;
  grainOpacity: number;
  ambientMotion: boolean;
}

export const V2_SETTINGS_KEY = "is-ai-good-yet:v2:settings:1";

const DEFAULTS: V2Settings = {
  version: 1,
  dimensions: { capability: true, trajectory: true, impact: true },
  timeWindow: "7d",
  scoreMin: -2,
  scoreMax: 2,
  confidenceMin: 0,
  conflictsOnly: false,
  density: "comfortable",
  sort: "newest",
  previewImages: true,
  scanlineOpacity: 0.055,
  vignetteStrength: 0.16,
  grainOpacity: 0.025,
  ambientMotion: true
};

const clamp = (value: unknown, min: number, max: number, fallback: number): number =>
  typeof value === "number" && Number.isFinite(value) ? Math.min(max, Math.max(min, value)) : fallback;

export function defaultV2Settings(): V2Settings {
  return structuredClone(DEFAULTS);
}

export function parseV2Settings(value: unknown): V2Settings {
  if (!value || typeof value !== "object") return defaultV2Settings();
  const raw = value as Partial<V2Settings>;
  const dimensions = raw.dimensions ?? DEFAULTS.dimensions;
  const timeWindows: V2TimeWindow[] = ["24h", "7d", "30d", "90d", "12m", "all"];
  const densities: V2Density[] = ["compact", "comfortable", "expanded"];
  const sorts: V2Sort[] = ["newest", "influence", "divergence", "polarization"];
  return {
    version: 1,
    dimensions: {
      capability: typeof dimensions.capability === "boolean" ? dimensions.capability : true,
      trajectory: typeof dimensions.trajectory === "boolean" ? dimensions.trajectory : true,
      impact: typeof dimensions.impact === "boolean" ? dimensions.impact : true
    },
    timeWindow: timeWindows.includes(raw.timeWindow as V2TimeWindow) ? raw.timeWindow as V2TimeWindow : DEFAULTS.timeWindow,
    scoreMin: clamp(raw.scoreMin, -2, 2, DEFAULTS.scoreMin),
    scoreMax: clamp(raw.scoreMax, -2, 2, DEFAULTS.scoreMax),
    confidenceMin: clamp(raw.confidenceMin, 0, 1, DEFAULTS.confidenceMin),
    conflictsOnly: typeof raw.conflictsOnly === "boolean" ? raw.conflictsOnly : false,
    density: densities.includes(raw.density as V2Density) ? raw.density as V2Density : DEFAULTS.density,
    sort: sorts.includes(raw.sort as V2Sort) ? raw.sort as V2Sort : DEFAULTS.sort,
    previewImages: typeof raw.previewImages === "boolean" ? raw.previewImages : true,
    scanlineOpacity: clamp(raw.scanlineOpacity, 0, 0.16, DEFAULTS.scanlineOpacity),
    vignetteStrength: clamp(raw.vignetteStrength, 0, 0.3, DEFAULTS.vignetteStrength),
    grainOpacity: clamp(raw.grainOpacity, 0, 0.1, DEFAULTS.grainOpacity),
    ambientMotion: typeof raw.ambientMotion === "boolean" ? raw.ambientMotion : true
  };
}

export function applyV2VisualSettings(root: HTMLElement, settings: V2Settings): void {
  root.style.setProperty("--v2-scanline-opacity", `${settings.scanlineOpacity * 100}%`);
  root.style.setProperty("--v2-vignette-opacity", `${settings.vignetteStrength * 100}%`);
  root.style.setProperty("--v2-grain-opacity", String(settings.grainOpacity));
  root.dataset.motion = settings.ambientMotion ? "on" : "off";
  root.dataset.density = settings.density;
}
