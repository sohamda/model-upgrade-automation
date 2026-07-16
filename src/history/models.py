"""History-local models for dry-run previews."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.shared.contracts import ArtifactManifest, SkipIndexKey


@dataclass(slots=True)
class HistoryPreview:
    """Manifest and skip-index previews produced during dry-run."""

    manifests: list[ArtifactManifest] = field(default_factory=list)
    skip_index_keys: list[SkipIndexKey] = field(default_factory=list)
