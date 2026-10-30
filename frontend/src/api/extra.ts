/**
 * Frontend-only API response shapes (not domain models).
 * Domain types live in ./types.ts and are generated from Pydantic.
 */

export interface PackSummary {
  pack_id: string;
  title: string;
  audience: string;
  item_count: number;
  high_risk_zones: string[];
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface CostsResponse {
  spent_usd: number;
  call_count: number;
  records: unknown[];
}

/** One place from GET /api/homes (Pass 3 spec 4.5). */
export interface HomeSummary {
  label: string;
  checkup_ids: string[];
  last_check_at: string;
  last_checkup_id: string;
  pack_ids: string[];
  open_fixes: number;
  open_findings: number;
  recheck_due: string;
}

export interface HomesResponse {
  homes: HomeSummary[];
}

/** Response of POST /checkups/{id}/captures (multipart upload). */
export interface CaptureUploadResponse {
  id: string;
  checkup_id: string;
  kind: string;
  keyframe_count: number;
  usable_keyframes: number;
}

/** One stored eval label from GET /checkups/{id}/reviews. */
export interface ReviewLabel {
  type: "verdict" | "missed";
  hazard_id?: string;
  item_id?: string | null;
  room?: string | null;
  mark?: "right" | "wrong";
  timestamp_s?: number | null;
  at?: string;
}

export interface ReviewsResponse {
  labels: ReviewLabel[];
  count: number;
}

export interface ReviewsSummary {
  total_labels: number;
  verdicts: number;
  missed: number;
  checkups: number;
}

/** GET /api/jobs/{id} - the persisted scan job the Processing page polls. */
export interface JobView {
  id: string;
  kind: string;
  steps: string[];
  status: string;
  completed_steps: string[];
  error?: string | null;
}

/** One item of a full pack (GET /api/packs/{pack_id}). */
export interface PackItemSummary {
  id: string;
  title: string;
}

export interface PackDetail {
  pack_id: string;
  title: string;
  items: PackItemSummary[];
}

/** Compiled custom checklist (POST /api/custom-checklists, Pass 3 P4). */
export interface CustomItem {
  id: string;
  title: string;
  kind: string;
  thin_object: boolean;
  sam_prompts: string[];
  safety_prompts: string[];
}

export interface CustomRefusal {
  line: string;
  reason: string;
}

export interface CustomChecklistResponse {
  checklist_id: string;
  label: string;
  source: string;
  items: CustomItem[];
  refusals: CustomRefusal[];
}
