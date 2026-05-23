import adapter from "@sveltejs/adapter-node"
import { vitePreprocess } from "@sveltejs/vite-plugin-svelte"

/** @type {import('@sveltejs/kit').Config} */
const config = {
  // Consult https://svelte.dev/docs/kit/integrations
  // for more information about preprocessors
  preprocess: vitePreprocess(),

  kit: {
    // Coolify/Nixpacks runs this as a generic Node service, so use the
    // explicit Node adapter instead of adapter-auto (which only targets
    // known platforms like Vercel/Netlify and leaves no runnable server here).
    adapter: adapter(),
    env: {
      publicPrefix: "PUBLIC_",
    },
  },
}

export default config
