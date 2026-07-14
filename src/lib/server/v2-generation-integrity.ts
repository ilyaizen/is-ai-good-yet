import { createHash } from "node:crypto"

interface ManifestFile {
  sha256: string
}

export function validateManifestHashes(files: Record<string, ManifestFile>, payloads: Record<string, string>): boolean {
  return Object.entries(files).every(([filename, entry]) => {
    const payload = payloads[filename]
    return typeof payload === "string" && entry.sha256 === createHash("sha256").update(payload).digest("hex")
  })
}
