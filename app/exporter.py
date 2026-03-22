"""Video export and conversion logic."""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from config import Config, STATE_PATH
from frigate_client import FrigateClient

log = logging.getLogger(__name__)


def load_state() -> set[str]:
    """Load set of already-exported review IDs."""
    if STATE_PATH.exists():
        data = json.loads(STATE_PATH.read_text())
        return set(data.get("exported_ids", []))
    return set()


def save_state(exported_ids: set[str]) -> None:
    """Persist exported review IDs."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps({"exported_ids": sorted(exported_ids)}))


def reencode_clip(input_path: str, output_path: str) -> None:
    """Re-encode video to universally compatible MP4.

    Uses H.264 Baseline profile with AAC audio. This ensures playback on
    virtually all devices including older phones, smart TVs, and browsers.
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-c:v", "libx264",
        "-profile:v", "baseline",
        "-level", "3.1",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ]
    log.info("Re-encoding: %s -> %s", input_path, output_path)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        log.error("ffmpeg failed: %s", result.stderr)
        raise RuntimeError(f"ffmpeg re-encode failed: {result.stderr[-500:]}")


def build_filename(camera: str, start_time: float, alert_id: str) -> str:
    """Build a descriptive filename for the exported clip."""
    dt = datetime.fromtimestamp(start_time, tz=timezone.utc)
    ts = dt.strftime("%Y%m%d_%H%M%S")
    short_id = alert_id[:8]
    return f"{camera}_{ts}_{short_id}.mp4"


def export_alert(
    client: FrigateClient,
    alert: dict,
    config: Config,
) -> str | None:
    """Export a single alert as a compatible MP4 clip.

    Returns the output file path on success, None on failure.
    """
    alert_id = alert["id"]
    camera = alert["camera"]
    start_time = alert["start_time"]
    end_time = alert.get("end_time")

    if end_time is None:
        log.info("Skipping in-progress alert %s", alert_id)
        return None

    duration = end_time - start_time
    if duration > config.max_clip_duration:
        log.warning(
            "Alert %s duration %.0fs exceeds max %ds, skipping",
            alert_id, duration, config.max_clip_duration,
        )
        return None

    padded_start = start_time - config.clip_padding
    padded_end = end_time + config.clip_padding

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = build_filename(camera, start_time, alert_id)
    final_path = output_dir / filename

    with tempfile.TemporaryDirectory() as tmpdir:
        raw_path = f"{tmpdir}/raw.mp4"

        try:
            client.download_clip(camera, padded_start, padded_end, raw_path)
        except Exception:
            log.exception("Failed to download clip for alert %s", alert_id)
            return None

        if config.video_profile == "passthrough":
            Path(raw_path).rename(final_path)
        else:
            try:
                reencode_clip(raw_path, str(final_path))
            except Exception:
                log.exception("Failed to re-encode clip for alert %s", alert_id)
                return None

    objects = alert.get("data", {}).get("objects", [])
    log.info(
        "Exported alert %s: camera=%s objects=%s duration=%.0fs -> %s",
        alert_id, camera, objects, duration, final_path,
    )
    return str(final_path)
