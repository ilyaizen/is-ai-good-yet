<script lang="ts">
  import { Tooltip as TooltipPrimitive } from "bits-ui"
  import { cn } from "$lib/utils.js"

  let {
    ref = $bindable(null),
    class: className,
    sideOffset = 0,
    side = "top",
    children,
    arrowClasses,
    variant = "primary",
    ...restProps
  }: TooltipPrimitive.ContentProps & {
    arrowClasses?: string
    variant?: "primary" | "destructive"
  } = $props()

  const variantClasses = {
    primary: "bg-primary text-primary-foreground",
    destructive: "bg-destructive text-destructive-foreground",
  }

  const arrowVariantClasses = {
    primary: "bg-primary",
    destructive: "bg-destructive",
  }
</script>

<TooltipPrimitive.Portal>
  <TooltipPrimitive.Content
    bind:ref
    data-slot="tooltip-content"
    {sideOffset}
    {side}
    class={cn(
      "animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 z-50 w-fit origin-(--bits-tooltip-content-transform-origin) rounded-md text-xs",
      variantClasses[variant],
      className
    )}
    {...restProps}
  >
    <div class="w-full px-3 py-1.5">
      {@render children?.()}
    </div>
    <TooltipPrimitive.Arrow>
      {#snippet child({ props })}
        <div
          class={cn(
            "z-50 size-2.5 rotate-45 rounded-[2px]",
            arrowVariantClasses[variant],
            "data-[side=top]:translate-x-1/2 data-[side=top]:translate-y-[calc(-50%_+_2px)]",
            "data-[side=bottom]:-translate-x-1/2 data-[side=bottom]:-translate-y-[calc(-50%_+_1px)]",
            "data-[side=right]:translate-x-[calc(50%_+_2px)] data-[side=right]:translate-y-1/2",
            "data-[side=left]:-translate-y-[calc(50%_-_3px)]",
            arrowClasses
          )}
          {...props}
        ></div>
      {/snippet}
    </TooltipPrimitive.Arrow>
  </TooltipPrimitive.Content>
</TooltipPrimitive.Portal>
