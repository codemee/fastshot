from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


def make_tab_title(now: datetime | None = None) -> str:
    value = now or datetime.now()
    return value.strftime("%y-%m-%d-%H%M%S")


@dataclass
class ShotDocument:
    title: str
    image: Any
    path: Path | None = None
    dirty: bool = True
    undo_stack: list[Any] = field(default_factory=list)

    @property
    def is_unsaved(self) -> bool:
        return self.path is None

    @property
    def is_dirty(self) -> bool:
        return self.dirty or self.is_unsaved

    @property
    def can_save(self) -> bool:
        return self.is_unsaved or self.dirty

    @property
    def display_title(self) -> str:
        return self.title

    def mark_dirty(self) -> None:
        self.dirty = True

    def mark_saved(self, path: str | Path) -> None:
        self.path = Path(path)
        self.title = self.path.stem
        self.dirty = False
