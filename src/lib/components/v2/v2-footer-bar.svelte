<script lang="ts">
  let { onReplay }: { onReplay: () => void } = $props();
</script>

<nav class="v2-footer" aria-label="Dashboard actions">
  <p><b>&gt;_</b> Inspect the current record, methodology, or replay the verdict.</p>
  <div><a href="#home">BACK TO TOP ↑</a><button type="button" onclick={onReplay}>REPLAY VERDICT <span>&gt;_</span></button></div>
</nav>
