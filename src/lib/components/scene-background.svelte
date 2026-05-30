<script lang="ts">
  import { T, useTask, useThrelte } from "@threlte/core";
  import { onMount, onDestroy, untrack } from "svelte";
  import * as THREE from "three";
  import { LineSegments2 } from "three/examples/jsm/lines/LineSegments2.js";
  import { LineSegmentsGeometry } from "three/examples/jsm/lines/LineSegmentsGeometry.js";
  import { LineMaterial } from "three/examples/jsm/lines/LineMaterial.js";
  import {
    DISPLACEMENT_AMP_MAX,
    RELAXATION_PASSES,
    SPHERE_RADIUS,
    clamp,
    createMembraneMeshData,
    lerp,
    smoothNoise2d
  } from "$lib/scene-background/membrane";
  import {
    getDefaultSceneBackgroundParams,
    applyThemeProfile,
    THEME_PROFILE,
    type ThemeMode,
    type SceneBackgroundParams
  } from "$lib/scene-background/defaults";
  import { scrollPosition } from "$lib/composables/scrollStore";
  import { pointerBus } from "$lib/composables/pointer-bus.svelte";
  import { pageActivity } from "$lib/composables/page-activity.svelte";

  interface Props {
    opacity?: number;
    theme?: ThemeMode;
    maxFps?: number;
    maxDpr?: number;
    suspendWhenHidden?: boolean;
  }

  let {
    opacity = 1,
    theme = "dark",
    maxFps = 60,
    maxDpr = 2,
    suspendWhenHidden = true
  }: Props = $props();

  const RADIUS = SPHERE_RADIUS;
  const MAX_PULSE_COUNT = 8;

  const params: SceneBackgroundParams = untrack(() => getDefaultSceneBackgroundParams(theme));

  let membraneGeo: THREE.BufferGeometry;
  let baseDirections: Float32Array;
  let edgePairs: Array<[number, number]>;
  let vertexNeighbors: ReturnType<typeof createMembraneMeshData>["vertexNeighbors"];
  let vertexInfluence: Float32Array;
  let posAttr: THREE.BufferAttribute | THREE.InterleavedBufferAttribute;
  let normalAttr: THREE.BufferAttribute | THREE.InterleavedBufferAttribute;
  let vertCount = 0;
  let baseHeight: Float32Array;
  let rawHeight: Float32Array;
  let relaxedHeight: Float32Array;
  let relaxScratch: Float32Array;
  let phaseA: Float32Array;
  let phaseB: Float32Array;
  let ampScale: Float32Array;
  let freqScale: Float32Array;
  let edgePosArr: Float32Array;
  let nodePosArr: Float32Array;
  const nodeGeo = new THREE.BufferGeometry();
  const edgeGeo = new LineSegmentsGeometry();

  function buildMembraneState(geo: ReturnType<typeof createMembraneMeshData>) {
    membraneGeo = geo.membraneGeo;
    baseDirections = geo.baseDirections;
    edgePairs = geo.edgePairs;
    vertexNeighbors = geo.vertexNeighbors;
    vertexInfluence = geo.vertexInfluence;
    posAttr = membraneGeo.attributes.position as THREE.BufferAttribute;
    normalAttr = membraneGeo.attributes.normal as THREE.BufferAttribute;
    vertCount = posAttr.count;

    baseHeight = new Float32Array(vertCount);
    rawHeight = new Float32Array(vertCount);
    relaxedHeight = new Float32Array(vertCount);
    relaxScratch = new Float32Array(vertCount);
    phaseA = new Float32Array(vertCount);
    phaseB = new Float32Array(vertCount);
    ampScale = new Float32Array(vertCount);
    freqScale = new Float32Array(vertCount);

    for (let i = 0; i < vertCount; i++) {
      const nx = baseDirections[i * 3];
      const ny = baseDirections[i * 3 + 1];
      const nz = baseDirections[i * 3 + 2];
      const sx = nx * RADIUS;
      const sy = ny * RADIUS;
      const sz = nz * RADIUS;
      const ampNoise = smoothNoise2d(sx * 0.06 + sz * 0.04 + 17.3, sy * 0.06 - 9.1);
      const phaseNoiseA = smoothNoise2d(sx * 0.045 - 3.4, sy * 0.045 + sz * 0.03 + 22.8);
      const phaseNoiseB = smoothNoise2d(sx * 0.05 + sz * 0.02 + 31.2, sy * 0.05 - 15.7);

      phaseA[i] = phaseNoiseA * Math.PI * 2;
      phaseB[i] = phaseNoiseB * Math.PI * 2;
      ampScale[i] = 0.72 + ampNoise * 0.95;
      freqScale[i] = 0.74 + smoothNoise2d(sx * 0.04 - 11.1, sy * 0.04 + sz * 0.025 + 8.6) * 0.66;
    }

    edgePosArr = new Float32Array(edgePairs.length * 6);
    nodePosArr = new Float32Array(vertCount * 3);
    nodeGeo.setAttribute("position", new THREE.BufferAttribute(nodePosArr, 3));
    edgeGeo.setPositions(edgePosArr);
  }

  buildMembraneState(createMembraneMeshData());

  function relaxDisplacement(input: Float32Array, output: Float32Array, amp: number) {
    const ampRatio = clamp(amp / DISPLACEMENT_AMP_MAX, 0, 1);
    const coupling = lerp(0.02, 0.52, clamp(params.relaxation, 0, 1)) * lerp(0.72, 1.12, ampRatio);

    relaxScratch.set(input);
    for (let pass = 0; pass < RELAXATION_PASSES; pass++) {
      for (let i = 0; i < vertCount; i++) {
        const neighbors = vertexNeighbors[i];

        if (neighbors.length === 0) {
          output[i] = relaxScratch[i];
          continue;
        }

        let weightedHeight = relaxScratch[i] * 0.42;
        let weightTotal = 0.42;

        for (const neighbor of neighbors) {
          weightedHeight += relaxScratch[neighbor.index] * neighbor.weight;
          weightTotal += neighbor.weight;
        }

        const neighborAverage = weightedHeight / weightTotal;
        const localCoupling = clamp(coupling * vertexInfluence[i], 0.01, 0.58);
        output[i] = lerp(relaxScratch[i], neighborAverage, localCoupling);
      }

      if (pass < RELAXATION_PASSES - 1) {
        relaxScratch.set(output);
      }
    }
  }

  type Pulse = {
    pos: THREE.Vector3;
    axis: THREE.Vector3;
    omega: number;
    freq: number;
    amp: number;
    phase: number;
  };

  function randomUnitVector(target: THREE.Vector3) {
    const u = Math.random() * 2 - 1;
    const phi = Math.random() * Math.PI * 2;
    const r = Math.sqrt(Math.max(0, 1 - u * u));
    target.set(r * Math.cos(phi), u, r * Math.sin(phi));
  }

  const pulses: Pulse[] = Array.from({ length: MAX_PULSE_COUNT }, () => {
    const pos = new THREE.Vector3();
    const axis = new THREE.Vector3();
    randomUnitVector(pos);
    randomUnitVector(axis);
    return {
      pos,
      axis,
      omega: (Math.random() - 0.5) * 0.28,
      freq: 0.42 + Math.random() * 0.38,
      amp: 0.75 + Math.random() * 0.65,
      phase: Math.random() * Math.PI * 2
    };
  });

  const backdropGeo = new THREE.PlaneGeometry(2, 2);
  const backdropMat = new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uBaseColor: { value: new THREE.Color(THEME_PROFILE.dark.background) },
      uGrainColor: { value: new THREE.Color(THEME_PROFILE.dark.grainColor) },
      uGrainOpacity: { value: THEME_PROFILE.dark.grainOpacity },
      uResolution: { value: new THREE.Vector2(1, 1) }
    },
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform float uTime;
      uniform vec3 uBaseColor;
      uniform vec3 uGrainColor;
      uniform float uGrainOpacity;
      uniform vec2 uResolution;
      varying vec2 vUv;

      float hash(vec2 p) {
        vec3 p3 = fract(vec3(p.xyx) * 0.1031);
        p3 += dot(p3, p3.yzx + 33.33);
        return fract((p3.x + p3.y) * p3.z);
      }

      void main() {
        vec2 pixel = floor(vUv * uResolution * 8.0);
        float grain = hash(pixel + floor(uTime * 12.0));
        vec3 color = mix(uBaseColor, uGrainColor, grain * uGrainOpacity);
        gl_FragColor = vec4(color, 1.0);
      }
    `,
    depthTest: false,
    depthWrite: false,
    fog: false
  });

  const edgeMat = new LineMaterial({
    color: new THREE.Color(params.edgeColor).getHex(),
    linewidth: params.edgeWidth,
    transparent: true,
    opacity: params.edgeOpacity,
    worldUnits: false,
    dashed: false,
    alphaToCoverage: false
  });
  edgeMat.resolution.set(
    typeof window !== "undefined" ? window.innerWidth : 1,
    typeof window !== "undefined" ? window.innerHeight : 1
  );
  edgeMat.depthTest = true;
  const edgeLines = new LineSegments2(edgeGeo, edgeMat);
  edgeLines.frustumCulled = false;
  edgeLines.renderOrder = 2;
  edgeLines.visible = params.edgesVisible;

  let elapsed = 0;
  let pulseElapsed = 0;
  let sphereRotationX = 0;
  const spotTarget = new THREE.Object3D();
  const pulseRotation = new THREE.Quaternion();
  // Hard-edged disk so node corners stay clipped by alphaTest.
  // Lazily created — Three.js objects are not safe during SSR.
  let _pointTexture: THREE.Texture | null = null;
  function getPointTexture() {
    if (_pointTexture) return _pointTexture;
    if (typeof document === "undefined") {
      // SSR fallback — DataTexture works without DOM
      const data = new Uint8Array(128 * 128 * 4);
      _pointTexture = new THREE.DataTexture(data, 128, 128, THREE.RGBAFormat);
      _pointTexture.needsUpdate = true;
      return _pointTexture;
    }
    const SIZE = 128;
    const canvas = document.createElement("canvas");
    canvas.width = SIZE;
    canvas.height = SIZE;
    const ctx2d = canvas.getContext("2d")!;
    const r = SIZE / 2;
    ctx2d.clearRect(0, 0, SIZE, SIZE);
    const grad = ctx2d.createRadialGradient(r, r, 0, r, r, r);
    grad.addColorStop(0, "rgba(255,255,255,1)");
    grad.addColorStop(0.85, "rgba(255,255,255,1)");
    grad.addColorStop(1, "rgba(255,255,255,0)");
    ctx2d.fillStyle = grad;
    ctx2d.beginPath();
    ctx2d.arc(r, r, r - 1, 0, Math.PI * 2);
    ctx2d.fill();
    const tex = new THREE.CanvasTexture(canvas);
    tex.magFilter = THREE.LinearFilter;
    tex.minFilter = THREE.LinearMipmapLinearFilter;
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.premultiplyAlpha = true;
    tex.needsUpdate = true;
    _pointTexture = tex;
    return tex;
    }

  let meshMat: THREE.MeshStandardMaterial | undefined = $state();
  let membraneMesh: THREE.Mesh | undefined = $state();
  let pointsMat: THREE.PointsMaterial | undefined = $state();
  let nodesPoints: THREE.Points | undefined = $state();
  let spotLight: THREE.SpotLight | undefined = $state();
  let ambientLight: THREE.AmbientLight | undefined = $state();
  let camera: THREE.PerspectiveCamera | undefined = $state();
  let sphereGroup: THREE.Group | undefined = $state();

  const ctx = useThrelte();
  let renderAccumulator = 0;
  let renderedFrames = 0;
  let fpsElapsed = 0;

  function applyFog() {
    if (params.fogEnabled) {
      ctx.scene.fog = new THREE.Fog(params.fogColor, params.fogNear, params.fogFar);
    } else {
      ctx.scene.fog = null;
    }
  }

  function applyThemeColors() {
    applyThemeProfile(params, theme);
    const next = THEME_PROFILE[theme];

    if (meshMat) {
      meshMat.color.set(params.meshColor);
      meshMat.roughness = params.roughness;
      meshMat.metalness = params.metalness;
    }
    if (membraneMesh) membraneMesh.visible = params.meshVisible;
    if (nodesPoints) nodesPoints.visible = params.nodesVisible;
    if (pointsMat) {
      pointsMat.color.set(params.nodeColor);
      pointsMat.size = params.nodeSize;
    }
    if (camera) {
      camera.fov = params.fov;
      camera.updateProjectionMatrix();
    }
    backdropMat.uniforms.uBaseColor.value.set(next.background);
    backdropMat.uniforms.uGrainColor.value.set(next.grainColor);
    backdropMat.uniforms.uGrainOpacity.value = next.grainOpacity;
    ctx.renderer.setClearColor(next.background, 1);
    ctx.scene.background = new THREE.Color(next.background);
    applyOpacity();
    edgeMat.color.set(new THREE.Color(params.edgeColor).getHex());
    if (ctx.scene.fog) (ctx.scene.fog as THREE.Fog).color.set(params.fogColor);
    if (ambientLight) {
      ambientLight.color.set(params.ambientColor);
      ambientLight.intensity = params.ambientIntensity;
    }
    if (spotLight) {
      spotLight.color.set(params.spotColor);
      spotLight.intensity = params.spotIntensity;
    }
  }

  function applyOpacity() {
    const alpha = Math.max(0, Math.min(opacity, 1));
    const themeDefaults = getDefaultSceneBackgroundParams(theme);

    edgeLines.visible = params.edgesVisible;
    params.edgeWidth = themeDefaults.edgeWidth;
    params.edgeOpacity = themeDefaults.edgeOpacity * alpha;
    params.nodeOpacity = themeDefaults.nodeOpacity * alpha;

    if (meshMat) {
      meshMat.opacity = params.meshOpacity * alpha;
    }
    edgeMat.linewidth = params.edgeWidth;
    edgeMat.opacity = params.edgeOpacity;
    if (pointsMat) {
      pointsMat.opacity = params.nodeOpacity;
    }
  }

  $effect(() => {
    opacity;
    applyOpacity();
  });

  $effect(() => {
    theme;
    applyThemeColors();
  });

  onMount(() => {
    ctx.autoRender.set(false);

    const resolveDpr = () => Math.min(window.devicePixelRatio || 1, maxDpr);

    ctx.renderer.setPixelRatio(resolveDpr());
    ctx.renderer.toneMapping = THREE.NoToneMapping;
    ctx.renderer.outputColorSpace = THREE.SRGBColorSpace;
    ctx.renderer.setClearColor(THEME_PROFILE[theme].background, 1);
    backdropMat.uniforms.uResolution.value.set(window.innerWidth, window.innerHeight);
    ctx.scene.background = new THREE.Color(THEME_PROFILE[theme].background);
    applyFog();
    applyThemeColors();
    applyOpacity();
    edgeMat.resolution.set(window.innerWidth, window.innerHeight);

    const onResize = () => {
      ctx.renderer.setPixelRatio(resolveDpr());
      ctx.renderer.setSize(window.innerWidth, window.innerHeight);
      backdropMat.uniforms.uResolution.value.set(window.innerWidth, window.innerHeight);
      edgeMat.resolution.set(window.innerWidth, window.innerHeight);
    };
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
    };
  });

  onDestroy(() => {
    edgeGeo.dispose();
    edgeMat.dispose();
    backdropGeo.dispose();
    backdropMat.dispose();
    membraneGeo.dispose();
    _pointTexture?.dispose();
  });

  useTask(
    (delta) => {
      if (suspendWhenHidden && !pageActivity.active) {
        renderAccumulator = 0;
        return;
      }

      const frameInterval = 1 / Math.max(1, maxFps);
      renderAccumulator += Math.min(delta, 0.05);
      if (renderAccumulator < frameInterval) return;

      const frameDelta = renderAccumulator;
      renderAccumulator = 0;

      elapsed += frameDelta * params.displaceSpeed;
      backdropMat.uniforms.uTime.value += frameDelta;
      pulseElapsed += frameDelta * params.pulseSpeed;
      const t = elapsed;
      const pulseT = pulseElapsed;
      const amp = params.displaceAmp;
      const pAmp = params.pulseAmp;
      const pulseCount = Math.min(pulses.length, Math.max(0, Math.round(params.pulseCount)));
      const pulseDrift = params.pulseDriftSpeed;
      const pulseWidth = Math.max(0.001, params.pulseWidth);
      const pulseSharpness = Math.max(0.25, params.pulseSharpness);
      const pulseBulge = params.pulseBulge;
      const organicAmp = params.organicAmp;
      const organicSpeed = params.organicSpeed;
      const organicFrequency = params.organicFrequency;
      const swirl = params.swirl;
      const wiggleAmp = params.wiggleAmp;
      const wiggleFreq = params.wiggleFreq;
      const wiggleSpeed = params.wiggleSpeed;
      const wiggleSeed = params.wiggleSeed;

      for (let i = 0; i < pulseCount; i++) {
        const p = pulses[i];
        pulseRotation.setFromAxisAngle(p.axis, p.omega * pulseDrift * frameDelta);
        p.pos.applyQuaternion(pulseRotation).normalize();
      }

      const wArr = posAttr.array as Float32Array;

      for (let i = 0; i < vertCount; i++) {
        const nx = baseDirections[i * 3];
        const ny = baseDirections[i * 3 + 1];
        const nz = baseDirections[i * 3 + 2];
        const sx = nx * RADIUS;
        const sy = ny * RADIUS;
        const sz = nz * RADIUS;
        const f = freqScale[i];
        const a = ampScale[i] * amp;

        let h =
          a *
          (Math.sin(t * 0.45 * f + sx * 0.22 + sy * 0.06 + sz * 0.1 + phaseA[i] * 0.45) * 0.5 +
            Math.cos(t * 0.32 * f - sx * 0.08 + sy * 0.24 - sz * 0.12 + phaseB[i] * 0.45) * 0.35 +
            Math.sin(t * 0.22 + (sx + sy + sz) * 0.1 + phaseA[i] * 0.28) * 0.25);

        const ang = Math.atan2(nz, nx);
        const offAxis = Math.sqrt(Math.max(0, 1 - ny * ny));
        h += swirl * Math.sin(ang * 3.0 - t * 0.7 + offAxis * RADIUS * 0.35) * offAxis;

        h +=
          organicAmp *
          ampScale[i] *
          (Math.sin(t * organicSpeed + phaseA[i] + sx * organicFrequency) * 0.45 +
            Math.sin(t * organicSpeed * 0.73 + phaseB[i] + (sy - sz) * organicFrequency) * 0.35 +
            Math.cos(t * organicSpeed * 1.31 + phaseA[i] * 0.7 + (sx + sz) * organicFrequency) *
              0.2);

        if (wiggleAmp > 0) {
          const wn = smoothNoise2d(
            sx * wiggleFreq * 0.05 + wiggleSeed,
            sy * wiggleFreq * 0.05 + sz * wiggleFreq * 0.03 + t * wiggleSpeed
          );
          h += (wn - 0.5) * 2 * wiggleAmp;
        }

        let pulseSum = 0;
        for (let j = 0; j < pulseCount; j++) {
          const p = pulses[j];
          const cosArc = clamp(nx * p.pos.x + ny * p.pos.y + nz * p.pos.z, -1, 1);
          const d = Math.acos(cosArc) * RADIUS;
          const falloff = Math.exp(-Math.pow(d / pulseWidth, pulseSharpness));
          const wave = Math.sin(d * p.freq - pulseT + p.phase);
          const crest = Math.max(0, Math.cos(d * p.freq * 0.55 - pulseT * 0.45 + p.phase));
          pulseSum += p.amp * falloff * (wave + crest * pulseBulge);
        }
        h += pAmp * pulseSum;

        rawHeight[i] = h;
      }

      relaxDisplacement(rawHeight, relaxedHeight, amp);

      const nArr = normalAttr.array as Float32Array;
      for (let i = 0; i < vertCount; i++) {
        const r = RADIUS + relaxedHeight[i];
        baseHeight[i] = r;
        wArr[i * 3] = baseDirections[i * 3] * r;
        wArr[i * 3 + 1] = baseDirections[i * 3 + 1] * r;
        wArr[i * 3 + 2] = baseDirections[i * 3 + 2] * r;
        nArr[i * 3] = baseDirections[i * 3];
        nArr[i * 3 + 1] = baseDirections[i * 3 + 1];
        nArr[i * 3 + 2] = baseDirections[i * 3 + 2];
      }

      posAttr.needsUpdate = true;
      normalAttr.needsUpdate = true;

      if (params.edgesVisible) {
        for (let e = 0; e < edgePairs.length; e++) {
          const a = edgePairs[e][0];
          const b = edgePairs[e][1];
          const ra = baseHeight[a] - 0.03;
          const rb = baseHeight[b] - 0.03;
          edgePosArr[e * 6] = baseDirections[a * 3] * ra;
          edgePosArr[e * 6 + 1] = baseDirections[a * 3 + 1] * ra;
          edgePosArr[e * 6 + 2] = baseDirections[a * 3 + 2] * ra;
          edgePosArr[e * 6 + 3] = baseDirections[b * 3] * rb;
          edgePosArr[e * 6 + 4] = baseDirections[b * 3 + 1] * rb;
          edgePosArr[e * 6 + 5] = baseDirections[b * 3 + 2] * rb;
        }
        edgeGeo.setPositions(edgePosArr);
        edgeMat.linewidth = params.edgeWidth;
      }

      for (let i = 0; i < vertCount; i++) {
        const r = baseHeight[i] - 0.06;
        nodePosArr[i * 3] = baseDirections[i * 3] * r;
        nodePosArr[i * 3 + 1] = baseDirections[i * 3 + 1] * r;
        nodePosArr[i * 3 + 2] = baseDirections[i * 3 + 2] * r;
      }
      (nodeGeo.attributes.position as THREE.BufferAttribute).needsUpdate = true;

      spotLight?.position.set(params.spotX, params.spotY, params.spotZ);
      spotTarget.position.set(Math.sin(t * 0.18) * 3, Math.cos(t * 0.23) * 2, 0);
      spotTarget.updateMatrixWorld();

      // Rotation from absolute scroll position, smoothed each frame to avoid jumps
      const target = ($scrollPosition * params.rotationGain) % (Math.PI * 2);
      sphereRotationX = lerp(sphereRotationX, target, 1 - Math.exp(-2.5 * frameDelta));
      if (sphereGroup) sphereGroup.rotation.x = sphereRotationX;

      pointerBus.tick(frameDelta, 2.5);
      if (camera) {
        const easeIn = (v: number, p: number) => Math.sign(v) * Math.pow(Math.abs(v), p);
        const px = pointerBus.currentX;
        const py = pointerBus.currentY;
        camera.rotation.order = "YXZ";
        camera.rotation.y = easeIn(px, 1.6) * 0.04;
        camera.rotation.x = easeIn(py, 1.25) * 0.15;
        camera.rotation.z = (params.cameraRollDeg * Math.PI) / 180;
        camera.position.set(params.cameraOffsetX, params.cameraOffsetY, params.cameraOffsetZ);
      }

      ctx.renderer.render(ctx.scene, ctx.camera.current);

      renderedFrames++;
      fpsElapsed += frameDelta;
    },
    { autoInvalidate: false }
  );
</script>

<T.PerspectiveCamera bind:ref={camera} makeDefault fov={params.fov} position={[0, 0, 0]} />

<T.Mesh
  geometry={backdropGeo}
  material={backdropMat}
  position={[0, 0, -2]}
  scale={[12, 12, 1]}
  renderOrder={-100}
  frustumCulled={false}
/>

<T.AmbientLight
  bind:ref={ambientLight}
  intensity={params.ambientIntensity}
  color={params.ambientColor}
/>

<T is={spotTarget} />

<T.SpotLight
  bind:ref={spotLight}
  position={[params.spotX, params.spotY, params.spotZ]}
  intensity={params.spotIntensity}
  color={params.spotColor}
  angle={params.spotAngle}
  penumbra={params.spotPenumbra}
  decay={params.spotDecay}
  distance={50}
  target={spotTarget}
/>

<T.Group bind:ref={sphereGroup}>
  <T.Mesh bind:ref={membraneMesh} geometry={membraneGeo} visible={params.meshVisible}>
    <T.MeshStandardMaterial
      bind:ref={meshMat}
      color={params.meshColor}
      flatShading
      side={THREE.BackSide}
      roughness={params.roughness}
      metalness={params.metalness}
      envMapIntensity={0}
      transparent
      opacity={params.meshOpacity * opacity}
    />
  </T.Mesh>

  <T is={edgeLines} />

  <T.Points
    bind:ref={nodesPoints}
    geometry={nodeGeo}
    renderOrder={999}
    frustumCulled={false}
    visible={params.nodesVisible}
  >
    <T.PointsMaterial
      bind:ref={pointsMat}
      map={getPointTexture()}
      alphaMap={getPointTexture()}
      color={params.nodeColor}
      size={params.nodeSize}
      sizeAttenuation
      transparent
      alphaTest={0.5}
      depthTest={true}
      depthWrite={false}
      opacity={params.nodeOpacity}
      fog={false}
    />
  </T.Points>
</T.Group>