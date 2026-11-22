<script lang="ts">
  import { getConvexClient } from "$lib/convex/client"
  import { api } from "../../../convex/_generated/api"
  import { onMount } from "svelte"
  import NumberFlow from "@number-flow/svelte"

  let { animated = true }: { animated?: boolean } = $props()
  let visitorCount = $state<number | null>(null)
  let unavailable = $state(false)

  onMount(() => {
    const convex = getConvexClient()
    if (!convex) {
      unavailable = true
      return
    }

    return convex.onUpdate(
      api.visitors.getVisitorCount,
      {},
      (count) => {
        visitorCount = count
        unavailable = false
      },
      () => {
        unavailable = true
      }
    )
  })
</script>

{#if unavailable}
  unavailable
{:else if visitorCount === null}
  loading
{:else}
  <NumberFlow value={visitorCount} {animated} format={{ useGrouping: true }} />
{/if}
