<script lang="ts">
  import { Drawer as DrawerPrimitive } from "vaul-svelte"

  type DrawerProps = {
    shouldScaleBackground?: boolean
    open?: boolean
    activeSnapPoint?: string | number | null
    [key: string]: any
  }

  let {
    shouldScaleBackground = true,
    open = $bindable(false),
    activeSnapPoint = $bindable(null),
    ...restProps
  }: DrawerProps = $props()
</script>

<DrawerPrimitive.NestedRoot {shouldScaleBackground} bind:open bind:activeSnapPoint {...restProps} />
