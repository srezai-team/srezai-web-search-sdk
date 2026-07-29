"""Ошибки API, разобранные по машинному коду.

Сервис отдаёт в теле ответа поле ``code`` — стабильный машинный идентификатор,
и ``error`` — человекочитаемый текст на двух языках. Ветвиться нужно по коду:
текст может измениться, код — нет.

Практическая разница, которую стоит знать до чтения кода ниже:

* ``SsrfBlocked`` — адрес запрещён (приватная сеть, нестандартный порт).
  Повторять бессмысленно, нужен другой URL.
* ``HostUnresolved`` — домена не существует или молчит DNS. Это не запрет:
  чаще всего в ссылке опечатка.
* ``RateLimited`` — единственная ошибка, у которой есть ``retry_after``.
* ``ServiceUnavailable`` / ``SearchUnavailable`` / ``UpstreamTimeout`` — сбой на
  нашей стороне либо у апстрима: повтор имеет смысл.
"""

from __future__ import annotations


class SrezAIError(Exception):
    """Базовая ошибка. Ловите её, если код ошибки не важен."""

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status

    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


class Unauthorized(SrezAIError):
    """Ключ отсутствует, отозван или не тот. Повтор не поможет."""


class RateLimited(SrezAIError):
    """Лимит исчерпан. ``retry_after`` — через сколько секунд можно повторить.

    Отказ по анти-флуду (burst) суточную квоту не расходует, так что короткая
    пауза действительно решает проблему.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status: int | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message, code=code, status=status)
        self.retry_after = retry_after


class BadRequest(SrezAIError):
    """Некорректные параметры. Текст ошибки называет поле."""


class SchemaInvalid(BadRequest):
    """Схема ``extract`` не разобралась. Текст указывает путь до проблемы."""


class SsrfBlocked(SrezAIError):
    """Адрес запрещён: разрешены только публичные http/https на портах 80/443."""


class HostUnresolved(SrezAIError):
    """Домена нет или DNS не отвечает. Не запрет — проверьте адрес на опечатку."""


class ReadFailed(SrezAIError):
    """Страница не отдала текст. Иногда помогает повтор с ``engine="stealth"``."""


class ExtractFailed(SrezAIError):
    """Данные по схеме извлечь не удалось."""


class SearchUnavailable(SrezAIError):
    """Движки не ответили. Это временный сбой, а не отсутствие информации."""


class UpstreamTimeout(SrezAIError):
    """Апстрим не успел. Повторите или сузьте задачу."""


class ServiceUnavailable(SrezAIError):
    """Сбой на нашей стороне. Запрос корректен, повторите позже."""


# Соответствие машинного кода классу. Неизвестный код — базовый SrezAIError:
# новый код на сервере не должен ломать старый клиент.
ERROR_CLASSES: dict[str, type[SrezAIError]] = {
    "unauthorized": Unauthorized,
    "rate_limited": RateLimited,
    "bad_request": BadRequest,
    "schema_invalid": SchemaInvalid,
    "method_not_allowed": BadRequest,
    "ssrf_blocked": SsrfBlocked,
    "host_unresolved": HostUnresolved,
    "read_failed": ReadFailed,
    "extract_failed": ExtractFailed,
    "search_unavailable": SearchUnavailable,
    "upstream_timeout": UpstreamTimeout,
    "service_unavailable": ServiceUnavailable,
    "empty_result": SrezAIError,
}
