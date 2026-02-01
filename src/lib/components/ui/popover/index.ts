import { Popover as PopoverPrimitive } from "bits-ui"
import Content from "./popover-content.svelte"
import Trigger from "./popover-trigger.svelte"
import Overlay from "./popover-overlay.svelte"
const Root = PopoverPrimitive.Root
const Close = PopoverPrimitive.Close

export {
  Root,
  Content,
  Trigger,
  Overlay,
  Close,
  //
  Root as Popover,
  Content as PopoverContent,
  Trigger as PopoverTrigger,
  Overlay as PopoverOverlay,
  Close as PopoverClose,
}
