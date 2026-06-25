"""Dialog controller for VectorTrackScript summary UI."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class DialogState:
    project_name: str = ""
    client_name: str = ""
    budget_hours: float = 0.0
    trust_note: str = ""
    aliases: List[str] = field(default_factory=list)
    vw_year: int = 2026
    data_dir: str = ""
    summary_text: str = ""
    total_hours: float = 0.0
    sync_config: object | None = None
    sync_status_note: str = ""


class DialogController:
    def __init__(self, vw_year: int = 2026) -> None:
        self.state = DialogState(vw_year=vw_year)

    def set_project_name(self, name: str) -> None:
        self.state.project_name = os.path.basename((name or "").replace("\\", "/"))

    def update_summary(self, *, summary_text: str, total_hours: float, trust_note: str = "") -> None:
        self.state.summary_text = summary_text
        self.state.total_hours = total_hours
        if trust_note:
            self.state.trust_note = trust_note
