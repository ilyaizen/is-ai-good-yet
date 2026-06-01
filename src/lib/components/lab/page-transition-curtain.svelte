<script lang="ts">
  import { onMount } from "svelte"
  import * as THREE from "three"

  interface Props {
    active: boolean
    progress: number
    poster: string
    accent: string
    title: string
    phase: "out" | "in"
  }

  let { active, progress, poster, accent, title, phase }: Props = $props()

  let canvas: HTMLCanvasElement | null = $state(null)
  let renderer: THREE.WebGLRenderer | null = null
  let scene: THREE.Scene | null = null
  let camera: THREE.OrthographicCamera | null = null
  let geometry: THREE.PlaneGeometry | null = null
  let material: THREE.ShaderMaterial | null = null
  let texture: THREE.Texture | null = null
  let raf = 0
  let resizeHandler: (() => void) | null = null
  let loadedPoster = ""

  const uniforms = {
    uProgress: { value: 0 },
    uTime: { value: 0 },
    uPoster: { value: null as THREE.Texture | null },
    uAccent: { value: new THREE.Color("#7dd3fc") },
    uPhase: { value: 0 },
  }

  function loadPoster(nextPoster: string) {
    if (!material) return
    if (texture) {
      texture.dispose()
      texture = null
    }

    loadedPoster = nextPoster
    const loader = new THREE.TextureLoader()
    texture = loader.load(nextPoster, () => {
      if (renderer) renderer.render(scene!, camera!)
    })
    texture.colorSpace = THREE.SRGBColorSpace
    texture.minFilter = THREE.LinearFilter
    texture.magFilter = THREE.LinearFilter
    texture.generateMipmaps = false
    uniforms.uPoster.value = texture
  }

  function resize() {
    if (!renderer || !canvas) return
    const width = canvas.clientWidth || window.innerWidth
    const height = canvas.clientHeight || window.innerHeight
    renderer.setSize(width, height, false)
  }

  onMount(() => {
    if (!canvas) return

    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "high-performance" })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5))
    renderer.setClearColor(0x000000, 0)

    scene = new THREE.Scene()
    camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1)
    geometry = new THREE.PlaneGeometry(2, 2)

    const vertexShader = `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `

    const fragmentShader = `
      precision mediump float;
      uniform sampler2D uPoster;
      uniform float uProgress;
      uniform float uTime;
      uniform vec3 uAccent;
      uniform float uPhase;
      varying vec2 vUv;

      float curtainMask(vec2 uv) {
        float distanceFromCenter = abs(uv.x - 0.5) * 2.0;
        float eased = smoothstep(uProgress - 0.15, uProgress + 0.15, distanceFromCenter);
        float ripple = sin((uv.y * 16.0) + (uTime * 0.006)) * 0.01;
        return clamp(eased + ripple, 0.0, 1.0);
      }

      void main() {
        vec2 uv = vUv;
        vec3 poster = texture2D(uPoster, vec2(uv.x, 1.0 - uv.y)).rgb;
        vec3 curtain = mix(vec3(0.028, 0.04, 0.06), uAccent * 0.2, 0.35);
        float mask = curtainMask(uv);
        float phaseMix = mix(uProgress, 1.0 - uProgress, step(0.5, uPhase));
        float openWindow = smoothstep(0.02, 0.14, phaseMix);
        vec3 color = mix(poster, curtain, mask);
        color = mix(color, poster, openWindow * (1.0 - mask));
        float scanline = step(0.5, mod(floor(uv.y * 420.0 + uTime * 22.0), 2.0));
        color += (1.0 - mask) * scanline * 0.018;
        gl_FragColor = vec4(color, 0.98);
      }
    `

    material = new THREE.ShaderMaterial({
      uniforms,
      vertexShader,
      fragmentShader,
      transparent: true,
      depthTest: false,
      depthWrite: false,
    })

    const mesh = new THREE.Mesh(geometry, material)
    scene.add(mesh)

    loadPoster(loadedPoster)
    resize()

    resizeHandler = () => resize()
    window.addEventListener("resize", resizeHandler)

    const tick = (time: number) => {
      if (!renderer || !scene || !camera || !material) return
      uniforms.uTime.value = time
      uniforms.uProgress.value = progress
      uniforms.uPhase.value = phase === "out" ? 0 : 1
      uniforms.uAccent.value.set(accent || "#7dd3fc")
      renderer.render(scene, camera)
      raf = requestAnimationFrame(tick)
    }

    raf = requestAnimationFrame(tick)

    return () => {
      if (resizeHandler) window.removeEventListener("resize", resizeHandler)
      cancelAnimationFrame(raf)
      texture?.dispose()
      geometry?.dispose()
      material?.dispose()
      renderer?.dispose()
      texture = null
      geometry = null
      material = null
      renderer = null
      scene = null
      camera = null
    }
  })

  $effect(() => {
    if (poster && poster !== loadedPoster) {
      loadPoster(poster)
    }
  })
</script>

<canvas
  bind:this={canvas}
  class="lab-transition-curtain"
  class:is-active={active}
  aria-hidden="true"
></canvas>

<style>
  .lab-transition-curtain {
    position: fixed;
    inset: 0;
    width: 100vw;
    height: 100vh;
    pointer-events: none;
    z-index: 80;
    opacity: 0;
    transition: opacity 120ms ease;
  }

  .lab-transition-curtain.is-active {
    opacity: 1;
  }
</style>
