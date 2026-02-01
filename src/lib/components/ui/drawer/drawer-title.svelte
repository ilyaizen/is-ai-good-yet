<script lang="ts">
  import type { HTMLAttributes } from "svelte/elements"
  import { Drawer as DrawerPrimitive } from "vaul-svelte"
  import { cn } from "$lib/utils.js"

  let { class: className, ...restProps }: HTMLAttributes<HTMLHeadingElement> = $props()
</script>

<DrawerPrimitive.Title data-slot="drawer-title" class={cn("text-foreground font-semibold", className)} {...restProps} />
