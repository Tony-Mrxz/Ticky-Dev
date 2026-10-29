# utils/update_checker.py
"""Finds a newer published build and installs it through the setup exe.

Every failure here is deliberately silent: a private repository, no network, a
rate limit or a half-formed release response all mean "say nothing", never an
error dialog in the notch. The only message a user ever sees is an update that
really exists.
"""

import os
import subprocess
import sys
import tempfile
import webbrowser

import requests
from PySide6.QtCore import QObject, QThread, Signal

from utils.version import APP_VERSION, RELEASE_REPO, is_newer, parse_version

API_URL = f"https://api.github.com/repos/{RELEASE_REPO}/releases/latest"


class ReleaseInfo:
    """The newest build GitHub says exists."""

    def __init__(self, version, download_url, page_url):
        self.version = version
        self.download_url = download_url
        self.page_url = page_url

    def __repr__(self):
        return f"<ReleaseInfo {self.version} {self.download_url!r}>"


def _pick_asset(release):
    """The setup exe on Windows, the disk image on macOS, any asset otherwise.

    Among the candidates for this platform the one with a version in its filename
    wins: the website needs a permanent .../download/Ticky-Setup.exe alias, and
    that alias carries no number, so picking it first would leave nothing to
    compare against.
    """
    wanted = ".exe" if sys.platform == "win32" else ".dmg"
    assets = release.get("assets") or []
    candidates = [a for a in assets if (a.get("name") or "").lower().endswith(wanted)]
    for asset in candidates:
        if parse_version(asset.get("name") or ""):
            return asset
    return candidates[0] if candidates else (assets[0] if assets else None)


def build_release_info(payload):
    """Turn a releases API response into ReleaseInfo, or None when unusable.

    The version comes from the asset filename first because the CI release reuses
    the tag "latest"; without a parseable number there is nothing to compare, so
    the answer is None rather than a guess.
    """
    if not isinstance(payload, dict):
        return None
    asset = _pick_asset(payload)
    page_url = payload.get("html_url") or ""
    if not asset:
        return None
    version = parse_version(asset.get("name") or "") or parse_version(payload.get("tag_name") or "")
    download_url = asset.get("browser_download_url") or ""
    if not version or not (download_url or page_url):
        return None
    return ReleaseInfo("%d.%d.%d" % version, download_url, page_url)


class ReleaseCheckWorker(QThread):
    """One request to the public releases endpoint; emits ReleaseInfo or None.

    The signal is not called "finished": QThread already owns a zero-argument
    finished() signal, and reusing the name is how slots silently stop firing.
    """

    result_ready = Signal(object)

    def run(self):
        info = None
        try:
            response = requests.get(API_URL, headers={"Accept": "application/vnd.github+json"}, timeout=6)
            if response.status_code == 200:
                info = build_release_info(response.json())
        except Exception:
            info = None
        self.result_ready.emit(info)


class SetupDownloadWorker(QThread):
    """Streams the installer to the temp folder and reports the path."""

    setup_ready = Signal(bool, str)

    def __init__(self, url, version, parent=None):
        super().__init__(parent)
        self._url = url
        self._version = version

    def run(self):
        target = os.path.join(tempfile.gettempdir(), f"Ticky-Setup-{self._version}.exe")
        try:
            with requests.get(self._url, stream=True, timeout=(15, 60)) as response:
                if response.status_code != 200:
                    raise RuntimeError(f"HTTP {response.status_code}")
                with open(target, "wb") as handle:
                    for chunk in response.iter_content(chunk_size=256 * 1024):
                        if chunk:
                            handle.write(chunk)
            # A login page or an error JSON saved as a .exe is the realistic
            # failure, and running it would be worse than not updating.
            if os.path.getsize(target) < 5 * 1024 * 1024:
                raise RuntimeError("downloaded installer is too small to be real")
        except Exception as exc:
            try:
                os.remove(target)
            except OSError:
                pass
            self.setup_ready.emit(False, str(exc))
            return
        self.setup_ready.emit(True, target)


class UpdateService(QObject):
    """One shared checker: the startup alert and the settings page ask the same instance."""

    checked = Signal(object)        # newer ReleaseInfo, or None meaning "already current"
    unavailable = Signal()          # nothing learnable - stay quiet
    download_changed = Signal(str)  # "downloading" | "ready" | "failed"

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers = []
        self._checking = False
        self._downloading = False
        self.latest = None
        self._pending_release = None

    def check(self):
        """Start a release check if one is not already in flight."""
        if self._checking:
            return
        self._checking = True
        worker = ReleaseCheckWorker(self)
        self._workers.append(worker)
        # Bound methods keep the slot on this object's thread; a bare lambda would
        # run inside the worker and let it be deleted while still running.
        worker.result_ready.connect(self._on_checked)
        worker.start()

    def download_and_install(self, info=None):
        """Fetch the setup exe and start it; falls back to the release page."""
        release = info or self.latest
        if not release or not release.download_url or self._downloading:
            self.open_release_page(release)
            return
        self._pending_release = release
        self._downloading = True
        self.download_changed.emit("downloading")
        worker = SetupDownloadWorker(release.download_url, release.version, self)
        self._workers.append(worker)
        worker.setup_ready.connect(self._on_downloaded)
        worker.start()

    @staticmethod
    def open_release_page(release):
        if release and release.page_url:
            webbrowser.open(release.page_url)

    def _on_checked(self, info):
        worker = self.sender()
        self._retire(worker)
        self._checking = False
        if info is None:
            self.unavailable.emit()
            return
        self.latest = info if is_newer(info.version) else None
        self.checked.emit(self.latest)

    def _on_downloaded(self, ok, detail):
        worker = self.sender()
        self._retire(worker)
        self._downloading = False
        release, self._pending_release = self._pending_release, None
        if not ok or not self._launch(detail):
            self.download_changed.emit("failed")
            self.open_release_page(release)
            return
        self.download_changed.emit("ready")

    @staticmethod
    def _launch(path):
        """Hand the installer to Windows; Setup closes the running Ticky itself."""
        try:
            if sys.platform == "win32":
                os.startfile(path)
            else:
                subprocess.Popen(["open", path])
            return True
        except Exception:
            try:
                os.remove(path)
            except OSError:
                pass
            return False

    def _retire(self, worker):
        if worker in self._workers:
            self._workers.remove(worker)
        # A QThread must not be destroyed while its OS thread is still leaving
        # run(); the signal that got us here fires from inside it.
        worker.wait(2000)
        worker.deleteLater()
