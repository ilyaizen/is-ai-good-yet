<script lang="ts">
  import type { PageData } from "./$types";
  import AdminLogin from "../../../admin/login/+page.svelte";

  let { data }: { data: PageData } = $props();
</script>

<div class="v2-admin">
  <AdminLogin {data} />
</div>
