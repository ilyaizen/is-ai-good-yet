<script lang="ts">
  import { onMount } from "svelte";
  import { createWireframeGlobe } from "./dotted-globe";

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
    flicker: true,
    initialRotation: [-18, 12]
  }));
</script>

<div class="v2-dotted-globe" bind:this={host} aria-hidden="true"></div>
