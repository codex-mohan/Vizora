"""Image-first preprocessing and quality scoring."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageFilter, ImageStat, UnidentifiedImageError

from core.camera_state import CameraStateRegistry, FrameQuality
from core.config import Settings
from core.model_registry import ModelProfile
from pipeline.contracts import ImageQuality, MediaInput, PreprocessedImage


class PreprocessingService:
    def __init__(self, settings: Settings, camera_states: CameraStateRegistry) -> None:
        self._settings = settings
        self._camera_states = camera_states

    def run(self, media: MediaInput, profile: ModelProfile) -> PreprocessedImage:
        quality = self._score_quality(media.data)
        camera_mode = self._camera_states.update(
            media.camera_id,
            FrameQuality(
                brightness=quality.brightness,
                blur=quality.blur,
                haze=quality.haze,
                noise=quality.noise,
            ),
        )
        applied_steps = list(profile.preprocessing.always_on)

        if camera_mode.value == "LOWLIGHT" and profile.preprocessing.lowlight_model.value != "disabled":
            applied_steps.append(profile.preprocessing.lowlight_model.value)
        if camera_mode.value == "HAZE" and profile.preprocessing.haze_model.value != "disabled":
            applied_steps.append(profile.preprocessing.haze_model.value)
        if camera_mode.value == "RAIN" and profile.preprocessing.rain_model.value != "disabled":
            applied_steps.append(profile.preprocessing.rain_model.value)

        return PreprocessedImage(
            media=media,
            quality=quality,
            applied_steps=applied_steps,
            camera_mode=camera_mode.value,
        )

    def _score_quality(self, data: bytes) -> ImageQuality:
        try:
            image = Image.open(BytesIO(data)).convert("L")
        except UnidentifiedImageError:
            return ImageQuality(
                brightness=0.0,
                blur=0.0,
                haze=1.0,
                noise=0.0,
                score=0.0,
                review_required=True,
            )

        stat = ImageStat.Stat(image)
        brightness = float(stat.mean[0])
        blur = float(ImageStat.Stat(image.filter(ImageFilter.FIND_EDGES)).var[0])
        noise = float(stat.stddev[0])
        haze = max(0.0, min(1.0, 1.0 - (noise / 80.0)))

        brightness_score = 1.0 - min(abs(128.0 - brightness) / 128.0, 1.0)
        blur_score = min(blur / 2000.0, 1.0)
        contrast_score = min(noise / 64.0, 1.0)
        score = max(0.0, min(1.0, 0.4 * brightness_score + 0.35 * blur_score + 0.25 * contrast_score))

        return ImageQuality(
            brightness=brightness,
            blur=blur,
            haze=haze,
            noise=noise,
            score=score,
            review_required=score < 0.35,
        )
