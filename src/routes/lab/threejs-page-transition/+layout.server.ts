import { buildLabTransitionCards } from "$lib/lab/transition-data"
import type { LayoutServerLoad } from "./$types"

export const load: LayoutServerLoad = async () => {
  return {
    cards: buildLabTransitionCards(),
  }
}
