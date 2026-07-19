<script lang="ts">
  import type { PageData } from "./$types";
  import V2AdminMethodology from "$lib/components/v2/v2-admin-methodology.svelte";
  import V2AdminObservability from "$lib/components/v2/v2-admin-observability.svelte";

  let { data }: { data: PageData } = $props();
</script>

<V2AdminObservability data={data.v2} />
<V2AdminMethodology methodology={data.methodology} />
