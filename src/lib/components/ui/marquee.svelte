<script lang="ts">
  import { cn } from "$lib/utils"

  let {
    class: className,
    pauseOnHover = true,
    reverseOnHover = false,
    vertical = false,
    repeat = 4,
    speed = 50,
    reverse = false,
    children,
  } = $props()

  let container: HTMLDivElement | undefined = $state()

  function reverseAnimations() {
    if (!reverseOnHover || !container) return
    for (const el of container.querySelectorAll("[data-marquee-animated]")) {
      for (const anim of el.getAnimations()) anim.reverse()
    }
  }
</script>

<div
  bind:this={container}
  role="group"
  class={cn(
    "group flex overflow-hidden p-1 [--gap:0.5rem] gap-(--gap)",
    {
      "flex-row": !vertical,
      "flex-col": vertical,
    },
    className
  )}
  onmouseenter={reverseAnimations}
  onmouseleave={reverseAnimations}>
  {#each Array(repeat) as _, i (i)}
    <div
      data-marquee-animated="true"
      class={cn("flex shrink-0 justify-around gap-(--gap) flex-row", {
        "animate-marquee": !vertical && !reverse,
        "animate-marquee-reverse": !vertical && reverse,
        "animate-marquee-vertical flex-col": vertical,
        "group-hover:[animation-play-state:paused]": pauseOnHover,
      })}
      style="animation-duration: {speed}s;">
      {@render children()}
    </div>
  {/each}
</div>

<style>
  @keyframes marquee {
    from {
      transform: translateX(0);
    }
    to {
      transform: translateX(calc(-100% - var(--gap)));
    }
  }

  @keyframes marquee-reverse {
    from {
      transform: translateX(calc(-100% - var(--gap)));
    }
    to {
      transform: translateX(0);
    }
  }

  @keyframes marquee-vertical {
    from {
      transform: translateY(0);
    }
    to {
      transform: translateY(calc(-100% - var(--gap)));
    }
  }

  .animate-marquee {
    animation: marquee linear infinite;
  }

  .animate-marquee-reverse {
    animation: marquee-reverse linear infinite;
  }

  .animate-marquee-vertical {
    animation: marquee-vertical linear infinite;
  }
</style>
