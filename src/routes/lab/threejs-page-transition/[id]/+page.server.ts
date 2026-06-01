import { error } from "@sveltejs/kit"
import type { PageServerLoad } from "./$types"
import { findLabTransitionCard, nextLabTransitionCard } from "$lib/lab/transition-data"

export const load: PageServerLoad = async ({ params, parent }) => {
  const { cards } = await parent()
  const card = findLabTransitionCard(cards, params.id)

  if (!card) {
    throw error(404, "Lab card not found")
  }

  return {
    card,
    nextCard: nextLabTransitionCard(cards, card.id),
  }
}
