from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train RT-DETRv2 accuracy detector through the official PyTorch repo.")
    parser.add_argument("--config", type=Path, default=Path("configs/training.yaml"))
    parser.add_argument("--weights-dir", type=Path, default=None)
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--vol-root", type=Path, default=None)
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--smoke", action="store_true", help="Create a tiny checkpoint/manifest to verify Modal plumbing.")
    parser.add_argument("--device", type=str, default=None)
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def config_hash(cfg: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()


def atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def copy_checkpoint(src: Path, weights_dir: Path, best_name: str = "best.pt") -> dict[str, str]:
    weights_dir.mkdir(parents=True, exist_ok=True)
    copied: dict[str, str] = {}
    if src.exists():
        best = weights_dir / best_name
        last = weights_dir / "last.pt"
        shutil.copy2(src, best)
        shutil.copy2(src, last)
        copied["best.pt"] = str(best)
        copied["last.pt"] = str(last)
    return copied


def write_manifest(
    cfg: dict[str, Any],
    model_cfg: dict[str, Any],
    run_dir: Path,
    weights_dir: Path,
    copied_weights: dict[str, str],
    status: str,
    detail: str | None = None,
) -> None:
    metrics = {"status": status}
    if detail:
        metrics["detail"] = detail
    manifest = {
        "model_name": "accuracy_detector",
        "model_arch": model_cfg.get("model", "rtdetrv2_s"),
        "framework": "rtdetrv2_pytorch",
        "task": "object_detection",
        "prediction_contract": cfg.get("runtime_contract", {}),
        "traffic_classes": cfg.get("traffic_classes", []),
        "config_hash": config_hash(cfg),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(run_dir),
        "weights": copied_weights,
        "status": status,
        "detail": detail,
    }
    atomic_json(run_dir / "metrics.json", metrics)
    atomic_json(run_dir / "manifest.json", manifest)
    atomic_json(weights_dir / "metrics.json", metrics)
    atomic_json(weights_dir / "manifest.json", manifest)


def run_smoke(cfg: dict[str, Any], model_cfg: dict[str, Any], run_dir: Path, weights_dir: Path) -> None:
    import torch

    run_dir.mkdir(parents=True, exist_ok=True)
    ckpt = run_dir / "rtdetrv2_smoke.pt"
    torch.save(
        {
            "model": "rtdetrv2_smoke",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "prediction_contract": cfg.get("runtime_contract", {}),
            "classes": cfg.get("traffic_classes", []),
        },
        ckpt,
    )
    copied = copy_checkpoint(ckpt, weights_dir)
    write_manifest(cfg, model_cfg, run_dir, weights_dir, copied, status="smoke_ok")
    console.print(f"[green]RT-DETRv2 smoke artifact written to {weights_dir}[/green]")


def find_checkpoint(run_dir: Path) -> Path | None:
    candidates = [
        *run_dir.rglob("best*.pt"),
        *run_dir.rglob("best*.pth"),
        *run_dir.rglob("checkpoint*.pt"),
        *run_dir.rglob("checkpoint*.pth"),
    ]
    return candidates[0] if candidates else None


def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    cfg = load_config(config_path)
    model_cfg = cfg["accuracy_detector"]

    def _handle_stop(signum, frame):
        raise KeyboardInterrupt(f"received signal {signum}")

    signal.signal(signal.SIGTERM, _handle_stop)

    vol_root = args.vol_root
    run_dir = (args.run_dir or ((vol_root / "runs" if vol_root else Path("runs")) / "accuracy_detector")).resolve()
    weights_dir = (args.weights_dir or (vol_root / "weights" / "accuracy_detector" if vol_root else run_dir / "exported_weights")).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    weights_dir.mkdir(parents=True, exist_ok=True)

    if args.smoke:
        run_smoke(cfg, model_cfg, run_dir, weights_dir)
        return

    repo_dir = Path(model_cfg["repo_dir"])
    train_script = repo_dir / model_cfg["train_script"]
    rt_config = repo_dir / model_cfg["config_path"]
    if not repo_dir.exists() or not train_script.exists() or not rt_config.exists():
        detail = (
            "RT-DETRv2 repo/config missing. Expected "
            f"repo={repo_dir}, train_script={train_script}, config={rt_config}. "
            "Mount or clone the official RT-DETR repo into the Modal volume before real training."
        )
        write_manifest(cfg, model_cfg, run_dir, weights_dir, {}, status="blocked", detail=detail)
        raise FileNotFoundError(detail)

    cmd = [
        sys.executable,
        str(train_script),
        "-c",
        str(rt_config),
        "--output-dir",
        str(run_dir),
    ]
    if args.device:
        cmd.extend(["--device", args.device])

    console.rule("[bold magenta]Training RT-DETRv2 Accuracy Detector")
    console.print(" ".join(cmd))
    try:
        result = subprocess.run(cmd, cwd=str(repo_dir), text=True, capture_output=True, check=False)
        (run_dir / "stdout.log").write_text(result.stdout, encoding="utf-8")
        (run_dir / "stderr.log").write_text(result.stderr, encoding="utf-8")
        if result.returncode != 0:
            detail = result.stderr[-2000:] or f"RT-DETRv2 training exited {result.returncode}"
            write_manifest(cfg, model_cfg, run_dir, weights_dir, {}, status="failed", detail=detail)
            sys.exit(result.returncode)
    except KeyboardInterrupt as exc:
        console.print(f"[yellow]Training interrupted: {exc}. Saving available checkpoint.[/yellow]")

    checkpoint = find_checkpoint(run_dir)
    if checkpoint is None:
        detail = "RT-DETRv2 training completed but no checkpoint was found."
        write_manifest(cfg, model_cfg, run_dir, weights_dir, {}, status="failed", detail=detail)
        raise FileNotFoundError(detail)

    copied = copy_checkpoint(checkpoint, weights_dir)
    write_manifest(cfg, model_cfg, run_dir, weights_dir, copied, status="ok")
    console.print(f"[green]Done. RT-DETRv2 weights copied to {weights_dir}[/green]")


if __name__ == "__main__":
    main()
