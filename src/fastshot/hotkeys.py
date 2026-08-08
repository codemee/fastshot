from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from PySide6.QtCore import QSettings

from fastshot.settings import CaptureMode


CAPTURE_MODES = (
    CaptureMode.ACTIVE_WINDOW,
    CaptureMode.REGION,
    CaptureMode.FULLSCREEN,
    CaptureMode.WINDOW_UNDER_CURSOR,
)


class HotkeyAction(str, Enum):
    REPEAT = "repeat"


HOTKEY_ACTIONS = (*CAPTURE_MODES, HotkeyAction.REPEAT)


@dataclass(frozen=True)
class HotkeyCombination:
    letter: str
    ctrl: bool = False
    shift: bool = False
    alt: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "letter", self.letter.upper())

    def is_valid(self) -> bool:
        return len(self.letter) == 1 and self.letter.isascii() and self.letter.isalpha() and (
            not self.shift or self.ctrl or self.alt
        )

    def display(self) -> str:
        modifiers = ((self.ctrl, "Ctrl"), (self.shift, "Shift"), (self.alt, "Alt"))
        parts = [name for enabled, name in modifiers if enabled]
        return "+".join((*parts, self.letter))


def default_hotkeys() -> dict[CaptureMode | HotkeyAction, HotkeyCombination]:
    return {
        CaptureMode.ACTIVE_WINDOW: HotkeyCombination("A", ctrl=True, shift=True),
        CaptureMode.REGION: HotkeyCombination("R", ctrl=True, shift=True),
        CaptureMode.FULLSCREEN: HotkeyCombination("F", ctrl=True, shift=True),
        CaptureMode.WINDOW_UNDER_CURSOR: HotkeyCombination("W", ctrl=True, shift=True),
        HotkeyAction.REPEAT: HotkeyCombination("Q", ctrl=True, shift=True),
    }


def validate_hotkeys(
    bindings: dict[CaptureMode | HotkeyAction, HotkeyCombination],
) -> str | None:
    if set(bindings) != set(HOTKEY_ACTIONS):
        return "incomplete"
    if any(not combination.is_valid() for combination in bindings.values()):
        return "invalid"
    if len(set(bindings.values())) != len(bindings):
        return "duplicate"
    return None


class HotkeyStore:
    def __init__(self, settings: QSettings | None = None) -> None:
        self.settings = settings or QSettings()

    def load(self) -> dict[CaptureMode | HotkeyAction, HotkeyCombination]:
        defaults = default_hotkeys()
        result: dict[CaptureMode | HotkeyAction, HotkeyCombination] = {}
        for mode in HOTKEY_ACTIONS:
            prefix = f"hotkeys/{mode.value}"
            default = defaults[mode]
            result[mode] = HotkeyCombination(
                str(self.settings.value(f"{prefix}/letter", default.letter)),
                self._bool(f"{prefix}/ctrl", default.ctrl),
                self._bool(f"{prefix}/shift", default.shift),
                self._bool(f"{prefix}/alt", default.alt),
            )
        return result if validate_hotkeys(result) is None else defaults

    def save(self, bindings: dict[CaptureMode | HotkeyAction, HotkeyCombination]) -> None:
        for mode, combination in bindings.items():
            prefix = f"hotkeys/{mode.value}"
            self.settings.setValue(f"{prefix}/letter", combination.letter)
            self.settings.setValue(f"{prefix}/ctrl", combination.ctrl)
            self.settings.setValue(f"{prefix}/shift", combination.shift)
            self.settings.setValue(f"{prefix}/alt", combination.alt)

    def _bool(self, key: str, default: bool) -> bool:
        value = self.settings.value(key, default)
        if isinstance(value, bool):
            return value
        return str(value).lower() in {"1", "true", "yes"}
