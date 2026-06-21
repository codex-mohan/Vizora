"""Shared device detection for GPU inference."""

from __future__ import annotations

import logging
import torch

logger = logging.getLogger(__name__)

_device: str | None = None
_half: bool | None = None


def get_device() -> str:
    global _device
    if _device is None:
        if torch.cuda.is_available():
            _device = "cuda:0"
            name = torch.cuda.get_device_name(0)
            mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            logger.info("GPU detected: %s (%.1f GB)", name, mem)
        else:
            _device = "cpu"
            logger.info("No GPU available, using CPU")
    return _device


def use_half() -> bool:
    global _half
    if _half is None:
        dev = get_device()
        if dev.startswith("cuda"):
            _half = True
            logger.info("FP16 half precision enabled")
        else:
            _half = False
    return _half


def get_torch_device() -> torch.device:
    return torch.device(get_device())
