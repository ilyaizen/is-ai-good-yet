let active = $state(true);
let initialized = false;

function readActive(): boolean {
  if (typeof document === "undefined") return true;
  return document.visibilityState === "visible";
}

function ensureListeners() {
  if (initialized || typeof document === "undefined" || typeof window === "undefined") return;
  initialized = true;

  const update = () => {
    active = readActive();
  };
  const pause = () => {
    active = false;
  };

  update();
  document.addEventListener("visibilitychange", update);
  window.addEventListener("pageshow", update);
  window.addEventListener("pagehide", pause);
}

export const pageActivity = {
  get active() {
    ensureListeners();
    return active;
  }
};