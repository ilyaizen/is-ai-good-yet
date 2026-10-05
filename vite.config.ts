import tailwindcss from "@tailwindcss/vite"
import { sveltekit } from "@sveltejs/kit/vite"
import { defineConfig, lazyPlugins } from "vite-plus"

const agentToolingIgnores = [
  ".agent/**",
  ".agents/**",
  ".claude/**",
  ".codex/**",
  ".continue/**",
  ".cursor/**",
  ".gemini/**",
  ".opencode/**",
  ".pi/**",
  ".pi-subagents/**",
  ".roo/**",
  ".windsurf/**",
  "tools/oxlint/anti-slop/**",
]

export default defineConfig({
  lint: {
    ignorePatterns: agentToolingIgnores,
    jsPlugins: [
      { name: "vite-plus", specifier: "vite-plus/oxlint-plugin" },
      { name: "anti-slop", specifier: "./tools/oxlint/anti-slop/index.ts" },
    ],
    rules: {
      "vite-plus/prefer-vite-plus-imports": "error",
      "anti-slop/no-chained-type-assertions": "error",
      "anti-slop/no-conditional-empty-object-spread": "error",
      "anti-slop/no-known-value-widening": "error",
      "anti-slop/no-module-mocking": "error",
      "anti-slop/no-object-parameters": "error",
      "anti-slop/no-reflect-apply": "error",
      "anti-slop/no-reflect-get": "error",
      "anti-slop/no-runtime-typeof": "error",
      "anti-slop/no-shape-in-symbol-names": "error",
      "anti-slop/no-unknown-parameters": "error",
      "anti-slop/no-unknown-returns": "error",
      "anti-slop/no-unknown-type-aliases": "error",
      "anti-slop/no-unsafe-dictionary-type": "error",
      "anti-slop/no-widen-then-assert": "error",
      "anti-slop/require-safety-comment-for-type-assertion": "error",
    },
    options: { typeAware: true, typeCheck: false },
  },
  fmt: {
    semi: false,
    singleQuote: false,
    trailingComma: "es5",
    printWidth: 120,
    tabWidth: 2,
    useTabs: false,
    svelteStrictMode: false,
    svelteAllowShorthand: true,
    svelteBracketNewLine: false,
    svelteIndentScriptAndStyle: true,
    sortPackageJson: false,
    ignorePatterns: [
      "convex/_generated/**",
      "pipeline/**/*.json",
      "src/lib/data/**",
      "static/data/**",
      ...agentToolingIgnores,
    ],
  },
  plugins: lazyPlugins(() => [tailwindcss(), sveltekit()]),
  server: {
    fs: {
      allow: ["convex"],
    },
  },
})
