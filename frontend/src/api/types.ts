/**
 * GENERATED from the Pydantic domain schemas by scripts/generate_types.py.
 * Do not edit by hand - run `make types`. The drift test fails on any diff.
 * Frontend-only response shapes live in ./extra.ts.
 */

export type Mode = "checkup" | "watch";
export type CaptureKind = "walkthrough" | "routine" | "recheck";
export type ItemKind = "presence" | "absence" | "interaction" | "measurement";
export type Severity = 1 | 2 | 3;
export type Verification = "confirmed" | "needs_human" | "rejected" | "cannot_assess";
export type RecheckStatus = "resolved" | "still_present" | "new" | "cannot_tell";
export type Outcome = "met" | "not_met" | "cannot_tell";
export type CompileStatus = "compiled" | "refused" | "needs_clarification";
export type Primitive = "object_present" | "object_absent" | "object_state" | "state_for_duration" | "zone_empty_for_duration" | "event_by_deadline" | "camera_health";
export type RuleState = "idle" | "watching" | "pending" | "alert" | "cannot_see";
export type ProviderName = "mock" | "meta" | "local";
export type CacheMode = "off" | "record" | "replay" | "auto";

export interface CannotAssess {
  area: string;
  reason: "not_filmed" | "too_dark" | "too_blurry" | "occluded" | "needs_measurement" | "not_visible_by_design";
  detail: string;
}

export interface Capture {
  id: string;
  checkup_id: string;
  kind: CaptureKind;
  file_path?: string | null;
  duration_s: number;
  width: number;
  height: number;
  fps: number;
  source: "phone_upload" | "phone_record" | "rayban_import" | "synthetic";
}

export interface Checkup {
  id: string;
  created_at: string;
  pack_ids: string[];
  resident_label?: string | null;
  language?: string;
  consent: Consent;
}

export interface Condition {
  primitive: Primitive;
  target?: string | null;
  target_state?: string | null;
  anchor?: string | null;
  area_hint?: string | null;
  duration_min?: number | null;
  deadline_local?: string | null;
}

export interface Consent {
  resident_informed: boolean;
  no_private_moments: boolean;
  retention_days?: number;
  keep_raw_video?: boolean;
}

export interface EvalCapture {
  capture_id: string;
  video_path: string;
  pack_ids: string[];
  hazards: GroundTruthHazard[];
  unassessable?: string[];
}

export interface EvalRunSummary {
  config_name: string;
  precision: number;
  recall: number;
  f1: number;
  confirmed_precision: number;
  needs_human_rate: number;
  cannot_assess_rate: number;
  cost_usd_per_scan: number;
  latency_s_per_scan: number;
  per_item: Record<string, Record<string, number>>;
}

export interface Evidence {
  keyframe_ids: string[];
  timestamps: number[];
  masks?: Mask[];
  narration_notes?: string[];
  measurement_ids?: string[];
}

export interface FixCard {
  id: string;
  hazard_id: string;
  chosen: FixOption;
  alternatives: FixOption[];
  plain_language_steps: string[];
  status?: "todo" | "done" | "skipped";
  note?: string | null;
}

export interface FixOption {
  id: string;
  title: string;
  how: string;
  difficulty: "easy" | "medium" | "pro";
  cost_estimate: string;
  visualization_prompt?: string | null;
}

export interface GroundTruthHazard {
  item_id: string;
  room: string;
  time_ranges: [number, number][];
  note?: string | null;
}

export interface Hazard {
  id: string;
  checkup_id: string;
  pack_id: string;
  pack_tags?: string[];
  item_id: string;
  kind: ItemKind;
  room: string;
  title: string;
  description: string;
  why_it_matters: string;
  severity: Severity;
  on_routine_path?: boolean;
  verification: Verification;
  verification_reason: string;
  evidence: Evidence;
  risk_score: number;
  rank?: number | null;
}

export interface HazardProposal {
  item_id: string;
  room: string;
  description: string;
  evidence_timestamps: number[];
  source_keyframe_ids?: string[];
  sam_prompts: string[];
  safety_prompts?: string[];
  confidence: number;
  why_risky: string;
  observed_interaction?: string | null;
}

export interface Keyframe {
  id: string;
  capture_id: string;
  t: number;
  image_path: string;
  sharpness: number;
  brightness: number;
  usable: boolean;
  room_guess?: string | null;
  room_confidence?: number | null;
}

export interface Mask {
  keyframe_id: string;
  polygon?: [number, number][] | null;
  rle?: string | null;
  bbox: [number, number, number, number];
  score: number;
  prompt: string;
}

export interface Measurement {
  id: string;
  checkup_id: string;
  label: string;
  value: number;
  unit: string;
  note?: string | null;
}

export interface NarrationFact {
  fact: string;
  t: number;
  affects?: string[];
}

export interface NarrationSegment {
  capture_id: string;
  t_start: number;
  t_end: number;
  text: string;
  language?: string | null;
}

export interface Recheck {
  id: string;
  checkup_id: string;
  capture_id: string;
  created_at: string;
  items: RecheckItem[];
  rule_outcomes?: RuleOutcome[];
  score_before: number;
  score_after: number;
}

export interface RecheckItem {
  hazard_id: string | null;
  item_id: string;
  room: string;
  status: RecheckStatus;
  reason: string;
  before_keyframe_id: string | null;
  after_keyframe_id: string | null;
}

export interface Report {
  checkup_id: string;
  generated_at: string;
  pack_ids: string[];
  summary: string;
  fix_first: string[];
  hazards: Hazard[];
  fixes: FixCard[];
  visualizations: Visualization[];
  routine_insights: RoutineInsight[];
  cannot_assess: CannotAssess[];
  stats: Record<string, number>;
  disclaimer: string;
}

export interface RoutineInsight {
  id: string;
  checkup_id: string;
  kind: "support_contact" | "path_obstacle" | "low_seat_difficulty" | "reaching_high" | "dark_path";
  summary: string;
  count?: number | null;
  related_hazard_ids?: string[];
  evidence: Evidence;
}

export interface RuleOutcome {
  rule_id: string;
  outcome: Outcome;
  reason: string;
  evidence?: Evidence | null;
  evaluated_at: string;
}

export interface RuleSpec {
  id: string;
  original_text: string;
  status: CompileStatus;
  mode: Mode | string;
  conditions: Condition[];
  schedule?: Schedule | null;
  evidence_policy?: Record<string, number>;
  notify?: "app" | "hub_voice" | "whatsapp_share"[];
  human_summary: string;
  clarifying_question?: string | null;
  refusal_reason?: string | null;
  alternatives?: string[];
  compiler_version?: string;
}

export interface Schedule {
  days?: "mon" | "tue" | "wed" | "thu" | "fri" | "sat" | "sun"[];
  start_local?: string | null;
  end_local?: string | null;
}

export interface Visualization {
  id: string;
  hazard_id: string;
  source_keyframe_id: string;
  image_path: string;
  prompt_used: string;
  watermark?: string;
}

export interface WatchEvent {
  id: string;
  source_id: string;
  rule_id: string;
  at: string;
  state_from: RuleState;
  state_to: RuleState;
  outcome: Outcome;
  reason: string;
  thumbnail_path?: string | null;
}

export interface WatchSource {
  id: string;
  kind: "phone" | "rtsp" | "file";
  label: string;
  rtsp_url?: string | null;
  roi?: [number, number, number, number] | null;
  room_type?: string | null;
  privacy_ok?: boolean;
  resident_consent?: boolean;
}
