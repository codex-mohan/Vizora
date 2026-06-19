"""VLM evidence-description adapter with template fallback."""

from __future__ import annotations

from datetime import datetime

from core.model_registry import Runtime, VlmChoice, VlmConfig
from pipeline.contracts import InferenceResult, ViolationClass


VIOLATION_TEMPLATES = {
    ViolationClass.HELMET: "Rider detected without helmet compliance.",
    ViolationClass.SEATBELT: "Driver detected without seatbelt compliance.",
    ViolationClass.TRIPLE_RIDE: "Triple riding detected on a two-wheeler.",
    ViolationClass.WRONG_SIDE: "Vehicle detected traveling in the wrong direction.",
    ViolationClass.STOP_LINE: "Vehicle detected crossing the stop line.",
    ViolationClass.RED_LIGHT: "Vehicle detected running a red signal.",
    ViolationClass.ILLEGAL_PARKING: "Vehicle detected parked in a restricted zone.",
}


class VlmDescriber:
    def __init__(self, config: VlmConfig) -> None:
        self.config = config

    @property
    def ready(self) -> bool:
        if not self.config.enabled or self.config.choice == VlmChoice.DISABLED:
            return False
        if self.config.runtime == Runtime.EXTERNAL_API:
            return self.config.endpoint_url is not None
        return bool(self.config.weights)

    def describe(self, result: InferenceResult) -> str | None:
        if self.config.runtime == Runtime.EXTERNAL_API:
            return self._call_external_api(result)
        return self._template_description(result)

    def _template_description(self, result: InferenceResult) -> str:
        ts = result.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        det_count = len(result.detections)
        veh_count = sum(1 for d in result.detections if d.label.value in ("car", "motorcycle", "bus", "truck", "auto"))
        plate_texts = [p.plate_text for p in result.plates if p.plate_text]
        plate_str = ", ".join(plate_texts) if plate_texts else "not extracted"

        violation_parts: list[str] = []
        for v in result.violations:
            desc = VIOLATION_TEMPLATES.get(v.violation_type, v.violation_type.value)
            violation_parts.append(f"{desc} (confidence {v.confidence:.0%})")

        violations_str = " ".join(violation_parts) if violation_parts else "No violations detected."

        return (
            f"At {ts}, camera {result.camera_id} captured an image with {det_count} detected objects "
            f"({veh_count} vehicles). Plate candidates: {plate_str}. "
            f"Violations: {violations_str} "
            f"Evidence quality score: {result.quality.score:.0%}. "
            f"Human review {'required' if result.review_required else 'not required'}. "
            f"Evidence packet: {result.evidence_packet_id}."
        )

    def _call_external_api(self, result: InferenceResult) -> str | None:
        import httpx
        try:
            prompt = self._build_prompt(result)
            resp = httpx.post(
                self.config.endpoint_url,
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content")
        except Exception:
            return self._template_description(result)

    def _build_prompt(self, result: InferenceResult) -> str:
        ts = result.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        plates = [p.plate_text for p in result.plates if p.plate_text]
        violations = [v.violation_type.value for v in result.violations]
        return (
            f"You are a traffic enforcement analyst. Write a concise evidence summary.\n"
            f"Camera: {result.camera_id}\nTime: {ts}\n"
            f"Objects detected: {len(result.detections)}\n"
            f"Plates: {', '.join(plates) if plates else 'none'}\n"
            f"Violations: {', '.join(violations) if violations else 'none'}\n"
            f"Confidence: {result.quality.score:.0%}\n"
            f"Write one paragraph describing the scene and findings."
        )


def build_vlm_describer(config: VlmConfig) -> VlmDescriber:
    return VlmDescriber(config)
