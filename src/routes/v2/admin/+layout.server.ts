// Auth gate (configured / authenticated + redirect to login) comes from the
// shared V1 layout load. Note: SvelteKit forbids `actions` in +layout.server.ts
// (only +page.server.ts may export actions), so logout stays on the page.
export { load } from "../../admin/+layout.server"
