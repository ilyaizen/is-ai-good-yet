export interface TokenStreamState {
  streamingInProgress: boolean
  streamedCharsPerLine: number[]
}

export interface TokenStreamOptions {
  tokensPerSecond?: number
  charsPerToken?: number
}

export function useTokenStream(lines: string[], options: TokenStreamOptions = {}) {
  const { tokensPerSecond = 400, charsPerToken = 4 } = options

  const state = $state<TokenStreamState>({
    streamingInProgress: false,
    streamedCharsPerLine: lines.map(() => 0),
  })

  let onComplete: (() => void) | null = null

  function stream(onCompleteCallback?: () => void): Promise<void> | undefined {
    if (state.streamingInProgress) return

    state.streamingInProgress = true
    state.streamedCharsPerLine = lines.map(() => 0)
    onComplete = onCompleteCallback ?? null

    const msPerToken = 1000 / tokensPerSecond

    function streamNextToken(): void {
      if (!state.streamingInProgress) return

      let currentStreamingLine = 0
      while (currentStreamingLine < lines.length) {
        if (state.streamedCharsPerLine[currentStreamingLine] < lines[currentStreamingLine].length) {
          break
        }
        currentStreamingLine++
      }

      if (currentStreamingLine >= lines.length) {
        state.streamingInProgress = false
        onComplete?.()
        return
      }

      const charsToStream = Math.max(1, Math.ceil(charsPerToken))

      state.streamedCharsPerLine[currentStreamingLine] = Math.min(
        state.streamedCharsPerLine[currentStreamingLine] + charsToStream,
        lines[currentStreamingLine].length
      )

      setTimeout(streamNextToken, msPerToken)
    }

    return new Promise<void>((resolve) => {
      const originalOnComplete = onComplete
      onComplete = () => {
        originalOnComplete?.()
        resolve()
      }
      streamNextToken()
    })
  }

  function reset(): void {
    state.streamingInProgress = false
    state.streamedCharsPerLine = lines.map(() => 0)
  }

  function getVisibleText(lineIndex: number): string {
    return lines[lineIndex].slice(0, state.streamedCharsPerLine[lineIndex])
  }

  function isLineComplete(lineIndex: number): boolean {
    return state.streamedCharsPerLine[lineIndex] >= lines[lineIndex].length
  }

  function isAllComplete(): boolean {
    return lines.every((_, i) => isLineComplete(i))
  }

  return {
    state,
    stream,
    reset,
    getVisibleText,
    isLineComplete,
    isAllComplete,
  }
}
