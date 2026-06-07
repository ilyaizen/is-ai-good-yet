<script lang="ts">
  import { page } from "$app/state"
  import { goto } from "$app/navigation"
  import { onMount } from "svelte"

  onMount(() => {
    const runParam = page.url.searchParams.get("run")
    const target = runParam ? `/admin?run=${runParam}` : "/admin"
    goto(target, { replaceState: true })
  })
</script>

<div class="mx-auto max-w-md px-4 py-20 text-center text-terminal-text-muted">
  Redirecting to unified admin page…
</div>