import json

import pytest
from PySide6.QtCore import QUrl

from tinynetuse.update_check import (
    LATEST_RELEASE_API_URL,
    CheckStatus,
    UpdateChecker,
    parse_release_response,
)


@pytest.mark.parametrize(
    ("tag_name", "local_version", "expected_status", "expected_version"),
    [
        ("v1.2.0", "1.1.1", CheckStatus.UPDATE_AVAILABLE, "1.2.0"),
        ("1.1.1", "1.1.1", CheckStatus.UP_TO_DATE, None),
        ("v1.0.0", "1.1.1", CheckStatus.UP_TO_DATE, None),
    ],
)
def test_release_response_compares_numeric_versions(
    tag_name, local_version, expected_status, expected_version
):
    result = parse_release_response(
        json.dumps({"tag_name": tag_name}).encode(), local_version
    )

    assert result.status is expected_status
    assert result.version == expected_version


@pytest.mark.parametrize(
    ("tag_name", "local_version", "expected_status", "expected_version"),
    [
        ("v1.10.0", "1.9.99", CheckStatus.UPDATE_AVAILABLE, "1.10.0"),
        ("v1.2.3.1", "1.2.3", CheckStatus.UPDATE_AVAILABLE, "1.2.3.1"),
        ("v1.2.3.0", "1.2.3", CheckStatus.UP_TO_DATE, None),
    ],
)
def test_release_response_compares_all_numeric_version_parts(
    tag_name, local_version, expected_status, expected_version
):
    result = parse_release_response(
        json.dumps({"tag_name": tag_name}).encode(), local_version
    )

    assert result.status is expected_status
    assert result.version == expected_version


@pytest.mark.parametrize(
    "payload",
    [
        b"not json",
        b"{}",
        b'{"tag_name": "latest"}',
        b'{"tag_name": "v1.2"}',
        b'{"tag_name": "1.2.3-beta"}',
        b'{"tag_name": " 1.2.3"}',
    ],
)
def test_release_response_rejects_invalid_github_data(payload):
    result = parse_release_response(payload, "1.1.1")

    assert result.status is CheckStatus.GITHUB_ERROR
    assert result.version is None


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (LATEST_RELEASE_API_URL, True),
        ("https://api.github.com:443/repos/laween-alsulaivany/TinyNetUse/releases/latest", True),
        ("http://api.github.com/repos/laween-alsulaivany/TinyNetUse/releases/latest", False),
        ("https://api.github.com:8443/repos/laween-alsulaivany/TinyNetUse/releases/latest", False),
        ("https://api.github.com/user", False),
        ("https://api.github.com/repos/laween-alsulaivany/TinyNetUse/releases/latest?draft=true", False),
        ("https://api.github.com.example.test/repos/laween-alsulaivany/TinyNetUse/releases/latest", False),
    ],
)
def test_update_checker_rejects_unexpected_api_origins(url, expected):
    assert UpdateChecker._is_expected_api_url(QUrl(url)) is expected
