<script lang="ts">
  import { slide } from "svelte/transition"
  import { ChevronRight } from "@lucide/svelte"
  import HoverIcon from "./hover-icon.svelte"
  import { cn } from "$lib/utils"

  let {
    title,
    description,
    sentiment,
  }: {
    title: string
    description: string
    sentiment: "positive" | "negative" | "neutral"
  } = $props()

  let isOpen = $state(false)
</script>

<div class="w-full">
  <button
    onclick={() => (isOpen = !isOpen)}
    class="group flex items-center text-left cursor-pointer select-none py-0.5 focus:outline-hidden rounded-sm transition-colors overflow-hidden"
    aria-expanded={isOpen}>
    <!-- Title Header -->
    <span
      class="font-semibold text-foreground text-sm transition-colors group-hover:text-primary group-hover:underline">
      {title}
    </span>

    <!-- Chevron slides in on hover -->
    <HoverIcon showOnHover={true}>
      {#snippet icon()}
        <ChevronRight color="var(--color-primary)" class={cn("ml-1 w-4 h-4", isOpen ? "rotate-90" : "")} />
      {/snippet}
    </HoverIcon>
  </button>

  {#if isOpen}
    <div transition:slide={{ duration: 300, axis: "y" }}>
      <div class="text-sm text-muted-foreground mt-0.5 leading-relaxed mb-2 lowercase">
        {description}
      </div>
    </div>
  {/if}
</div>
