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

<DrawerPrimitive.Description
  data-slot="drawer-description"
  class={cn("text-muted-foreground text-sm", className)}
  {...restProps}
/>
