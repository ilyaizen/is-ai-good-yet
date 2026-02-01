<script lang="ts">
  // @ts-ignore complex type from bits-ui
  import { Calendar as CalendarPrimitive } from "bits-ui"
  import * as Calendar from "./index.js"
  import { cn } from "$lib/utils.js"
  import type { ButtonVariant } from "../button/button.svelte"
  import { isEqualMonth, type DateValue } from "@internationalized/date"
  import type { Snippet } from "svelte"

  let {
    ref = $bindable(null),
    value = $bindable(),
    placeholder = $bindable(),
    class: className,
    weekdayFormat = "short",
    buttonVariant = "ghost",
    captionLayout = "label",
    locale = "en-US",
    months: monthsProp,
    years,
    monthFormat: monthFormatProp,
    yearFormat = "numeric",
    day,
    disableDaysOutsideMonth = false,
    animationDirection = undefined,
    type = "single",
    ...restProps
  }: Record<string, any> = $props()

  const monthFormat = $derived.by(() => {
    if (monthFormatProp) return monthFormatProp
    if (captionLayout.startsWith("dropdown")) return "short"
    return "long"
  })
</script>

<!--
Discriminated Unions + Destructing (required for bindable) do not
get along, so we shut typescript up by casting `value` to `never`.
-->
<!-- @ts-ignore -->
<CalendarPrimitive.Root
  bind:value={value as never}
  bind:ref
  bind:placeholder
  {weekdayFormat}
  {disableDaysOutsideMonth}
  class={cn(
    "bg-background group/calendar p-3 [--cell-size:--spacing(8)] [[data-slot=card-content]_&]:bg-transparent [[data-slot=popover-content]_&]:bg-transparent",
    className
  )}
  {locale}
  {monthFormat}
  {yearFormat}
  {type}
  {...restProps}
>
  {#snippet children({ months, weekdays })}
    <Calendar.Months>
      <Calendar.Nav class="pointer-events-none z-10">
        <Calendar.PrevButton variant={buttonVariant} class="pointer-events-auto" />
        <Calendar.NextButton variant={buttonVariant} class="pointer-events-auto" />
      </Calendar.Nav>
      {#each months as month, monthIndex (month)}
        {@const monthKey = `${month.value.year}-${month.value.month}`}
        {#key monthKey}
          <Calendar.Month
            class={cn(
              "calendar-month-animation fade-in-0",
              animationDirection === "left" && "slide-left",
              animationDirection === "right" && "slide-right"
            )}
          >
            <Calendar.Header>
              <Calendar.Caption
                {captionLayout}
                months={monthsProp}
                {monthFormat}
                {years}
                {yearFormat}
                month={month.value}
                bind:placeholder
                {locale}
                {monthIndex}
              />
            </Calendar.Header>
            <Calendar.Grid>
              <Calendar.GridHead>
                <Calendar.GridRow class="select-none">
                  {#each weekdays as weekday (weekday)}
                    <Calendar.HeadCell>
                      {weekday.slice(0, 2)}
                    </Calendar.HeadCell>
                  {/each}
                </Calendar.GridRow>
              </Calendar.GridHead>
              <Calendar.GridBody>
                {#each month.weeks as weekDates (weekDates)}
                  <Calendar.GridRow class="mt-2 w-full">
                    {#each weekDates as date (date)}
                      <Calendar.Cell {date} month={month.value}>
                        {#if day}
                          {@render day({
                            day: date,
                            outsideMonth: !isEqualMonth(date, month.value),
                          })}
                        {:else}
                          <Calendar.Day />
                        {/if}
                      </Calendar.Cell>
                    {/each}
                  </Calendar.GridRow>
                {/each}
              </Calendar.GridBody>
            </Calendar.Grid>
          </Calendar.Month>
        {/key}
      {/each}
    </Calendar.Months>
  {/snippet}
</CalendarPrimitive.Root>

<style>
  /* Calendar month slide animations with motion-wrapper timing */
  :global(.calendar-month-animation.slide-left) {
    transform: translateX(20px);
    animation: calendar-month-slide-left 350ms var(--ease-swift) forwards;
  }

  :global(.calendar-month-animation.slide-right) {
    transform: translateX(-20px);
    animation: calendar-month-slide-right 350ms var(--ease-swift) forwards;
  }

  @keyframes calendar-month-slide-left {
    from {
      transform: translateX(20px);
    }
    to {
      transform: translateX(0);
    }
  }

  @keyframes calendar-month-slide-right {
    from {
      transform: translateX(-20px);
    }
    to {
      transform: translateX(0);
    }
  }

  /* Respect reduced motion preference */
  @media (prefers-reduced-motion: reduce) {
    :global(.calendar-month-animation),
    :global(.calendar-month-animation.slide-left),
    :global(.calendar-month-animation.slide-right) {
      animation-duration: 0ms;
      animation-name: none;
      transform: translateX(0);
    }
  }
</style>
