export const state = {
  // Use same-origin relative API routes so the frontend works when served by FastAPI.
  apiBase: "/api",
  currentQueryId: null,
  lastResponse: null,
};
