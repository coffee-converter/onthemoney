export type Confidence = 'high' | 'partial' | 'insufficient';

export interface Citation {
  label: string;
  url: string;
}

export interface Flow {
  state: string;
  total: string;
  count: number;
}

export interface OverlayPoint {
  lng: number;
  lat: number;
  value: number;
  color?: string | null;
  label?: string | null;
  tooltip?: string[];
}

export interface OverlayRegion {
  place: string; // district id, e.g. "AZ-01"
  value: number;
  color?: string | null; // explicit color (e.g. by party); else shaded by value
  label?: string | null; // text drawn on the district
  tooltip?: string[];
}

export interface Overlay {
  type: 'points' | 'regions';
  points?: OverlayPoint[];
  regions?: OverlayRegion[];
}

export interface Scene {
  camera: { type: string; lon: number; lat: number; zoom: number };
  highlight?: { state: string; district: string };
  flows: Flow[];
  overlays?: Overlay[]; // agent-composed custom layers (render_map)
  loading?: boolean; // district identified, funding still being fetched
}

export interface Candidate {
  cand_id?: string;
  name: string;
  party?: string;
  district?: string; // e.g. "IL-05"
  receipts?: string | null;
  individualTotal?: string | null;
}

export interface RosterCandidate {
  cand_id: string;
  name: string;
  party: string;
  itemized: string;
  receipts: string | null;
  individual_total: string | null;
}

export interface Answer {
  text: string;
  confidence: Confidence;
  total: string | null;
  receipts?: string | null;
  individual_total?: string | null;
  citations: Citation[];
  scene: Scene | null;
}

export interface PerTool {
  name: string;
  ms: number;
  ok: boolean;
}

export interface Telemetry {
  model: string;
  turns: number;
  tool_calls: number;
  tool_failures: number;
  input_tokens: number;
  output_tokens: number;
  elapsed_ms: number;
  per_tool: PerTool[];
  est_cost_usd: number;
}

export interface Step {
  type: 'tool_use' | 'tool_result' | 'text' | 'result' | 'answer' | 'telemetry';
  name?: string;
  input?: Record<string, unknown>;
  payload?: Record<string, unknown>;
  text?: string;
}

export interface ScoreboardData {
  item_count: number;
  accuracy: number;
  trajectory_accuracy: number;
  scene_accuracy: number;
  neutrality_accuracy: number;
  brier: number;
  by_regime?: Record<string, { count: number; accuracy: number }>;
  items: {
    id: string;
    correct: boolean;
    trajectory_ok: boolean;
    scene_ok: boolean;
    neutral_ok: boolean;
    confidence: string;
  }[];
  coverage?: {
    cycle: number;
    districts: number;
    candidates: number;
    contributions: number;
  };
}
