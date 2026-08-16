import os

from packaging.version import Version
from PySide6.QtCore import QSettings
from uv_tool_updater import ReleaseInfo

from fshot.app import FShotApplication


class FakeSession:
    def __init__(self) -> None:
        self.host_pid = None

    def start_helper(self, *, host_pid: int) -> int:
        self.host_pid = host_pid
        return 1234


class FakeUpdater:
    def __init__(self) -> None:
        self.session = FakeSession()
        self.prepare_calls = []

    def check(self, **_options):
        raise AssertionError("No network check expected")

    def prepare_update(self, release, **options):
        self.prepare_calls.append((release, options))
        return self.session

    def consume_latest_result(self):
        return None


def _controller(qt_app, tmp_path, monkeypatch):
    monkeypatch.setattr(FShotApplication, "_register_hotkeys", lambda self: None)
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    updater = FakeUpdater()
    controller = FShotApplication(qt_app, updater=updater, update_settings=settings)
    return controller, updater


def test_tray_exposes_update_controls(qt_app, tmp_path, monkeypatch):
    controller, _updater = _controller(qt_app, tmp_path, monkeypatch)

    assert controller.check_updates_action in controller.tray.contextMenu().actions()
    assert controller.automatic_updates_action.isCheckable()
    assert controller.automatic_updates_action.isChecked()


def test_confirmed_update_starts_helper_before_shutdown(qt_app, tmp_path, monkeypatch):
    controller, updater = _controller(qt_app, tmp_path, monkeypatch)
    release = ReleaseInfo(package_name="fshot", version=Version("0.0.11"))
    shutdown = []
    monkeypatch.setattr(controller.window, "confirm_discard_all", lambda _key: True)
    monkeypatch.setattr(controller, "_shutdown", lambda: shutdown.append(True))

    controller._install_update(release)

    assert updater.prepare_calls == [
        (
            release,
            {
                "restart_args": [],
                "restart_on_failure": True,
                "wait_timeout": 600,
            },
        )
    ]
    assert updater.session.host_pid == os.getpid()
    assert shutdown == [True]


def test_declined_unsaved_changes_cancel_update(qt_app, tmp_path, monkeypatch):
    controller, updater = _controller(qt_app, tmp_path, monkeypatch)
    release = ReleaseInfo(package_name="fshot", version=Version("0.0.11"))
    monkeypatch.setattr(controller.window, "confirm_discard_all", lambda _key: False)

    controller._install_update(release)

    assert updater.prepare_calls == []
    assert updater.session.host_pid is None
