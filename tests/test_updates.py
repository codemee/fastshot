import io
import json
from datetime import datetime, timedelta, timezone

from packaging.version import Version
from PySide6.QtCore import QEventLoop, QSettings, QTimer
from uv_tool_updater import InstalledTool, ReleaseInfo, UpdateCheck, UpdateStatus

from fshot.updates import GitHubReleaseUpdater, LAST_CHECKED_AT_KEY, UpdateManager


class FakeUpdater:
    def __init__(self, check=None, error: Exception | None = None) -> None:
        self.result = check
        self.error = error
        self.calls = []

    def check(self, **options):
        self.calls.append(options)
        if self.error is not None:
            raise self.error
        return self.result


def _available_update() -> UpdateCheck:
    installed = InstalledTool(
        package_name="fshot",
        command_name="fshot",
        current_version=Version("1.0.0"),
        executable_path=None,
        python_prefix=None,
        uv_path=None,
        uv_tool_dir=None,
        managed_by_uv=True,
    )
    release = ReleaseInfo(package_name="fshot", version=Version("1.1.0"))
    return UpdateCheck(UpdateStatus.UPDATE_AVAILABLE, installed, release)


def test_automatic_update_check_defaults_to_daily(qt_app, tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    manager = UpdateManager(FakeUpdater(_available_update()), settings)
    now = datetime(2026, 8, 16, 12, tzinfo=timezone.utc)

    assert manager.automatic_checks_enabled
    assert manager.automatic_check_is_due(now)

    settings.setValue(LAST_CHECKED_AT_KEY, (now - timedelta(hours=23)).isoformat())
    assert not manager.automatic_check_is_due(now)

    settings.setValue(LAST_CHECKED_AT_KEY, (now - timedelta(hours=25)).isoformat())
    assert manager.automatic_check_is_due(now)

    manager.set_automatic_checks_enabled(False)
    assert not manager.automatic_check_is_due(now)


def test_skipped_update_version_is_persisted(qt_app, tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    manager = UpdateManager(FakeUpdater(_available_update()), settings)

    manager.skip_version("1.1.0")

    assert manager.is_version_skipped("1.1.0")
    assert not manager.is_version_skipped("1.2.0")


def test_update_check_runs_off_the_ui_thread(qt_app, tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    updater = FakeUpdater(_available_update())
    manager = UpdateManager(updater, settings)
    loop = QEventLoop()
    received = []
    manager.checkFinished.connect(lambda check, manual: (received.append((check, manual)), loop.quit()))

    assert manager.start_check(manual=True)
    assert manager.is_checking
    QTimer.singleShot(2000, loop.quit)
    loop.exec()
    manager.thread_pool.waitForDone()

    assert received == [(_available_update(), True)]
    assert updater.calls == [{"timeout": 5.0, "allow_prereleases": False}]
    assert not manager.is_checking
    assert settings.value(LAST_CHECKED_AT_KEY)


def test_unexpected_update_check_failure_is_reported(qt_app, tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    manager = UpdateManager(FakeUpdater(error=RuntimeError("offline")), settings)
    loop = QEventLoop()
    received = []
    manager.checkFailed.connect(
        lambda message, manual: (received.append((message, manual)), loop.quit())
    )

    assert manager.start_check(manual=True)
    QTimer.singleShot(2000, loop.quit)
    loop.exec()
    manager.thread_pool.waitForDone()

    assert received == [("offline", True)]
    assert not manager.is_checking


class _JsonResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def test_packaged_update_checker_uses_latest_github_release(monkeypatch):
    import fshot.updates as updates

    payload = {
        "tag_name": "v1.2.0",
        "html_url": "https://github.com/codemee/fshot/releases/tag/v1.2.0",
        "prerelease": False,
    }
    monkeypatch.setattr(
        updates,
        "urlopen",
        lambda _request, timeout: _JsonResponse(json.dumps(payload).encode()),
    )

    check = GitHubReleaseUpdater("1.1.0").check()

    assert check.status is UpdateStatus.UPDATE_AVAILABLE
    assert str(check.installed.current_version) == "1.1.0"
    assert str(check.release.version) == "1.2.0"
    assert check.release.release_url == payload["html_url"]


def test_packaged_update_checker_reports_current_release(monkeypatch):
    import fshot.updates as updates

    payload = {
        "tag_name": "v1.2.0",
        "html_url": "https://github.com/codemee/fshot/releases/tag/v1.2.0",
    }
    monkeypatch.setattr(
        updates,
        "urlopen",
        lambda _request, timeout: _JsonResponse(json.dumps(payload).encode()),
    )

    check = GitHubReleaseUpdater("1.2.0").check()

    assert check.status is UpdateStatus.UP_TO_DATE
