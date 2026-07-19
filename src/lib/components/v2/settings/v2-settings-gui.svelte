<script lang="ts">
  import { onMount } from "svelte";
  import {
    applyV2VisualSettings,
    defaultV2Settings,
    parseV2Settings,
    V2_SETTINGS_KEY,
    type V2Settings
  } from "$lib/state/v2-settings.svelte";

  interface Props {
    open: boolean;
    settings: V2Settings;
    root: HTMLElement | null;
    onClose: () => void;
    onChange: (settings: V2Settings) => void;
  }

  let { open, settings, root, onClose, onChange }: Props = $props();
  // eslint-disable-next-line no-unassigned-vars -- assigned via bind:this
  let host: HTMLDivElement;
  // eslint-disable-next-line no-unassigned-vars -- assigned via bind:this
  let panel: HTMLElement;
  let disposeGui: () => void = () => undefined;
  let previousFocus: HTMLElement | null = null;

  function persist(next: V2Settings): void {
    const safe = parseV2Settings(next);
    onChange(safe);
    if (root) applyV2VisualSettings(root, safe);
    localStorage.setItem(V2_SETTINGS_KEY, JSON.stringify(safe));
  }

  onMount(() => {
    let destroyed = false;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && open) onClose();
    };
    document.addEventListener("keydown", onKey);

    void import("lil-gui").then(({ default: GUI }) => {
      if (destroyed) return;
      const model: V2Settings = { ...settings, dimensions: { ...settings.dimensions } };
      const gui = new GUI({ container: host, autoPlace: false, title: "DISPLAY CONTROL", width: 340 });
      const sync = () => persist(model);

      const dimensions = gui.addFolder("DIMENSIONS");
      dimensions.add(model.dimensions, "capability").name("Capability").onChange(sync);
      dimensions.add(model.dimensions, "trajectory").name("Trajectory").onChange(sync);
      dimensions.add(model.dimensions, "impact").name("Impact").onChange(sync);

      const windowFolder = gui.addFolder("WINDOW");
      windowFolder.add(model, "timeWindow", ["24h", "7d", "30d", "90d", "12m", "all"]).name("Time window").onChange(sync);

      const filters = gui.addFolder("FILTERS");
      filters.add(model, "conflictsOnly").name("Source conflicts only").onChange(sync);

      const display = gui.addFolder("DISPLAY");
      display.add(model, "density", ["compact", "comfortable", "expanded"]).name("Density").onChange(sync);
      display.add(model, "sort", ["newest", "influence", "divergence", "polarization"]).name("Sort").onChange(sync);
      display.add(model, "previewImages").name("Preview images").onChange(sync);

      const crt = gui.addFolder("CRT");
      crt.add(model, "scanlineOpacity", 0, 0.16, 0.005).name("Scanline opacity").onChange(sync);
      crt.add(model, "vignetteStrength", 0, 0.3, 0.01).name("Vignette strength").onChange(sync);
      crt.add(model, "grainOpacity", 0, 0.1, 0.005).name("Grain opacity").onChange(sync);
      crt.add(model, "ambientMotion").name("Ambient motion").onChange(sync);

      const actions = {
        resetFilters: () => {
          const defaults = defaultV2Settings();
          Object.assign(model.dimensions, defaults.dimensions);
          Object.assign(model, {
            timeWindow: defaults.timeWindow,
            conflictsOnly: defaults.conflictsOnly,
            density: defaults.density,
            sort: defaults.sort,
            previewImages: defaults.previewImages
          });
          gui.controllersRecursive().forEach((controller) => controller.updateDisplay());
          sync();
        },
        resetVisualEffects: () => {
          const defaults = defaultV2Settings();
          Object.assign(model, { scanlineOpacity: defaults.scanlineOpacity, vignetteStrength: defaults.vignetteStrength, grainOpacity: defaults.grainOpacity, ambientMotion: defaults.ambientMotion });
          gui.controllersRecursive().forEach((controller) => controller.updateDisplay());
          sync();
        }
      };
      const actionFolder = gui.addFolder("ACTIONS");
      actionFolder.add(actions, "resetFilters").name("Reset filters");
      actionFolder.add(actions, "resetVisualEffects").name("Reset visual effects");
      disposeGui = () => gui.destroy();
    });

    return () => {
      destroyed = true;
      disposeGui();
      document.removeEventListener("keydown", onKey);
    };
  });

  $effect(() => {
    if (open) {
      previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      window.setTimeout(() => panel?.focus(), 0);
    } else if (previousFocus) {
      previousFocus.focus();
      previousFocus = null;
    }
  });
</script>

{#if open}
  <button class="v2-settings-backdrop" aria-label="Close display control" onclick={onClose}></button>
{/if}
<aside
  id="v2-display-control"
  class="v2-settings"
  class:v2-settings--open={open}
  aria-hidden={!open}
  aria-label="Display control"
  tabindex="-1"
  bind:this={panel}
>
  <header><strong>DISPLAY CONTROL</strong><button type="button" onclick={onClose} aria-label="Close display control">[x]</button></header>
  <div class="v2-settings__gui" bind:this={host}></div>
</aside>
