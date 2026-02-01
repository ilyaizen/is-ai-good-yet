<script lang="ts">
  import type { HTMLButtonAttributes } from "svelte/elements"
  import { Drawer as DrawerPrimitive } from "vaul-svelte"

  let { ...restProps }: HTMLButtonAttributes = $props()
</script>

<DrawerPrimitive.Close data-slot="drawer-close" {...restProps} />
