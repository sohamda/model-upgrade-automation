"""Watch-list normalization helpers."""

from __future__ import annotations

from src.shared.config import AppConfig
from src.shared.contracts import WatchedModel


def load_watch_list(config: AppConfig) -> list[WatchedModel]:
    """Return configured watch-list entries in declaration order."""

    return list(config.watch_list)
