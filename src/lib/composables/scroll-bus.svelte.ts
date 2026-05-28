// Module-scoped bus so components outside the page (e.g. layout-level SceneBackground)
// can read the per-frame scroll delta from the page's smoothScroll instance.

let delta = $state(0);

export const scrollBus = {
  get delta() {
    return delta;
  },
  setDelta(value: number) {
    delta = value;
  }
};