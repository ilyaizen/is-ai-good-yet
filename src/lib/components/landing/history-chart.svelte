<script lang="ts">
  import type { WeeklySnapshot } from "$lib/server/db"

  let {
    data = [],
    compact = false,
    onHover = undefined,
  }: { data: WeeklySnapshot[]; compact?: boolean; onHover?: (snapshot: WeeklySnapshot | null) => void } = $props()

  // Chart dimensions - use smaller values in compact mode
  const width = 800
  const height = $derived(compact ? 150 : 280)
  const padding = $derived(
    compact ? { top: 10, right: 0, bottom: 10, left: 0 } : { top: 20, right: 20, bottom: 40, left: 50 }
  )
  const chartWidth = $derived(width - padding.left - padding.right)
  const chartHeight = $derived(height - padding.top - padding.bottom)

  // Y-axis range: 0-100 (verdict score)
  const yMin = 0
  const yMax = 100
  const baseline = 50 // Midpoint for candlesticks

  // Threshold lines
  const yesThreshold = 55
  const noThreshold = 45

  // Filter data to start from May 2023
  const filteredData = $derived(data.filter((d) => d.weekStart >= "2023-05-01"))

  // Hover state
  let hoveredIndex = $state<number | null>(null)
  let containerElement = $state<HTMLDivElement | null>(null)
  let rafId = $state<number | null>(null)

  // Calculate scales
  function xScale(index: number): number {
    if (filteredData.length <= 1) return padding.left + chartWidth / 2
    return padding.left + (index / (filteredData.length - 1)) * chartWidth
  }

  function yScale(value: number): number {
    return padding.top + chartHeight - ((value - yMin) / (yMax - yMin)) * chartHeight
  }

  // Candlestick width - always 1px for minimal look
  const candleWidth = 1

  // Format week date for display (e.g., "Feb 10 '25")
  function formatWeekDate(weekStart: string): string {
    const date = new Date(weekStart)
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return `${monthNames[date.getMonth()]} ${date.getDate()} '${String(date.getFullYear()).slice(2)}`
  }

  // Format month for axis labels (e.g., "02-24")
  function formatMonth(weekStart: string): string {
    const date = new Date(weekStart)
    const month = String(date.getMonth() + 1).padStart(2, "0")
    const year = String(date.getFullYear()).slice(2)
    return `${month}-${year}`
  }

  // Get month labels (show monthly labels to avoid crowding with weekly data)
  const monthLabels = $derived(() => {
    if (filteredData.length === 0) return []
    const labels: { x: number; label: string }[] = []

    const step = Math.max(1, Math.floor(filteredData.length / 12))
    let lastMonth = ""

    for (let i = 0; i < filteredData.length; i += step) {
      const month = formatMonth(filteredData[i].weekStart)
      if (month !== lastMonth) {
        labels.push({ x: xScale(i), label: month })
        lastMonth = month
      }
    }

    const lastIndex = filteredData.length - 1
    const lastLabel = formatMonth(filteredData[lastIndex].weekStart)
    if (labels.length === 0 || labels[labels.length - 1].label !== lastLabel) {
      labels.push({ x: xScale(lastIndex), label: lastLabel })
    }
    return labels
  })

  // Handle hover - throttled with rAF for performance
  function handleMouseMove(event: MouseEvent) {
    if (rafId !== null) return
    rafId = requestAnimationFrame(() => {
      rafId = null
      if (!containerElement) return
      const rect = containerElement.getBoundingClientRect()
      const x = event.clientX - rect.left

      if (filteredData.length === 0) {
        hoveredIndex = null
        onHover?.(null)
        return
      }

      const svgX = (x / rect.width) * width

      let closest = 0
      let closestDist = Infinity
      for (let i = 0; i < filteredData.length; i++) {
        const dist = Math.abs(xScale(i) - svgX)
        if (dist < closestDist) {
          closestDist = dist
          closest = i
        }
      }

      if (hoveredIndex !== closest) {
        hoveredIndex = closest
        onHover?.(filteredData[closest])
      }
    })
  }

  function handleMouseLeave() {
    if (rafId !== null) {
      cancelAnimationFrame(rafId)
      rafId = null
    }
    hoveredIndex = null
    onHover?.(null)
  }

  // Get color for verdict
  function getVerdictColor(verdict: "YES" | "NO" | "NOT_YET"): string {
    switch (verdict) {
      case "YES":
        return "var(--color-primary)"
      case "NO":
        return "var(--color-destructive)"
      case "NOT_YET":
        return "var(--color-warning)"
    }
  }

  // Get display text for verdict
  function getVerdictDisplay(verdict: "YES" | "NO" | "NOT_YET"): string {
    switch (verdict) {
      case "YES":
        return "Yes"
      case "NO":
        return "No"
      case "NOT_YET":
        return "Not yet"
    }
  }

  // Normalized stacked area chart data
  // For each point, calculate the percentage of positive, neutral, negative
  const stackedAreaData = $derived(() => {
    if (filteredData.length === 0) return []

    return filteredData.map((point, i) => {
      const total = point.positiveCount + point.neutralCount + point.negativeCount
      if (total === 0) {
        return {
          x: xScale(i),
          negativeEnd: 0,
          neutralEnd: 50,
          positiveEnd: 100,
        }
      }

      // Calculate percentages (stacked from bottom: negative, neutral, positive)
      const negativePercent = (point.negativeCount / total) * 100
      const neutralPercent = (point.neutralCount / total) * 100
      const positivePercent = (point.positiveCount / total) * 100

      return {
        x: xScale(i),
        negativeEnd: negativePercent,
        neutralEnd: negativePercent + neutralPercent,
        positiveEnd: 100, // Always 100 for normalized
      }
    })
  })

  // Generate SVG path for stacked area (from bottom y1 to top y2)
  function generateAreaPath(points: Array<{ x: number; y1: number; y2: number }>): string {
    if (points.length === 0) return ""

    // Build the path: go along the top edge, then back along the bottom edge
    const topEdge = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${yScale(p.y2)}`).join(" ")
    const bottomEdge = [...points]
      .reverse()
      .map((p) => `L ${p.x} ${yScale(p.y1)}`)
      .join(" ")

    return `${topEdge} ${bottomEdge} Z`
  }

  // Paths for stacked areas
  const negativePath = $derived(() => {
    const areaData = stackedAreaData()
    const points = areaData.map((d) => ({ x: d.x, y1: 0, y2: d.negativeEnd }))
    return generateAreaPath(points)
  })

  const neutralPath = $derived(() => {
    const areaData = stackedAreaData()
    const points = areaData.map((d) => ({ x: d.x, y1: d.negativeEnd, y2: d.neutralEnd }))
    return generateAreaPath(points)
  })

  const positivePath = $derived(() => {
    const areaData = stackedAreaData()
    const points = areaData.map((d) => ({ x: d.x, y1: d.neutralEnd, y2: d.positiveEnd }))
    return generateAreaPath(points)
  })
</script>

<div
  class="chart-container"
  class:compact
  bind:this={containerElement}
  onmousemove={handleMouseMove}
  onmouseleave={handleMouseLeave}
  role="img">
  {#if filteredData.length > 0}
    <svg viewBox="0 0 {width} {height}" class="chart" aria-label="Historical verdict score chart">
      <defs>
        <!-- Rounded clip path -->
        <clipPath id="chartClip">
          <rect x={padding.left} y={padding.top} width={chartWidth} height={chartHeight} rx="6" ry="6" />
        </clipPath>
      </defs>
      <!-- Chart content with rounded clip -->
      <g clip-path="url(#chartClip)">
        <!-- Background regions (subtle) -->
        <rect
          x={padding.left}
          y={yScale(yMax)}
          width={chartWidth}
          height={yScale(yesThreshold) - yScale(yMax)}
          fill="var(--color-primary)"
          opacity="0.05" />
        <rect
          x={padding.left}
          y={yScale(yesThreshold)}
          width={chartWidth}
          height={yScale(noThreshold) - yScale(yesThreshold)}
          fill="#ca8a04"
          opacity="0.05" />
        <rect
          x={padding.left}
          y={yScale(noThreshold)}
          width={chartWidth}
          height={yScale(yMin) - yScale(noThreshold)}
          fill="#ef4444"
          opacity="0.05" />

        <!-- Normalized stacked area chart (sentiment breakdown) -->
        <g class="stacked-area">
          <!-- Negative (bottom) - red -->
          <path d={negativePath()} fill="var(--color-destructive)" opacity="0.2" />
          <!-- Neutral (middle) - yellow -->
          <path d={neutralPath()} fill="var(--color-warning)" opacity="0.2" />
          <!-- Positive (top) - green -->
          <path d={positivePath()} fill="var(--color-primary)" opacity="0.2" />
        </g>

        <!-- Baseline at 50 -->
        <line
          x1={padding.left}
          y1={yScale(baseline)}
          x2={padding.left + chartWidth}
          y2={yScale(baseline)}
          stroke="var(--color-border)"
          stroke-width="1"
          opacity="0.6" />

        <!-- Threshold lines -->
        <line
          x1={padding.left}
          y1={yScale(yesThreshold)}
          x2={padding.left + chartWidth}
          y2={yScale(yesThreshold)}
          stroke="var(--color-primary)"
          stroke-width="1"
          stroke-dasharray="3 3"
          opacity="0.4" />
        <line
          x1={padding.left}
          y1={yScale(noThreshold)}
          x2={padding.left + chartWidth}
          y2={yScale(noThreshold)}
          stroke="var(--color-destructive)"
          stroke-width="1"
          stroke-dasharray="3 3"
          opacity="0.4" />

        <!-- Candlesticks (showing week-over-week change) -->
        {#each filteredData as point, i}
          {@const x = xScale(i)}
          {@const prevScore = i > 0 ? filteredData[i - 1].verdictScore : point.verdictScore}
          {@const currScore = point.verdictScore}
          {@const prevY = yScale(prevScore)}
          {@const currY = yScale(currScore)}
          {@const isUp = currScore >= prevScore}
          {@const changeColor = isUp ? "var(--color-primary)" : "var(--color-destructive)"}
          {@const isHovered = hoveredIndex === i}

          <!-- Wick (vertical line from previous score to current score) -->
          <line
            x1={x}
            y1={prevY}
            x2={x}
            y2={currY}
            stroke={changeColor}
            stroke-width={candleWidth}
            stroke-linecap="round"
            class="candlestick"
            opacity={isHovered ? 1 : 0.6} />

          <!-- Cap (small dot at current score level) -->
          <circle cx={x} cy={currY} r={isHovered ? 3 : 1.5} fill={changeColor} opacity={isHovered ? 1 : 0.8} />
        {/each}

        <!-- Hover vertical guide line -->
        {#if hoveredIndex !== null}
          <line
            x1={xScale(hoveredIndex)}
            y1={padding.top}
            x2={xScale(hoveredIndex)}
            y2={height - padding.bottom}
            stroke="var(--color-foreground)"
            stroke-width="1"
            stroke-dasharray="2 2"
            opacity="0.3" />
        {/if}
      </g>

      {#if !compact}
        <!-- Y-axis labels -->
        <text x={padding.left - 8} y={yScale(100)} text-anchor="end" dominant-baseline="middle" class="label-text">
          100
        </text>
        <text x={padding.left - 8} y={yScale(baseline)} text-anchor="end" dominant-baseline="middle" class="label-text">
          50
        </text>
        <text x={padding.left - 8} y={yScale(0)} text-anchor="end" dominant-baseline="middle" class="label-text">
          0
        </text>

        <!-- X-axis labels -->
        {#each monthLabels() as label}
          <text x={label.x} y={height - 10} text-anchor="middle" class="label-text">
            {label.label}
          </text>
        {/each}
      {/if}
    </svg>

    <!-- Tooltip - only shown in non-compact mode (compact mode uses parent display) -->
    {#if hoveredIndex !== null && !compact}
      {@const point = filteredData[hoveredIndex]}
      {@const prevScore = hoveredIndex > 0 ? filteredData[hoveredIndex - 1].verdictScore : point.verdictScore}
      {@const change = point.verdictScore - prevScore}
      {@const changeSign = change >= 0 ? "+" : ""}
      {@const changeColor = change >= 0 ? "var(--color-primary)" : "var(--color-destructive)"}
      {@const xPercent = (xScale(hoveredIndex) / width) * 100}
      {@const yPercent = (yScale(point.verdictScore) / height) * 100}
      <div class="tooltip" style="left: {xPercent}%; top: {yPercent}%;">
        <div class="tooltip-month">Week of {formatWeekDate(point.weekStart)}</div>
        <div class="tooltip-score" style="color: {getVerdictColor(point.verdict)}">
          {Math.round(point.verdictScore)} ({getVerdictDisplay(point.verdict)})
        </div>
        {#if hoveredIndex > 0}
          <div class="tooltip-change" style="color: {changeColor}">
            {changeSign}{change.toFixed(1)} from prev week
          </div>
        {/if}
        <div class="tooltip-count">{point.articleCount} articles (12mo window)</div>
      </div>
    {/if}
  {:else}
    <div class="empty-state">No data available</div>
  {/if}
</div>

<style>
  .chart-container {
    position: relative;
    width: 100%;
    max-width: 800px;
    margin: 2rem auto;
  }

  .chart-container.compact {
    margin: 0.5rem auto 0;
    max-width: 100%;
  }

  .chart-container.compact .chart {
    border-radius: 0;
  }

  .chart {
    width: 100%;
    height: auto;
    display: block;
    border-radius: 12px;
  }

  .label-text {
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 500;
    fill: var(--color-muted-foreground);
  }

  .candlestick {
    transition:
      opacity 150ms var(--ease-swift),
      stroke-width 150ms var(--ease-swift);
  }

  .tooltip {
    position: absolute;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: 1rem;
    font-family: var(--font-mono);
    font-size: 0.875rem;
    pointer-events: none;
    transform: translate(-50%, -100%);
    margin-top: -12px;
    z-index: 50;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
    min-width: 140px;
    text-align: center;
    backdrop-filter: blur(8px);
  }

  .tooltip-month {
    color: var(--color-foreground);
    font-weight: 600;
    margin-bottom: 0.375rem;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .tooltip-score {
    font-size: 1.125rem;
    font-weight: 700;
    margin-bottom: 0.375rem;
  }

  .tooltip-change {
    font-size: 0.8125rem;
    font-weight: 600;
    margin-bottom: 0.375rem;
  }

  .tooltip-count {
    color: var(--color-muted-foreground);
    font-size: 0.6875rem;
    font-weight: 500;
  }

  .empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: var(--color-muted-foreground);
    font-family: var(--font-mono);
    border-radius: 12px;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
  }
</style>
