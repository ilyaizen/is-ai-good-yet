<script lang="ts">
  import { v12Effects } from "$lib/state/v12-effects.svelte"

  let { value }: { value: string } = $props()

  /**
   * Odometer digits (ported from the v1.2 direction-B prototype): each digit is a
   * masked column rolling a 0-9 strip with steps() so digits tick like a counter,
   * staggered right-to-left. Separators (".", "±", "−") stay static. Falls back to
   * plain text whenever motion is not OK (FX off / reduced motion).
   */
  function flow(node: HTMLElement, initial: string) {
    let length = -1
    let strips: HTMLElement[] = []

    function mirror(text: string): void {
      const sr = node.querySelector(".sr-only")
      if (sr) sr.textContent = text
    }

    function build(text: string): void {
      node.textContent = ""
      strips = []
      for (const ch of text) {
        const cell = document.createElement("span")
        if (ch >= "0" && ch <= "9") {
          cell.className = "flow-col"
          const strip = document.createElement("span")
          strip.className = "flow-strip"
          strip.setAttribute("aria-hidden", "true")
          strip.setAttribute("data-d", "0")
          strip.style.transform = "translateY(0%)"
          for (let digit = 0; digit <= 9; digit += 1) {
            const row = document.createElement("span")
            row.textContent = String(digit)
            strip.appendChild(row)
          }
          cell.appendChild(strip)
          strips.push(strip)
        } else {
          cell.className = "flow-sep"
          cell.textContent = ch
        }
        node.appendChild(cell)
      }
      const sr = document.createElement("span")
      sr.className = "sr-only"
      sr.textContent = text
      node.appendChild(sr)
      length = [...text].length
    }

    function update(text: string): void {
      if (!v12Effects.motionOK) {
        node.textContent = text
        strips = []
        return
      }
      if ([...text].length !== length) {
        build(text)
      }
      const digits = [...text].filter((ch) => ch >= "0" && ch <= "9")
      strips.forEach((strip, index) => {
        const target = Number(digits[index])
        const current = Number(strip.getAttribute("data-d"))
        const dist = Math.abs(target - current)
        const fromRight = strips.length - 1 - index
        strip.style.transition =
          dist > 0 ? `transform ${140 + dist * 60}ms steps(${dist}, end) ${fromRight * 45}ms` : "none"
        strip.style.transform = `translateY(${target * -10}%)`
        strip.setAttribute("data-d", String(target))
      })
      mirror(text)
    }

    build(initial)
    update(initial)
    return { update } satisfies { update(next: string): void }
  }
</script>

<span class="flow" use:flow={value}>{value}</span>

<style>
  .flow {
    display: inline-flex;
    align-items: baseline;
    font-variant-numeric: tabular-nums;
  }

  /* Strip cells and separators are created imperatively by the flow action, so
     they are invisible to Svelte's CSS pruner — scope them globally; the
     flow-* class names are unique to this component. */
  :global(.flow-col) {
    display: inline-block;
    width: 0.62em;
    height: 1em;
    line-height: 1;
    overflow: hidden;
    text-align: center;
  }

  :global(.flow-strip) {
    display: block;
    will-change: transform;
  }

  :global(.flow-strip > span) {
    display: block;
    height: 1em;
    line-height: 1;
  }

  :global(.flow-sep) {
    display: inline-block;
    height: 1em;
    line-height: 1;
    text-align: center;
  }

  :global(html.fx-off .flow-strip) {
    transition: none;
  }

  @media (prefers-reduced-motion: reduce) {
    :global(.flow-strip) {
      transition: none;
    }
  }
</style>
