export type ThemeMode = "light" | "dark";

export type ThemeProfile = {
  background: string;
  grainColor: string;
  grainOpacity: number;
};

export type SceneBackgroundParams = {
  displaceAmp: number;
  displaceSpeed: number;
  pulseAmp: number;
  pulseSpeed: number;
  pulseCount: number;
  pulseDriftSpeed: number;
  pulseWidth: number;
  pulseSharpness: number;
  pulseBulge: number;
  organicAmp: number;
  organicSpeed: number;
  organicFrequency: number;
  relaxation: number;
  swirl: number;
  meshColor: string;
  meshOpacity: number;
  meshWireframe: boolean;
  meshVisible: boolean;
  roughness: number;
  metalness: number;
  ambientIntensity: number;
  ambientColor: string;
  spotIntensity: number;
  spotColor: string;
  spotAngle: number;
  spotPenumbra: number;
  spotDecay: number;
  edgesVisible: boolean;
  edgeColor: string;
  edgeWidth: number;
  edgeOpacity: number;
  nodesVisible: boolean;
  nodeColor: string;
  nodeSize: number;
  nodeOpacity: number;
  fogEnabled: boolean;
  fogNear: number;
  fogFar: number;
  fogColor: string;
  fov: number;
  spotX: number;
  spotY: number;
  spotZ: number;
  rotationGain: number;
  wiggleAmp: number;
  wiggleFreq: number;
  wiggleSpeed: number;
  wiggleSeed: number;
  bevelEnabled: boolean;
  bevelStrength: number;
  bevelInset: number;
  cameraOffsetX: number;
  cameraOffsetY: number;
  cameraOffsetZ: number;
  cameraRollDeg: number;
};

type VisualThemeDefaults = {
  profile: ThemeProfile;
  background: SceneBackgroundParams;
};

const DARK_DEFAULTS: VisualThemeDefaults = {
  profile: {
    background: "#050505",
    grainColor: "#ffffff",
    grainOpacity: 0.006
  },
  background: {
    displaceAmp: 7,
    displaceSpeed: 0.3,
    pulseAmp: 1,
    pulseSpeed: 0.5,
    pulseCount: 4,
    pulseDriftSpeed: 1,
    pulseWidth: 5,
    pulseSharpness: 3,
    pulseBulge: 1,
    organicAmp: 1,
    organicSpeed: 2,
    organicFrequency: 0.5,
    relaxation: 0.5,
    swirl: 0,
    meshColor: "#a3a3a3",
    meshOpacity: 0.89,
    meshWireframe: false,
    meshVisible: true,
    roughness: 0.4,
    metalness: 0.3,
    ambientIntensity: 2.1,
    ambientColor: "#5a5a5a",
    spotIntensity: 260,
    spotColor: "#d6d6d6",
    spotAngle: 1.57,
    spotPenumbra: 1,
    spotDecay: 1.55,
    edgesVisible: true,
    edgeColor: "#3f3f3f",
    edgeWidth: 1,
    edgeOpacity: 0.15,
    nodesVisible: true,
    nodeColor: "#a0a0a0",
    nodeSize: 0.35,
    nodeOpacity: 0.2,
    fogEnabled: false,
    fogNear: 12.2,
    fogFar: 80,
    fogColor: "#050505",
    fov: 65,
    spotX: -0.6,
    spotY: 3.3,
    spotZ: 7.1,
    rotationGain: 0.003,
    wiggleAmp: 0.15,
    wiggleFreq: 4,
    wiggleSpeed: 1.5,
    wiggleSeed: 0,
    bevelEnabled: false,
    bevelStrength: 0.15,
    bevelInset: 0.18,
    cameraOffsetX: 0,
    cameraOffsetY: 0,
    cameraOffsetZ: 0,
    cameraRollDeg: 0
  }
};

const LIGHT_OVERRIDES = {
  profile: {
    background: "#f7f7f4",
    grainColor: "#0a0a0a",
    grainOpacity: 0.003
  },
  background: {
    meshColor: "#ffffff",
    meshOpacity: 0.75,
    ambientIntensity: 1.35,
    ambientColor: "#f5f5f0",
    spotIntensity: 95,
    spotColor: "#ffffff",
    edgeColor: "#2a2a27",
    edgeOpacity: 0.15,
    nodeOpacity: 0.15,
    fogColor: "#f4f2ed"
  }
} satisfies {
  profile: ThemeProfile;
  background: Partial<SceneBackgroundParams>;
};

function createVisualDefaults(overrides?: typeof LIGHT_OVERRIDES): VisualThemeDefaults {
  return {
    profile: { ...DARK_DEFAULTS.profile, ...overrides?.profile },
    background: { ...DARK_DEFAULTS.background, ...overrides?.background }
  };
}

export const VISUAL_DEFAULTS: Record<ThemeMode, VisualThemeDefaults> = {
  light: createVisualDefaults(LIGHT_OVERRIDES),
  dark: createVisualDefaults()
};

export const THEME_PROFILE: Record<ThemeMode, ThemeProfile> = {
  light: VISUAL_DEFAULTS.light.profile,
  dark: VISUAL_DEFAULTS.dark.profile
};

export function getDefaultSceneBackgroundParams(theme: ThemeMode): SceneBackgroundParams {
  return { ...VISUAL_DEFAULTS[theme].background };
}

export function applyThemeProfile(params: SceneBackgroundParams, nextTheme: ThemeMode): void {
  Object.assign(params, getDefaultSceneBackgroundParams(nextTheme));
}