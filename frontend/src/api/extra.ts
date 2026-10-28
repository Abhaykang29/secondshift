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
