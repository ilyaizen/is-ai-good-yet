import path from "node:path"

type ResolvePipelinePythonOptions = {
  explicit?: string
  repoRoot: string
  pipelineDir: string
  platform: NodeJS.Platform
  exists: (candidate: string) => boolean
}

export function resolvePipelinePython(options: ResolvePipelinePythonOptions): string {
  const executable = options.platform === "win32" ? path.join("Scripts", "python.exe") : path.join("bin", "python")
  const candidates = [
    options.explicit?.trim(),
    path.join(options.repoRoot, ".venv", executable),
    path.join(options.pipelineDir, ".venv", executable),
    options.platform === "win32" ? undefined : "/usr/bin/python3",
  ].filter((candidate): candidate is string => Boolean(candidate))

  return candidates.find(options.exists) ?? candidates[0]
}

export function createOnceFinalizer<T extends unknown[]>(finalize: (...args: T) => void): (...args: T) => boolean {
  let finalized = false

  return (...args: T): boolean => {
    if (finalized) return false
    finalized = true
    finalize(...args)
    return true
  }
}
