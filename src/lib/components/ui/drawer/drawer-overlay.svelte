<script lang="ts">
  import type { HTMLAttributes } from "svelte/elements"
  import { Drawer as DrawerPrimitive } from "vaul-svelte"
  import { cn, type WithElementRef } from "$lib/utils.js"

  let {
    ref = $bindable(null),
    class: className,
    ...restProps
  }: WithElementRef<HTMLAttributes<HTMLDivElement>> = $props()
</script>

<DrawerPrimitive.Overlay
  data-slot="drawer-overlay"
  class={cn(
    "data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 fixed inset-0 z-50 bg-black/50 backdrop-blur",
    className
  )}
  {...restProps}
/>
