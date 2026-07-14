import tailwindcss from "@tailwindcss/vite"
import { sveltekit } from "@sveltejs/kit/vite"
import { defineConfig, lazyPlugins } from "vite-plus"

export default defineConfig({
  lint: {
    jsPlugins: [{ name: "vite-plus", specifier: "vite-plus/oxlint-plugin" }],
    rules: { "vite-plus/prefer-vite-plus-imports": "error" },
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
    ignorePatterns: ["convex/_generated/**", "pipeline/**/*.json", "src/lib/data/**", "static/data/**"],
  },
  plugins: lazyPlugins(() => [tailwindcss(), sveltekit()]),
  server: {
    fs: {
      allow: ["convex"],
    },
  },
})
