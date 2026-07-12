<script lang="ts">
  import type { PageData } from "./$types";
  import V2AdminMethodology from "$lib/components/v2/v2-admin-methodology.svelte";
  import AdminPage from "../../admin/+page.svelte";

  let { data }: { data: PageData } = $props();
</script>

<div class="v2-admin">
  <AdminPage {data} />
  <V2AdminMethodology methodology={data.methodology} />
</div>
