import { loadV2PageData } from "$lib/server/v2-page-adapter";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = () => loadV2PageData();
