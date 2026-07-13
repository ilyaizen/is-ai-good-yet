<script lang="ts">
  import { onMount } from "svelte";
  import { createWireframeGlobe } from "./dotted-globe";
  import { WORLD_CITIES } from "./world-cities";

  let host: HTMLDivElement;
  onMount(() => createWireframeGlobe(host, {
    rotationSpeed: 1.8,
    graticuleStep: 15,
    wireAlpha: 0.15,
    dotAlpha: 0.62,
    dotRadius: 0.9,
    landResolution: 2,
    radiusFraction: 0.43,
    limbPadding: 0.2,
    flicker: false,
    initialRotation: [-18, 12],
    cities: WORLD_CITIES
  }));
</script>

<div class="v2-dotted-globe" bind:this={host} aria-hidden="true"></div>
