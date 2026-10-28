/**
 * Typed API client for the SecondShift backend.
 * Thin fetch wrappers only - pages own their own state.
 */
import type { CostsResponse, HealthResponse, PackSummary } from "./extra";
import type { Checkup, FixCard, Report } from "./types";

const BASE = "/api";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return (await res.json()) as T;
}

async function sendJson<T>(path: string, method: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${method} ${path} failed: ${res.status} ${await res.text()}`);
  return (await res.json()) as T;
}

export const api = {
  health: () => getJson<HealthResponse>("/health"),
  packs: () => getJson<{ packs: PackSummary[] }>("/packs"),
  costs: () => getJson<CostsResponse>("/costs"),
  report: (checkupId: string) => getJson<Report>(`/reports/${checkupId}`),
  share: (checkupId: string) =>
    getJson<{ text: string; whatsapp_url: string }>(`/reports/${checkupId}/share`),
  createCheckup: (body: unknown) => sendJson<Checkup>("/checkups", "POST", body),
  scan: (checkupId: string, scenario?: string) =>
    sendJson<{ job_id: string; job_status: string; report: Report }>(
      `/checkups/${checkupId}/scan`, "POST", scenario ? { scenario } : {},
    ),
  updateFix: (checkupId: string, fixId: string, status: string, note?: string) =>
    sendJson<FixCard>(`/reports/${checkupId}/fixes/${fixId}`, "PATCH", { status, note }),
  compileRule: (text: string, modeHint: string) =>
    sendJson<Record<string, unknown>>("/rules/compile", "POST", { text, mode_hint: modeHint }),
  recheck: (checkupId: string, scenario: string) =>
    sendJson<Record<string, unknown>>(`/checkups/${checkupId}/recheck`, "POST", { scenario }),
  evalLatest: () => getJson<Record<string, unknown>>("/eval/latest"),
  imageUrl: (checkupId: string, name: string) => `${BASE}/reports/${checkupId}/image/${name}`,
};
