export type BBox = {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
};

export type DetectedObject = {
  id: string;
  label: string;
  bbox: BBox;
  confidence: number;
  metadata: Record<string, unknown>;
};

export type PlateResult = {
  plate_text: string | null;
  confidence: number;
  bbox: BBox | null;
  review_required: boolean;
};

export type ViolationPrediction = {
  violation_type: string;
  confidence: number;
  object_ids: string[];
  bbox: BBox | null;
  evidence: Record<string, unknown>;
  review_required: boolean;
  review_reasons: string[];
};

export type ProcessResult = {
  request_id: string;
  camera_id: string;
  timestamp: string;
  mode: "still_image" | "temporal_burst";
  quality: {
    brightness: number;
    blur: number;
    haze: number;
    noise: number;
    score: number;
    review_required: boolean;
  };
  detections: DetectedObject[];
  tracks: unknown[];
  poses: unknown[];
  plates: PlateResult[];
  violations: ViolationPrediction[];
  evidence_packet_id: string;
  model_profile: string;
  review_required: boolean;
  review_reasons: string[];
  description: string | null;
};

export interface ViolationListItem {
  id: string;
  violation_type: string;
  confidence: number;
  camera_id: string;
  location: string;
  timestamp: string;
  vehicle_class: string | null;
  plate: string | null;
  plate_hash: string | null;
  description: string | null;
  evidence_packet_id: string | null;
  review_required: boolean;
  status?: string;
}

export interface ViolationListResponse {
  items: ViolationListItem[];
  total: number;
  page: number;
  size: number;
}

export interface EvidencePacket {
  packet_id: string;
  violation_id: string;
  frame_urls: string[];
  plate_crop_url: string | null;
  annotated_frame_url: string | null;
  vlm_description: string | null;
  hash_chain: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  violation?: ViolationListItem;
}

export interface AnalyticsSummary {
  total_violations: number;
  by_type: Record<string, number>;
  by_hour: Record<string, number>;
  trend: Array<{ date: string; count: number }>;
  avg_confidence: number;
  review_queue_depth: number;
  active_cameras: number;
  violations_today: number;
}

export interface Hotspot {
  location_name: string;
  latitude: number | null;
  longitude: number | null;
  violation_count: number;
}

export interface RepeatOffender {
  plate_text: string;
  plate_hash: string;
  violation_count: number;
  last_seen_at: string;
  violation_types: string[];
}

export interface HeatmapCell {
  day: number;
  hour: number;
  count: number;
}

export interface CameraInfo {
  id: string;
  name: string;
  location_name: string | null;
  latitude: number | null;
  longitude: number | null;
  current_mode: string;
  status: string;
  created_at: string;
}
