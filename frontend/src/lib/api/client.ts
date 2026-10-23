import createClient from "openapi-fetch";

import type { paths } from "./schema";

/**
 * Typed API client generated from the backend's OpenAPI schema.
 * Paths, request bodies and responses are all checked by TypeScript:
 * if the backend changes, `npm run api:types` + `npm run typecheck` shows what broke.
 */
export const api = createClient<paths>({
  baseUrl: "",
  credentials: "include",
});
