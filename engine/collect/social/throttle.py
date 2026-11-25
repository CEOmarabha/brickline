"""Per-account rate limits, jitter, and a small on-disk request log."""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from engine.collect.social.config import env

PREFIX = {"facebook": "FB", "instagram": "IG", "tiktok": "TIKTOK"}
STATE = Path("data/raw/social_throttle.json")


@dataclass
class Throttle:
    name: str
    min_delay: float = 10.0
    max_delay: float = 24.0
    max_per_run: int = 30
    max_per_hour: int = 60

    def __post_init__(self) -> None:
        self._run = 0
        self._last = 0.0
        prefix = PREFIX.get(self.name, self.name.upper())
        if raw := env(f"{prefix}_MIN_DELAY"):
            self.min_delay = float(raw)
        if raw := env(f"{prefix}_MAX_DELAY"):
            self.max_delay = float(raw)
        if raw := env(f"{prefix}_MAX_PER_RUN"):
            self.max_per_run = int(raw)
        if raw := env(f"{prefix}_MAX_PER_HOUR"):
            self.max_per_hour = int(raw)

    def remaining(self) -> int:
        return max(0, self.max_per_run - self._run)

    def allow(self) -> bool:
        if self._run >= self.max_per_run:
            return False
        hour_ago = datetime.now(UTC) - timedelta(hours=1)
        stamps = [s for s in _load().get(self.name, []) if datetime.fromisoformat(s) >= hour_ago]
        return len(stamps) < self.max_per_hour

    def wait(self, sleep=time.sleep) -> None:
        if self._last:
            gap = random.uniform(self.min_delay, self.max_delay)
            elapsed = time.monotonic() - self._last
            if elapsed < gap:
                sleep(gap - elapsed)
        self._last = time.monotonic()
        self._run += 1
        _record(self.name)


def _load() -> dict:
    if not STATE.is_file():
        return {}
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _record(name: str) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    data = _load()
    stamps = data.get(name, [])
    stamps.append(datetime.now(UTC).isoformat())
    data[name] = stamps[-200:]
    STATE.write_text(json.dumps(data), encoding="utf-8")
