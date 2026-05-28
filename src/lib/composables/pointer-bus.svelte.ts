// Module-scoped pointer bus. One window listener feeds normalized pointer
// coordinates (−1..1, y inverted to match Three's convention) to any component
// that wants them. Eased "current" values are advanced by a single tick() call
// per frame (owned by scene-background).

let targetX = $state(0);
let targetY = $state(0);
let currentX = $state(0);
let currentY = $state(0);

let initialised = false;

function ensureListeners() {
  if (initialised || typeof window === "undefined") return;
  initialised = true;

  const onPointerMove = (event: PointerEvent) => {
    targetX = (event.clientX / Math.max(1, window.innerWidth)) * 2 - 1;
    targetY = -((event.clientY / Math.max(1, window.innerHeight)) * 2 - 1);
  };
  const onPointerLeave = () => {
    targetX = 0;
    targetY = 0;
  };

  window.addEventListener("pointermove", onPointerMove, { passive: true });
  window.addEventListener("pointerleave", onPointerLeave);
}

export const pointerBus = {
  get targetX() {
    ensureListeners();
    return targetX;
  },
  get targetY() {
    ensureListeners();
    return targetY;
  },
  get currentX() {
    ensureListeners();
    return currentX;
  },
  get currentY() {
    ensureListeners();
    return currentY;
  },
  tick(delta: number, ease: number) {
    ensureListeners();
    const k = 1 - Math.exp(-Math.max(0.01, ease) * Math.max(0, delta));
    currentX += (targetX - currentX) * k;
    currentY += (targetY - currentY) * k;
  }
};