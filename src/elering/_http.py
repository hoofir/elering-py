"""Minimal JSON-over-HTTP transport built on the standard library."""

from __future__ import annotations

import gzip
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from http.client import HTTPResponse
from typing import Any

from ._errors import (
    EleringBadRequest,
    EleringHTTPError,
    EleringServerError,
    EleringTransportError,
)

_ALLOWED_SCHEMES = frozenset({"http", "https"})


def build_url(base_url: str, path: str, params: dict[str, Any] | None) -> str:
    scheme = urllib.parse.urlsplit(base_url).scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"base_url must use http or https, got {base_url!r}")
    url = base_url.rstrip("/") + "/" + path.lstrip("/")
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    return url


def _read(response: HTTPResponse | urllib.error.HTTPError) -> bytes:
    body = response.read()
    if response.headers.get("Content-Encoding") == "gzip":
        return gzip.decompress(body)
    return body


def _raise_for_status(status: int, url: str, body: bytes) -> None:
    """Turn an error response into the matching exception.

    Errors carry ``{"status": ..., "messages": [...]}``; the messages are the
    only part worth surfacing, so they are attached to the exception.
    """
    text = body.decode("utf-8", errors="replace")
    messages: list[str] | None = None
    try:
        payload = json.loads(text)
    except ValueError:
        payload = None
    if isinstance(payload, dict) and isinstance(payload.get("messages"), list):
        messages = [str(message) for message in payload["messages"]]
    if status < 500:
        raise EleringBadRequest(status, url, text, messages)
    raise EleringServerError(status, url, text)


def get_json(
    url: str,
    *,
    timeout: float,
    retries: int,
    backoff: float,
    user_agent: str,
) -> Any:
    """Perform a GET request and return the decoded JSON body.

    Returns ``None`` for an empty body. Retries transport failures and 5xx
    responses with exponential backoff.
    """
    request = urllib.request.Request(  # noqa: S310 - scheme validated in build_url
        url,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "User-Agent": user_agent,
        },
        method="GET",
    )

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
                if response.status == 204:
                    return None
                body = _read(response)
                if not body.strip():
                    return None
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            body = _read(exc)
            if exc.code < 500:
                _raise_for_status(exc.code, url, body)
            last_error = EleringServerError(
                exc.code, url, body.decode("utf-8", "replace")
            )
        except urllib.error.URLError as exc:
            last_error = EleringTransportError(f"request to {url} failed: {exc.reason}")
        except TimeoutError as exc:
            last_error = EleringTransportError(f"request to {url} timed out: {exc}")
        except ValueError as exc:
            raise EleringHTTPError(200, url, f"invalid JSON response: {exc}") from exc

        if attempt < retries:
            time.sleep(backoff * 2**attempt)

    assert last_error is not None
    raise last_error
