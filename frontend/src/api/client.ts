/**
 * Typed API client for the SecondShift backend.
 * Thin fetch wrappers only - pages own their own state.
 */
import type { CostsResponse, HealthResponse, PackSummary } from "./extra";
import type { Report } from "./types";

const BASE = "/api";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return (await res.json()) as T;
}

export const api = {
  health: () => getJson<HealthResponse>("/health"),
  packs: () => getJson<{ packs: PackSummary[] }>("/packs"),
  costs: () => getJson<CostsResponse>("/costs"),
  report: (checkupId: string) => getJson<Report>(`/reports/${checkupId}`),
};
