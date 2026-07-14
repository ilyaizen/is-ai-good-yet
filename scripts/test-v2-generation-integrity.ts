import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { validateManifestHashes } from "../src/lib/server/v2-generation-integrity"

const dataDirectory = fileURLToPath(new URL("../src/lib/data/v2/", import.meta.url))
const manifest = JSON.parse(readFileSync(`${dataDirectory}/manifest.json`, "utf8")) as {
  files: Record<string, { sha256: string }>
}
const payloads = Object.fromEntries(
  Object.keys(manifest.files).map((filename) => [filename, readFileSync(`${dataDirectory}/${filename}`, "utf8")])
)

assert.equal(validateManifestHashes(manifest.files, payloads), true)
assert.equal(
  validateManifestHashes(manifest.files, {
    ...payloads,
    "verdict.json": payloads["verdict.json"].trimEnd(),
  }),
  false
)

console.log("V2 generation manifest hashes match the checked-in file bytes.")
