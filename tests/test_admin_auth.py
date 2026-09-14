import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.core.auth import require_admin_token


def _settings(token: str):
    return SimpleNamespace(app=SimpleNamespace(admin_api_token=token))


def test_admin_token_accepts_matching_bearer_token():
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="secret")

    with patch("src.core.auth.get_settings", return_value=_settings("secret")):
        assert asyncio.run(require_admin_token(credentials)) is None


@pytest.mark.parametrize(
    "credentials",
    [
        None,
        HTTPAuthorizationCredentials(scheme="Basic", credentials="secret"),
    ],
)
def test_admin_token_rejects_missing_or_non_bearer_token_with_401(credentials):
    with patch("src.core.auth.get_settings", return_value=_settings("secret")):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(require_admin_token(credentials))

    assert exc_info.value.status_code == 401
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


def test_admin_token_rejects_invalid_token_with_403():
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong")

    with patch("src.core.auth.get_settings", return_value=_settings("secret")):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(require_admin_token(credentials))

    assert exc_info.value.status_code == 403


def test_admin_token_fails_closed_when_not_configured():
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="secret")

    with patch("src.core.auth.get_settings", return_value=_settings("")):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(require_admin_token(credentials))

    assert exc_info.value.status_code == 503
