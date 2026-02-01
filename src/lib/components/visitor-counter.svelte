<script lang="ts">
  import { getConvexClient } from "$lib/convex/client"
  import { api } from "../../../convex/_generated/api"
  import { onMount } from "svelte"

  // Reactive state using Svelte 5 runes
  let visitorCount = $state<number | null>(null)
  let isLoading = $state(true)
  let error = $state<string | null>(null)

  onMount(() => {
    const convex = getConvexClient()
    let pollInterval: ReturnType<typeof setInterval> | null = null

    /**
     * Fetch visitor count via polling (Convex v1.31.7 doesn't support watchQuery on browser client)
     * Poll every 5 seconds for updates
     */
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

    // Fetch immediately on mount
    fetchVisitorCount()

    // Poll every 5 seconds for updates
    pollInterval = setInterval(fetchVisitorCount, 5000)

    // Cleanup interval on component unmount
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval)
      }
    }
  })

  // Format number with locale string (1234 -> "1,234")
  // Derived value automatically updates when visitorCount changes
  const formattedCount = $derived(visitorCount !== null ? visitorCount.toLocaleString() : "—")
</script>

{#if error}
  <!-- Error state: Convex unavailable -->
  <span class="visitor-counter-error">unavailable</span>
{:else if isLoading}
  <!-- Loading state: Still connecting to Convex -->
  <span class="visitor-counter-loading">loading...</span>
{:else}
  <!-- Success state: Display the count -->
  <span>{formattedCount}</span>
{/if}

<style>
  .visitor-counter-loading {
    opacity: 0.6;
  }

  .visitor-counter-error {
    opacity: 0.4;
  }
</style>
