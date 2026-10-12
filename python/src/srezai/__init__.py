"""срезAI — поисковый API для ИИ-агентов.

    from srezai import SrezAI

    client = SrezAI()
    print(client.search("новости ИИ", num=5, time_range="day"))

Документация: https://srezai.ru/docs
"""

from .client import SrezAI
from .errors import (
    BadRequest,
    ExtractFailed,
    HostUnresolved,
    RateLimited,
    ReadFailed,
    SchemaInvalid,
    SearchUnavailable,
    ServiceUnavailable,
    SrezAIError,
    SsrfBlocked,
    Unauthorized,
    UpstreamTimeout,
)

__version__ = "0.2.1"

__all__ = [
    "BadRequest",
    "ExtractFailed",
    "HostUnresolved",
    "RateLimited",
    "ReadFailed",
    "SchemaInvalid",
    "SearchUnavailable",
    "ServiceUnavailable",
    "SrezAI",
    "SrezAIError",
    "SsrfBlocked",
    "Unauthorized",
    "UpstreamTimeout",
    "__version__",
]
