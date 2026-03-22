"""Frigate API client."""

from __future__ import annotations

import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)


class FrigateClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url, timeout=timeout)

    def get_alerts(
        self,
        *,
        after: float | None = None,
        before: float | None = None,
        cameras: str = "all",
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch review items with severity=alert."""
        params: dict[str, Any] = {"severity": "alert", "cameras": cameras}
        if after is not None:
            params["after"] = after
        if before is not None:
            params["before"] = before
        if limit is not None:
            params["limit"] = limit

        resp = self.client.get("/api/review", params=params)
        resp.raise_for_status()
        return resp.json()

    def download_clip(
        self,
        camera: str,
        start_time: float,
        end_time: float,
        output_path: str,
        timeout: float = 120.0,
    ) -> None:
        """Download a recording clip as MP4.

        Uses the /api/{camera}/start/{start}/end/{end}/clip.mp4 endpoint
        which streams the MP4 directly.
        """
        url = f"/api/{camera}/start/{start_time}/end/{end_time}/clip.mp4"
        log.info("Downloading clip: %s (%.1fs)", url, end_time - start_time)

        with self.client.stream("GET", url, timeout=timeout) as resp:
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=65536):
                    f.write(chunk)

    def close(self):
        self.client.close()
