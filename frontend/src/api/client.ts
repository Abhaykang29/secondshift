/**
 * Typed API client for the SecondShift backend.
 * Thin fetch wrappers only - pages own their own state.
 */
import type {
  CaptureUploadResponse,
  CostsResponse,
  CustomChecklistResponse,
  HealthResponse,
  HomesResponse,
  JobView,
  PackDetail,
  PackSummary,
  ReviewsResponse,
  ReviewsSummary,
} from "./extra";
import type { Checkup, FixCard, Keyframe, Report } from "./types";

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

async function postForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status} ${await res.text()}`);
  return (await res.json()) as T;
}

async function deleteJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`DELETE ${path} failed: ${res.status} ${await res.text()}`);
  return (await res.json()) as T;
}

export const api = {
  health: () => getJson<HealthResponse>("/health"),
  packs: () => getJson<{ packs: PackSummary[] }>("/packs"),
  pack: (packId: string) => getJson<PackDetail>(`/packs/${packId}`),
  costs: () => getJson<CostsResponse>("/costs"),
  settings: () =>
    getJson<{ provider_mode: string; credits_mode?: string }>("/settings"),
  homes: () => getJson<HomesResponse>("/homes"),
  deleteHome: (label: string) =>
    deleteJson<{ deleted_checkups: number }>(`/homes/${encodeURIComponent(label)}`),
  job: (jobId: string) => getJson<JobView>(`/jobs/${jobId}`),
  keyframes: (captureId: string) =>
    getJson<{ keyframes: Keyframe[] }>(`/captures/${captureId}/keyframes`),
  uploadCapture: (checkupId: string, file: File, kind: "walkthrough" | "routine") => {
    const form = new FormData();
    form.append("file", file);
    form.append("kind", kind);
    form.append("source", "phone_upload");
    return postForm<CaptureUploadResponse>(`/checkups/${checkupId}/captures`, form);
  },
  reviews: (checkupId: string) =>
    getJson<ReviewsResponse>(`/checkups/${checkupId}/reviews`),
  postReview: (checkupId: string, hazardId: string, mark: "right" | "wrong") =>
    sendJson<{ stored: boolean; total_labels: number }>(
      `/checkups/${checkupId}/reviews`, "POST", { hazard_id: hazardId, mark },
    ),
  postMissed: (
    checkupId: string,
    body: { item_id: string; room: string; timestamp_s: number | null },
  ) =>
    sendJson<{ stored: boolean; total_labels: number }>(
      `/checkups/${checkupId}/missed`, "POST", body,
    ),
  reviewsSummary: () => getJson<ReviewsSummary>("/reviews/summary"),
  compileCustom: (lines: string[]) =>
    sendJson<CustomChecklistResponse>("/custom-checklists", "POST", { lines }),
  report: (checkupId: string) => getJson<Report>(`/reports/${checkupId}`),
  share: (checkupId: string) =>
    getJson<{ text: string; whatsapp_url: string }>(`/reports/${checkupId}/share`),
  createCheckup: (body: unknown) => sendJson<Checkup>("/checkups", "POST", body),
  scan: (checkupId: string, scenario?: string, captureId?: string) =>
    sendJson<{ job_id: string; job_status: string; report: Report }>(
      `/checkups/${checkupId}/scan`,
      "POST",
      {
        ...(scenario ? { scenario } : {}),
        ...(captureId ? { capture_id: captureId } : {}),
      },
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
