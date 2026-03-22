"""Configuration handling for Frigate Connect.

Reads from /data/options.json (HA addon) or environment variables (standalone).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

OPTIONS_PATH = Path("/data/options.json")
LOCAL_OPTIONS_PATH = Path("options.json")
STATE_PATH = Path("/data/state.json") if Path("/data").exists() else Path("state.json")


@dataclass
class Config:
    frigate_url: str
    poll_interval: int
    clip_padding: int
    output_dir: str
    max_clip_duration: int
    video_profile: str  # "compatible" or "passthrough"

    @classmethod
    def load(cls) -> Config:
        for p in (OPTIONS_PATH, LOCAL_OPTIONS_PATH):
            if p.exists():
                with open(p) as f:
                    opts = json.load(f)
                break
        else:
            opts = {}

        return cls(
            frigate_url=opts.get("frigate_url", os.environ.get("FRIGATE_URL", "http://localhost:5000")).rstrip("/"),
            poll_interval=int(opts.get("poll_interval", os.environ.get("POLL_INTERVAL", "60"))),
            clip_padding=int(opts.get("clip_padding", os.environ.get("CLIP_PADDING", "10"))),
            output_dir=opts.get("output_dir", os.environ.get("OUTPUT_DIR", "/media/frigateconnect")),
            max_clip_duration=int(opts.get("max_clip_duration", os.environ.get("MAX_CLIP_DURATION", "300"))),
            video_profile=opts.get("video_profile", os.environ.get("VIDEO_PROFILE", "compatible")),
        )
