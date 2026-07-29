"""Транспорт: HTTP, авторизация, разбор ошибок, повторы.

Вынесен из ``client.py``, чтобы методы API читались как список возможностей, а
не как обёртки над ``httpx``.
"""

from __future__ import annotations

import os
import time
from collections.abc import Mapping
from typing import Any

import httpx
from typing_extensions import Self

from .errors import ERROR_CLASSES, RateLimited, SrezAIError

DEFAULT_BASE_URL = "https://srezai.ru"

# DeepResearch синхронный и занимает до двух минут: общий таймаут должен быть
# заметно больше, иначе клиент оборвёт соединение раньше, чем сервер ответит,
# и кредиты спишутся без результата.
DEFAULT_TIMEOUT = 180.0

# Повторяем только то, что имеет смысл повторять: сбои апстрима и лимиты.
# Ошибки запроса (400, 401) повторять бессмысленно — вернём сразу.
RETRY_CODES = frozenset(
    {"rate_limited", "service_unavailable", "search_unavailable", "upstream_timeout"}
)


def _detail(payload: Mapping[str, Any], fallback: str) -> str:
    err = payload.get("error")
    return err if isinstance(err, str) and err else fallback


def _header_seconds(raw: str | None) -> int | None:
    """Retry-After в секундах. Форму с датой не разбираем — API её не отдаёт."""
    if not raw:
        return None
    try:
        return int(raw.strip())
    except ValueError:
        return None


def _raise_for_payload(
    status: int,
    payload: Mapping[str, Any],
    header_retry_after: int | None = None,
) -> None:
    """Превращает тело ошибки в типизированное исключение."""
    code = payload.get("code")
    code = code if isinstance(code, str) else None
    message = _detail(payload, f"HTTP {status}")
    cls = ERROR_CLASSES.get(code or "", SrezAIError)
    if cls is RateLimited:
        # Поле называется retryAfterSec — так его отдаёт API и так оно описано в
        # документации. Заголовок Retry-After дублирует его и служит запасным
        # источником, если тело придёт без поля.
        raw = payload.get("retryAfterSec")
        retry_after = int(raw) if isinstance(raw, (int, float)) else None
        if retry_after is None and header_retry_after is not None:
            retry_after = header_retry_after
        raise RateLimited(message, code=code, status=status, retry_after=retry_after)
    raise cls(message, code=code, status=status)


def _make_client(timeout: float) -> httpx.Client:
    """Создаёт httpx.Client, объясняя понятным языком отказ из-за системного прокси.

    httpx умеет только http, https и socks5, а прокси он подхватывает из
    окружения сам — на Windows ещё и из настроек системы. Если там прописан,
    например, socks4, конструктор падает с ``Unknown scheme for proxy URL``, и по
    этому тексту невозможно догадаться, что дело не в SDK и не в ключе.
    """
    try:
        return httpx.Client(timeout=timeout)
    except ValueError as err:
        if "proxy" not in str(err).lower():
            raise
        raise ValueError(
            f"Не удалось создать HTTP-клиент из-за настроек прокси в системе: {err}. "
            "httpx поддерживает только http, https и socks5. Либо исправьте прокси, "
            "либо передайте свой клиент: "
            "SrezAI(client=httpx.Client(trust_env=False))."
        ) from err


class Transport:
    """Синхронный HTTP-транспорт с повторами по кодам из ``RETRY_CODES``."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 2,
        client: httpx.Client | None = None,
    ) -> None:
        key = api_key or os.environ.get("SREZAI_API_KEY")
        if not key:
            raise ValueError(
                "Нужен API-ключ: передайте api_key= или задайте переменную "
                "окружения SREZAI_API_KEY. Ключ создаётся в личном кабинете "
                "на https://srezai.ru/dashboard."
            )
        self.api_key = key
        self.base_url = base_url.rstrip("/")
        self.max_retries = max(0, max_retries)
        self._owns_client = client is None
        self._client = client if client is not None else _make_client(timeout)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def post(self, path: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        # None-поля не отправляем: сервер отличает «не передано» от явного null.
        body = {k: v for k, v in payload.items() if v is not None}
        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "srezai-python/0.1.0",
        }

        last: SrezAIError | None = None
        for attempt in range(self.max_retries + 1):
            try:
                res = self._client.post(url, json=body, headers=headers)
            except httpx.TimeoutException as exc:
                last = SrezAIError(f"Запрос не успел за отведённое время: {exc}")
                if attempt < self.max_retries:
                    time.sleep(_backoff(attempt, None))
                    continue
                raise last from exc
            except httpx.HTTPError as exc:
                raise SrezAIError(f"Сетевая ошибка: {exc}") from exc

            try:
                data = res.json()
            except ValueError:
                raise SrezAIError(
                    f"Ответ не является JSON (HTTP {res.status_code}).",
                    status=res.status_code,
                ) from None

            if res.is_success:
                return data if isinstance(data, dict) else {"data": data}

            payload_map = data if isinstance(data, dict) else {}
            code = payload_map.get("code")
            retryable = isinstance(code, str) and code in RETRY_CODES
            header_hint = _header_seconds(res.headers.get("Retry-After"))
            if retryable and attempt < self.max_retries:
                raw = payload_map.get("retryAfterSec")
                hint = int(raw) if isinstance(raw, (int, float)) else header_hint
                time.sleep(_backoff(attempt, hint))
                continue
            _raise_for_payload(res.status_code, payload_map, header_hint)

        # Недостижимо: цикл либо вернул результат, либо бросил исключение.
        raise last or SrezAIError("Запрос не выполнен.")


def _backoff(attempt: int, retry_after: float | None) -> float:
    """Пауза перед повтором. Подсказку сервера уважаем, но с потолком.

    Без потолка ``retry_after`` при исчерпанной суточной квоте усыпил бы
    вызывающего на часы — а это уже не повтор, а зависание.
    """
    if retry_after is not None and retry_after > 0:
        return min(float(retry_after), 30.0)
    return min(2.0**attempt, 8.0)
