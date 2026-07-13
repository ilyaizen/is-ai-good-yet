<script lang="ts">
  import { onMount } from "svelte";
  import { createDottedGlow } from "./dotted-glow";

  let host: HTMLDivElement;
  onMount(() => createDottedGlow(host, {
    gap: 16,
    radius: 1.1,
    color: "163,230,53",
    glowColor: "163,230,53,0.55",
    opacity: 0.36,
    speedScale: 0.7,
    backgroundOpacity: 0.32
  }));
</script>

<div class="v2-dotted-glow" bind:this={host} aria-hidden="true"></div>
