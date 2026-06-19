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
