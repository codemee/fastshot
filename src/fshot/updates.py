from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from packaging.version import Version
from PySide6.QtCore import QObject, QRunnable, QSettings, QThreadPool, Signal, Slot
from uv_tool_updater import InstalledTool, ReleaseInfo, UpdateCheck, Updater, UpdateStatus, check_is_due

from fshot import __version__

AUTOMATIC_CHECKS_KEY = "updates/check_automatically"
LAST_CHECKED_AT_KEY = "updates/last_checked_at"
SKIPPED_VERSION_KEY = "updates/skipped_version"
UPDATE_CHECK_INTERVAL_SECONDS = 24 * 60 * 60
GITHUB_LATEST_RELEASE_API = "https://api.github.com/repos/codemee/fshot/releases/latest"
GITHUB_RELEASES_URL = "https://github.com/codemee/fshot/releases/latest"


class GitHubReleaseUpdater:
    """Read-only update checker for frozen EXE/App distributions."""

    def __init__(self, current_version: str = __version__) -> None:
        self.current_version = Version(current_version)

    def check(self, timeout: float = 5.0, allow_prereleases: bool = False) -> UpdateCheck:
        del allow_prereleases
        request = Request(
            GITHUB_LATEST_RELEASE_API,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"FShot/{self.current_version}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
        latest = Version(str(payload["tag_name"]).removeprefix("v"))
        installed = InstalledTool(
            package_name="fshot",
            command_name="fshot",
            current_version=self.current_version,
            executable_path=Path(sys.executable),
            python_prefix=Path(sys.prefix),
            uv_path=None,
            uv_tool_dir=None,
            managed_by_uv=False,
        )
        release = ReleaseInfo(
            package_name="fshot",
            version=latest,
            release_url=str(payload.get("html_url") or GITHUB_RELEASES_URL),
            prerelease=bool(payload.get("prerelease", False)),
        )
        status = (
            UpdateStatus.UPDATE_AVAILABLE
            if latest > self.current_version
            else UpdateStatus.UP_TO_DATE
        )
        return UpdateCheck(status=status, installed=installed, release=release)

    def consume_latest_result(self):
        return None


class _UpdateCheckSignals(QObject):
    finished = Signal(object, bool)
    failed = Signal(str, bool)


class _UpdateCheckTask(QRunnable):
    def __init__(self, updater: Updater, manual: bool) -> None:
        super().__init__()
        self.updater = updater
        self.manual = manual
        self.signals = _UpdateCheckSignals()

    @Slot()
    def run(self) -> None:
        try:
            check = self.updater.check(timeout=5.0, allow_prereleases=False)
        except Exception as exc:  # pragma: no cover - defensive third-party boundary
            self.signals.failed.emit(str(exc), self.manual)
            return
        self.signals.finished.emit(check, self.manual)


class UpdateManager(QObject):
    checkFinished = Signal(object, bool)
    checkFailed = Signal(str, bool)
    checkingChanged = Signal(bool)

    def __init__(
        self,
        updater: Updater,
        settings: QSettings,
        thread_pool: QThreadPool | None = None,
    ) -> None:
        super().__init__()
        self.updater = updater
        self.settings = settings
        self.thread_pool = thread_pool or QThreadPool(self)
        self.thread_pool.setMaxThreadCount(1)
        self._task: _UpdateCheckTask | None = None

    @property
    def is_checking(self) -> bool:
        return self._task is not None

    @property
    def automatic_checks_enabled(self) -> bool:
        return self.settings.value(AUTOMATIC_CHECKS_KEY, True, type=bool)

    def set_automatic_checks_enabled(self, enabled: bool) -> None:
        self.settings.setValue(AUTOMATIC_CHECKS_KEY, enabled)

    def automatic_check_is_due(self, now: datetime | None = None) -> bool:
        if not self.automatic_checks_enabled:
            return False
        checked_at = self.settings.value(LAST_CHECKED_AT_KEY, None)
        return check_is_due(
            str(checked_at) if checked_at else None,
            now=now or datetime.now(timezone.utc),
            interval_seconds=UPDATE_CHECK_INTERVAL_SECONDS,
        )

    def start_check(self, *, manual: bool = False, now: datetime | None = None) -> bool:
        if self.is_checking:
            return False
        if not manual and not self.automatic_check_is_due(now):
            return False
        task = _UpdateCheckTask(self.updater, manual)
        task.signals.finished.connect(self._check_finished)
        task.signals.failed.connect(self._check_failed)
        self._task = task
        self.checkingChanged.emit(True)
        self.thread_pool.start(task)
        return True

    def skip_version(self, version: str) -> None:
        self.settings.setValue(SKIPPED_VERSION_KEY, version)

    def is_version_skipped(self, version: str) -> bool:
        return str(self.settings.value(SKIPPED_VERSION_KEY, "")) == version

    def _mark_checked(self) -> None:
        checked_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self.settings.setValue(LAST_CHECKED_AT_KEY, checked_at)

    @Slot(object, bool)
    def _check_finished(self, check: UpdateCheck, manual: bool) -> None:
        self._mark_checked()
        self._task = None
        self.checkingChanged.emit(False)
        self.checkFinished.emit(check, manual)

    @Slot(str, bool)
    def _check_failed(self, message: str, manual: bool) -> None:
        self._mark_checked()
        self._task = None
        self.checkingChanged.emit(False)
        self.checkFailed.emit(message, manual)
