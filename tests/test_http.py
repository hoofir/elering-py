"""Transport-level tests: retries, backoff, gzip and status handling.

``urlopen`` is stubbed, so nothing here touches the network.
"""

import gzip
import io
import json
import urllib.error
from email.message import Message

import pytest

from elering import _http
from elering._errors import (
    EleringBadRequest,
    EleringHTTPError,
    EleringServerError,
    EleringTransportError,
)

URL = "https://dashboard.elering.ee/api/system/latest"


class FakeResponse:
    def __init__(
        self, status=200, body=b'{"success": true, "data": []}', encoding=None
    ):
        self.status = status
        self._body = body
        self.headers = Message()
        if encoding:
            self.headers["Content-Encoding"] = encoding

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def http_error(code, body=b"", encoding=None):
    headers = Message()
    if encoding:
        headers["Content-Encoding"] = encoding
    return urllib.error.HTTPError(URL, code, "err", headers, io.BytesIO(body))


@pytest.fixture
def transport(monkeypatch):
    """Queue outcomes for successive urlopen calls and count the attempts."""
    outcomes: list[object] = []
    attempts: list[str] = []

    def fake_urlopen(request, timeout=None):
        attempts.append(request.full_url)
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(_http.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(_http.time, "sleep", lambda _: None)
    return outcomes, attempts


def get(**kwargs):
    params = {"timeout": 10, "retries": 2, "backoff": 0.5, "user_agent": "test"}
    params.update(kwargs)
    return _http.get_json(URL, **params)


# -- success paths ----------------------------------------------------------


def test_returns_decoded_json(transport):
    outcomes, _ = transport
    outcomes.append(FakeResponse(body=b'{"success": true, "data": [{"price": 1}]}'))
    assert get() == {"success": True, "data": [{"price": 1}]}


def test_gzip_body_is_decompressed(transport):
    outcomes, _ = transport
    payload = gzip.compress(json.dumps({"data": [{"price": 1}]}).encode())
    outcomes.append(FakeResponse(body=payload, encoding="gzip"))
    assert get() == {"data": [{"price": 1}]}


def test_204_returns_none(transport):
    outcomes, _ = transport
    outcomes.append(FakeResponse(status=204, body=b""))
    assert get() is None


def test_blank_body_returns_none(transport):
    outcomes, _ = transport
    outcomes.append(FakeResponse(body=b"   "))
    assert get() is None


def test_request_headers_are_set(transport, monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["headers"] = dict(request.headers)
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(_http.urllib.request, "urlopen", fake_urlopen)
    get(user_agent="elering-py/1.2.3", timeout=42)

    assert captured["headers"]["Accept"] == "application/json"
    assert captured["headers"]["Accept-encoding"] == "gzip"
    assert captured["headers"]["User-agent"] == "elering-py/1.2.3"
    assert captured["timeout"] == 42


# -- retries ----------------------------------------------------------------


def test_server_error_is_retried_then_succeeds(transport):
    outcomes, attempts = transport
    outcomes.extend([http_error(503), FakeResponse(body=b'{"data": []}')])
    assert get(retries=2) == {"data": []}
    assert len(attempts) == 2


def test_server_error_raises_after_retries_are_exhausted(transport):
    outcomes, attempts = transport
    outcomes.extend([http_error(500, b"boom")] * 3)
    with pytest.raises(EleringServerError) as excinfo:
        get(retries=2)
    assert excinfo.value.status == 500
    assert len(attempts) == 3, "initial attempt plus two retries"


def test_client_error_is_not_retried(transport):
    outcomes, attempts = transport
    outcomes.append(
        http_error(
            400, b'{"status": "BAD_REQUEST", "messages": ["Maximum period is 1 year"]}'
        )
    )
    with pytest.raises(EleringBadRequest) as excinfo:
        get(retries=5)
    assert excinfo.value.messages == ["Maximum period is 1 year"]
    assert "Maximum period is 1 year" in str(excinfo.value)
    assert len(attempts) == 1


def test_transport_failure_is_retried(transport):
    outcomes, attempts = transport
    outcomes.extend([urllib.error.URLError("dns"), FakeResponse(body=b'{"data": []}')])
    assert get(retries=1) == {"data": []}
    assert len(attempts) == 2


def test_transport_failure_raises_after_retries(transport):
    outcomes, attempts = transport
    outcomes.extend([urllib.error.URLError("dns")] * 2)
    with pytest.raises(EleringTransportError, match="dns"):
        get(retries=1)
    assert len(attempts) == 2


def test_timeout_is_retried_then_raises(transport):
    outcomes, attempts = transport
    outcomes.extend([TimeoutError("slow")] * 2)
    with pytest.raises(EleringTransportError, match="timed out"):
        get(retries=1)
    assert len(attempts) == 2


def test_retries_can_be_disabled(transport):
    outcomes, attempts = transport
    outcomes.append(http_error(502))
    with pytest.raises(EleringServerError):
        get(retries=0)
    assert len(attempts) == 1


def test_backoff_grows_exponentially(transport, monkeypatch):
    outcomes, _ = transport
    delays: list[float] = []
    monkeypatch.setattr(_http.time, "sleep", delays.append)
    outcomes.extend([http_error(500)] * 4)

    with pytest.raises(EleringServerError):
        get(retries=3, backoff=0.5)

    assert delays == [0.5, 1.0, 2.0]


def test_no_sleep_after_the_final_attempt(transport, monkeypatch):
    outcomes, _ = transport
    delays: list[float] = []
    monkeypatch.setattr(_http.time, "sleep", delays.append)
    outcomes.append(http_error(500))

    with pytest.raises(EleringServerError):
        get(retries=0)

    assert delays == []


# -- malformed responses ----------------------------------------------------


def test_invalid_json_raises_without_retrying(transport):
    outcomes, attempts = transport
    outcomes.append(FakeResponse(body=b"not json"))
    with pytest.raises(EleringHTTPError, match="invalid JSON"):
        get(retries=3)
    assert len(attempts) == 1


def test_gzip_error_body_is_decompressed(transport):
    outcomes, _ = transport
    body = gzip.compress(
        b'{"status": "NOT_FOUND", "messages": ["No static resource."]}'
    )
    outcomes.append(http_error(404, body, encoding="gzip"))
    with pytest.raises(EleringBadRequest) as excinfo:
        get()
    assert excinfo.value.messages == ["No static resource."]


def test_non_json_error_body_still_raises(transport):
    outcomes, _ = transport
    outcomes.append(http_error(400, b"Bad Request"))
    with pytest.raises(EleringBadRequest) as excinfo:
        get()
    assert excinfo.value.messages == []
    assert "Bad Request" in excinfo.value.body


# -- URL building -----------------------------------------------------------


@pytest.mark.parametrize(
    ("base", "path", "params", "expected"),
    [
        ("https://x.test", "/A", None, "https://x.test/A"),
        ("https://x.test/", "A", None, "https://x.test/A"),
        ("https://x.test", "/A", {}, "https://x.test/A"),
        ("https://x.test", "/A", {"b": 1}, "https://x.test/A?b=1"),
        ("https://x.test", "/A", {"f": ["1", "2"]}, "https://x.test/A?f=1&f=2"),
    ],
)
def test_build_url(base, path, params, expected):
    assert _http.build_url(base, path, params) == expected


@pytest.mark.parametrize("base", ["file:///etc/passwd", "ftp://x.test", "x.test"])
def test_build_url_rejects_non_http_schemes(base):
    with pytest.raises(ValueError, match="http or https"):
        _http.build_url(base, "/A", None)
