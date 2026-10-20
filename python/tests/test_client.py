"""Проверяем то, что легко сломать незаметно: разбор ошибок, повторы, тело запроса."""

from __future__ import annotations

import httpx
import pytest
from pytest_httpx import HTTPXMock

from srezai import BadRequest, HostUnresolved, RateLimited, SrezAI, SsrfBlocked, Unauthorized

KEY = "srz_live_test"


def make(**kw: object) -> SrezAI:
    return SrezAI(KEY, max_retries=0, **kw)  # type: ignore[arg-type]


def test_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SREZAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="SREZAI_API_KEY"):
        SrezAI()


def test_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SREZAI_API_KEY", "srz_live_from_env")
    assert SrezAI()._t.api_key == "srz_live_from_env"


def test_search_sends_bearer_and_drops_none(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"results": [], "meta": {}})
    make().search("тест", num=3)

    req = httpx_mock.get_requests()[0]
    assert req.headers["authorization"] == f"Bearer {KEY}"
    import json

    body = json.loads(req.content)
    assert body == {"query": "тест", "num": 3}, "None-поля не должны уходить на сервер"


def test_snake_case_maps_to_camel(httpx_mock: HTTPXMock) -> None:
    """time_range → timeRange. Опечатка здесь молча отключила бы фильтр."""
    httpx_mock.add_response(json={"results": []})
    make().search("тест", time_range="day", include_domains=["habr.com"])

    import json

    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["timeRange"] == "day"
    assert body["includeDomains"] == ["habr.com"]


@pytest.mark.parametrize(
    ("code", "status", "exc"),
    [
        ("unauthorized", 401, Unauthorized),
        ("ssrf_blocked", 400, SsrfBlocked),
        ("host_unresolved", 400, HostUnresolved),
    ],
)
def test_error_codes_map_to_classes(
    httpx_mock: HTTPXMock, code: str, status: int, exc: type[Exception]
) -> None:
    httpx_mock.add_response(status_code=status, json={"code": code, "error": "нет"})
    with pytest.raises(exc):
        make().read_url("https://example.com")


def test_host_unresolved_is_not_ssrf(httpx_mock: HTTPXMock) -> None:
    """Несуществующий домен — не запрет. Иначе агент решит, что ссылку запретили."""
    httpx_mock.add_response(
        status_code=400, json={"code": "host_unresolved", "error": "домена нет"}
    )
    with pytest.raises(HostUnresolved) as ei:
        make().read_url("https://nonexistent.invalid")
    assert not isinstance(ei.value, SsrfBlocked)


def test_unknown_code_does_not_break_client(httpx_mock: HTTPXMock) -> None:
    """Новый код на сервере не должен ломать старый клиент."""
    from srezai import SrezAIError

    httpx_mock.add_response(status_code=418, json={"code": "brand_new", "error": "?"})
    with pytest.raises(SrezAIError) as ei:
        make().search("тест")
    assert ei.value.code == "brand_new"


def test_rate_limit_exposes_retry_after(httpx_mock: HTTPXMock) -> None:
    """Поле называется retryAfterSec: с retryAfter клиент молча терял подсказку."""
    httpx_mock.add_response(
        status_code=429, json={"code": "rate_limited", "error": "лимит", "retryAfterSec": 7}
    )
    with pytest.raises(RateLimited) as ei:
        make().search("тест")
    assert ei.value.retry_after == 7


def test_rate_limit_falls_back_to_header(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        status_code=429,
        json={"code": "rate_limited", "error": "лимит"},
        headers={"Retry-After": "11"},
    )
    with pytest.raises(RateLimited) as ei:
        make().search("тест")
    assert ei.value.retry_after == 11


def test_retries_then_succeeds(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=503, json={"code": "service_unavailable", "error": "сбой"})
    httpx_mock.add_response(json={"results": [{"title": "ок"}]})

    client = SrezAI(KEY, max_retries=1)
    assert client.search("тест")["results"][0]["title"] == "ок"
    assert len(httpx_mock.get_requests()) == 2


def test_bad_request_is_not_retried(httpx_mock: HTTPXMock) -> None:
    """Повторять ошибку запроса — трата денег и времени."""
    httpx_mock.add_response(status_code=400, json={"code": "bad_request", "error": "не то"})
    with pytest.raises(BadRequest):
        SrezAI(KEY, max_retries=3).search("тест")
    assert len(httpx_mock.get_requests()) == 1


def test_extract_rejects_both_url_and_urls() -> None:
    with pytest.raises(ValueError, match="ровно одно"):
        make().extract({"t": "string"}, url="https://a.com", urls=["https://b.com"])


def test_extract_requires_one_target() -> None:
    with pytest.raises(ValueError, match="ровно одно"):
        make().extract({"t": "string"})


def test_answer_search_sends_query_and_depth(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"answer": "ответ", "sources": [], "confidence": 0.9})
    result = make().answer_search("вопрос", depth="fast")

    assert result["answer"] == "ответ"
    req = httpx_mock.get_requests()[0]
    assert req.url.path == "/api/v1/answer"
    import json

    body = json.loads(req.content)
    assert body == {"query": "вопрос", "depth": "fast"}


def test_unsupported_system_proxy_explains_itself(monkeypatch: pytest.MonkeyPatch) -> None:
    """Прокси, который httpx не умеет, не должен выглядеть как поломка SDK."""
    monkeypatch.delenv("no_proxy", raising=False)
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.setenv("ALL_PROXY", "socks4://127.0.0.1:1080")
    with pytest.raises(ValueError, match="trust_env=False"):
        SrezAI(KEY)


def test_own_client_bypasses_proxy_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Обходной путь из текста ошибки обязан работать."""
    monkeypatch.delenv("no_proxy", raising=False)
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.setenv("ALL_PROXY", "socks4://127.0.0.1:1080")
    with httpx.Client(trust_env=False) as own:
        assert SrezAI(KEY, client=own)._t is not None


def test_transcript_one_video_and_field_mapping(httpx_mock: HTTPXMock) -> None:
    """Строка → список, snake_case → camelCase, пустые поля не уходят."""
    httpx_mock.add_response(json={"results": [], "errors": []})
    make().transcript("https://youtu.be/dQw4w9WgXcQ", languages=["ru"], max_chars=8000)

    import json

    req = httpx_mock.get_requests()[0]
    assert str(req.url) == "https://srezai.ru/api/v1/transcript"
    body = json.loads(req.content)
    assert body["videos"] == ["https://youtu.be/dQw4w9WgXcQ"]
    assert body["languages"] == ["ru"]
    assert body["maxChars"] == 8000
    assert "from" not in body and "to" not in body and "timestamps" not in body


def test_transcript_window_passes_through(httpx_mock: HTTPXMock) -> None:
    """from_ → from (окно продолжения), to остаётся to."""
    httpx_mock.add_response(json={"results": []})
    make().transcript(["https://youtu.be/a", "https://youtu.be/b"], from_=1290, to=1800)

    import json

    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["from"] == 1290
    assert body["to"] == 1800
    assert body["videos"] == ["https://youtu.be/a", "https://youtu.be/b"]
