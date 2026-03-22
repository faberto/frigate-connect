"""Frigate Connect - Export Frigate alert clips as compatible MP4 videos."""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

# Allow imports to work both from /app/ (container) and project root (local dev)
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from exporter import export_alert, load_state, save_state
from frigate_client import FrigateClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("frigateconnect")


def poll_and_export(client: FrigateClient, config: Config) -> None:
    """Single poll cycle: fetch new alerts and export them."""
    exported_ids = load_state()

    try:
        alerts = client.get_alerts()
    except Exception:
        log.exception("Failed to fetch alerts from Frigate")
        return

    new_alerts = [a for a in alerts if a["id"] not in exported_ids]
    if not new_alerts:
        log.debug("No new alerts")
        return

    log.info("Found %d new alert(s)", len(new_alerts))

    for alert in new_alerts:
        result = export_alert(client, alert, config)
        if result is not None:
            exported_ids.add(alert["id"])
            save_state(exported_ids)


def main() -> None:
    config = Config.load()
    os.environ["TZ"] = config.timezone
    time.tzset()
    log.info(
        "Starting Frigate Connect: frigate_url=%s poll_interval=%ds padding=%ds profile=%s output=%s",
        config.frigate_url,
        config.poll_interval,
        config.clip_padding,
        config.video_profile,
        config.output_dir,
    )

    client = FrigateClient(config.frigate_url)

    try:
        while True:
            poll_and_export(client, config)
            time.sleep(config.poll_interval)
    except KeyboardInterrupt:
        log.info("Shutting down")
    finally:
        client.close()


if __name__ == "__main__":
    main()
