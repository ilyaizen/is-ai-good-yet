<script lang="ts">
  import { Popover as PopoverPrimitive } from "bits-ui"
  import { cn } from "$lib/utils.js"

  let { ref = $bindable(null), class: className, ...restProps }: PopoverPrimitive.OverlayProps = $props()
</script>

<PopoverPrimitive.Overlay
  bind:ref
  data-slot="popover-overlay"
  class={cn(
    "data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 fixed inset-0 z-[100] bg-black/50",
    className
  )}
  {...restProps}
/>
