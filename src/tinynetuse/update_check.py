"""Manual GitHub release checks for TinyNetUse."""

from dataclasses import dataclass
from enum import Enum
import json
import re

from PySide6 import QtCore, QtNetwork


LATEST_RELEASE_API_URL = (
    "https://api.github.com/repos/laween-alsulaivany/TinyNetUse/releases/latest"
)
LATEST_RELEASE_PAGE_URL = (
    "https://github.com/laween-alsulaivany/TinyNetUse/releases/latest"
)
REQUEST_TIMEOUT_MS = 10_000
MAX_RESPONSE_BYTES = 64 * 1024
VERSION_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?$")


class CheckStatus(Enum):
    UP_TO_DATE = "up_to_date"
    UPDATE_AVAILABLE = "update_available"
    NETWORK_ERROR = "network_error"
    GITHUB_ERROR = "github_error"


@dataclass(frozen=True)
class UpdateCheckResult:
    status: CheckStatus
    version: str | None = None


def _version_parts(version: str) -> tuple[int, ...] | None:
    match = VERSION_PATTERN.fullmatch(version)
    if match is None:
        return None
    return tuple(int(part) for part in match.groups(default="0"))


def parse_release_response(payload: bytes, local_version: str) -> UpdateCheckResult:
    try:
        release = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return UpdateCheckResult(CheckStatus.GITHUB_ERROR)

    tag_name = release.get("tag_name") if isinstance(release, dict) else None
    if not isinstance(tag_name, str):
        return UpdateCheckResult(CheckStatus.GITHUB_ERROR)

    remote_parts = _version_parts(tag_name)
    local_parts = _version_parts(local_version)
    if remote_parts is None or local_parts is None:
        return UpdateCheckResult(CheckStatus.GITHUB_ERROR)

    if remote_parts > local_parts:
        return UpdateCheckResult(
            CheckStatus.UPDATE_AVAILABLE,
            tag_name.removeprefix("v"),
        )
    return UpdateCheckResult(CheckStatus.UP_TO_DATE)


class UpdateChecker(QtCore.QObject):
    """Check the fixed GitHub API endpoint without blocking the Qt event loop."""

    finished = QtCore.Signal(object)

    def __init__(self, local_version: str, parent=None):
        super().__init__(parent)
        self._local_version = local_version
        self._network = QtNetwork.QNetworkAccessManager(self)
        self._reply = None
        self._response = bytearray()
        self._timeout = QtCore.QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.timeout.connect(self._on_timeout)

    def check(self) -> bool:
        if self._reply is not None:
            return False

        request = QtNetwork.QNetworkRequest(QtCore.QUrl(LATEST_RELEASE_API_URL))
        request.setRawHeader(b"Accept", b"application/vnd.github+json")
        request.setRawHeader(
            b"User-Agent", f"TinyNetUse/{self._local_version}".encode("ascii")
        )
        request.setAttribute(
            QtNetwork.QNetworkRequest.Attribute.CacheLoadControlAttribute,
            QtNetwork.QNetworkRequest.CacheLoadControl.AlwaysNetwork,
        )
        request.setAttribute(
            QtNetwork.QNetworkRequest.Attribute.CacheSaveControlAttribute,
            False,
        )
        request.setAttribute(
            QtNetwork.QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QtNetwork.QNetworkRequest.RedirectPolicy.SameOriginRedirectPolicy,
        )

        self._response.clear()
        self._reply = self._network.get(request)
        reply = self._reply
        reply.readyRead.connect(lambda: self._read_reply(reply))
        reply.finished.connect(lambda: self._finish_reply(reply))
        self._timeout.start(REQUEST_TIMEOUT_MS)
        return True

    def cancel(self):
        if self._reply is not None:
            self._complete(self._reply, None, abort=True)

    def _read_reply(self, reply):
        if reply is not self._reply:
            return

        content_length = reply.header(
            QtNetwork.QNetworkRequest.KnownHeaders.ContentLengthHeader
        )
        if isinstance(content_length, int) and content_length > MAX_RESPONSE_BYTES:
            self._complete(
                reply, UpdateCheckResult(CheckStatus.GITHUB_ERROR), abort=True
            )
            return

        self._response.extend(bytes(reply.readAll()))
        if len(self._response) > MAX_RESPONSE_BYTES:
            self._complete(
                reply, UpdateCheckResult(CheckStatus.GITHUB_ERROR), abort=True
            )

    def _finish_reply(self, reply):
        if reply is not self._reply:
            return

        if not self._is_expected_api_url(reply.url()):
            self._complete(reply, UpdateCheckResult(CheckStatus.GITHUB_ERROR))
            return

        status_code = reply.attribute(
            QtNetwork.QNetworkRequest.Attribute.HttpStatusCodeAttribute
        )
        if isinstance(status_code, int) and status_code != 200:
            self._complete(reply, UpdateCheckResult(CheckStatus.GITHUB_ERROR))
            return

        if reply.error() != QtNetwork.QNetworkReply.NetworkError.NoError:
            self._complete(reply, UpdateCheckResult(CheckStatus.NETWORK_ERROR))
            return

        if status_code != 200:
            self._complete(reply, UpdateCheckResult(CheckStatus.GITHUB_ERROR))
            return

        self._read_reply(reply)
        if reply is self._reply:
            self._complete(
                reply,
                parse_release_response(bytes(self._response), self._local_version),
            )

    def _on_timeout(self):
        if self._reply is not None:
            self._complete(
                self._reply, UpdateCheckResult(CheckStatus.NETWORK_ERROR), abort=True
            )

    def _complete(self, reply, result: UpdateCheckResult | None, abort=False):
        if reply is not self._reply:
            return
        # Clear this first because abort() can synchronously emit finished.
        self._reply = None
        self._timeout.stop()
        if abort:
            reply.abort()
        reply.deleteLater()
        if result is not None:
            self.finished.emit(result)

    @staticmethod
    def _is_expected_api_url(url: QtCore.QUrl) -> bool:
        return (
            url.scheme() == "https"
            and url.host().casefold() == "api.github.com"
            and url.port() in (-1, 443)
            and url.path() == "/repos/laween-alsulaivany/TinyNetUse/releases/latest"
            and not url.query()
            and not url.fragment()
            and not url.userInfo()
        )
