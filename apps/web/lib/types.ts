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

export interface Scene {
  camera: { type: string; lon: number; lat: number; zoom: number };
  highlight: { state: string; district: string };
  flows: Flow[];
  loading?: boolean; // district identified, funding still being fetched
}

export interface Candidate {
  name: string;
  party?: string;
  district?: string; // e.g. "IL-05"
  receipts?: string | null;
  individualTotal?: string | null;
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

export interface Step {
  type: 'tool_use' | 'tool_result' | 'text' | 'result' | 'answer';
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
