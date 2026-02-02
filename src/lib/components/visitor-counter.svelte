<script lang="ts">
  import { getConvexClient } from "$lib/convex/client"
  import { api } from "../../../convex/_generated/api"
  import { onMount } from "svelte"
  import NumberFlow from "@number-flow/svelte"

  let visitorCount = $state<number | null>(null)
  let isLoading = $state(true)
  let error = $state<string | null>(null)

  onMount(() => {
    const convex = getConvexClient()
    let pollInterval: ReturnType<typeof setInterval> | null = null

    const fetchVisitorCount = async () => {
      try {
        const count = await convex.query(api.visitors.getVisitorCount, {})
        visitorCount = count
        isLoading = false
        error = null
      } catch (e) {
        error = `Failed to fetch visitor count: ${e instanceof Error ? e.message : String(e)}`
        isLoading = false
        console.error("Visitor count fetch error:", e)
      }
    }

    fetchVisitorCount()
    pollInterval = setInterval(fetchVisitorCount, 5000)

    return () => {
      if (pollInterval) {
        clearInterval(pollInterval)
      }
    }
  })
</script>

{#if error}
  <span class="visitor-counter-error">unavailable</span>
{:else if isLoading}
  <span class="visitor-counter-loading">···</span>
{:else if visitorCount !== null}
  <NumberFlow value={visitorCount} format={{ useGrouping: true }} />
{/if}

<style>
  .visitor-counter-loading {
    opacity: 0.6;
  }

  .visitor-counter-error {
    opacity: 0.4;
  }
</style>
