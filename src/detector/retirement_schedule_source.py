"""Live retirement schedule source backed by Microsoft Learn content."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Final
from urllib.error import URLError
from urllib.request import Request, urlopen

from src.shared.contracts import RetiringModel
from src.shared.errors import DependencyUnavailableError

LEARN_RETIREMENT_URL: Final[str] = (
    "https://raw.githubusercontent.com/MicrosoftDocs/azure-ai-docs-pr/live/articles/foundry/openai/concepts/model-retirement-schedule.md"
)


@dataclass(slots=True)
class LearnRetirementScheduleSource:
    """Fetch and parse retirement signals from Microsoft Learn markdown/HTML pages."""

    url: str = LEARN_RETIREMENT_URL
    timeout_seconds: int = 20

    def _fetch_text(self) -> str:
        request = Request(self.url, headers={"User-Agent": "model-upgrade-automation/0.1"})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except URLError as error:
            raise DependencyUnavailableError(
                "Failed to fetch live retirement schedule from Microsoft Learn. "
                f"Check network access and URL reachability: {self.url}"
            ) from error
        if not raw.strip():
            raise DependencyUnavailableError(
                f"Live retirement schedule returned empty content: {self.url}"
            )
        return raw

    def _parse_rows(self, text: str) -> list[RetiringModel]:
        rows: list[RetiringModel] = []
        table_row_pattern = re.compile(
            r"\|\s*(gpt-[^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|",
            re.IGNORECASE,
        )
        for model_id, version, retirement_date in table_row_pattern.findall(text):
            parsed_date = retirement_date.strip()
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", parsed_date)
            if date_match:
                parsed_date = date_match.group(1)
            else:
                try:
                    parsed_date = datetime.strptime(parsed_date[:12].strip(), "%b %d, %Y").date().isoformat()
                except ValueError:
                    continue
            rows.append(
                RetiringModel(
                    model_id=model_id.strip(),
                    current_version=version.strip(),
                    retirement_date=parsed_date,
                    replacement_family=model_id.strip().split("-")[0] + "-4.1",
                    source=self.url,
                )
            )
        if not rows:
            raise DependencyUnavailableError(
                "Unable to parse retirement rows from Microsoft Learn content. "
                "Validate that the page format has not changed and update parser accordingly."
            )
        return rows

    def load(self) -> list[RetiringModel]:
        """Load live retirement entries."""

        text = self._fetch_text()
        loaded = self._parse_rows(text)
        fetched_at = datetime.now(timezone.utc).isoformat()
        for entry in loaded:
            entry.source = f"{self.url}#fetched={fetched_at}"
        return loaded
