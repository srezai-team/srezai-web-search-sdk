"""Клиент поискового API срезAI.

    from srezai import SrezAI

    client = SrezAI()  # ключ из SREZAI_API_KEY
    hits = client.search("курс рубля к юаню", num=5)
    page = client.read_url("https://example.com")

Все методы синхронные и бросают подклассы :class:`srezai.SrezAIError`.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from typing import Any, Literal

import httpx

if sys.version_info >= (3, 11):
    from typing import Self
else:  # 3.10: Self ещё не в typing
    from typing_extensions import Self

from ._client import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, Transport

Engine = Literal["auto", "fast", "dynamic", "stealth"]
Category = Literal["general", "news", "it", "science"]
Depth = Literal["flash", "auto"]
TimeRange = Literal["", "day", "week", "month", "year"]
Language = Literal["auto", "ru", "en"]

# Глубина answer_search: не путать с Depth у search — другая шкала.
AnswerDepth = Literal["fast", "balanced", "deep"]


class SrezAI:
    """Точка входа в API. Один экземпляр можно держать на всё приложение.

    :param api_key: ключ ``srz_live_…``. По умолчанию берётся из
        переменной окружения ``SREZAI_API_KEY``.
    :param base_url: адрес сервиса. Меняйте для On-Premise-развёртывания.
    :param timeout: таймаут одного запроса, с. По умолчанию 180 — с запасом
        под синхронный DeepResearch.
    :param max_retries: сколько раз повторить при сбое апстрима или лимите.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 2,
        client: httpx.Client | None = None,
    ) -> None:
        self._t = Transport(
            api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            client=client,
        )

    def close(self) -> None:
        """Закрывает HTTP-соединения. Не нужен, если клиент передан извне."""
        self._t.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # --- Поиск ---

    def search(
        self,
        query: str,
        *,
        num: int | None = None,
        category: Category | None = None,
        language: Language | None = None,
        time_range: TimeRange | None = None,
        depth: Depth | None = None,
        excerpts: bool | None = None,
        include_domains: Sequence[str] | None = None,
        exclude_domains: Sequence[str] | None = None,
        engines: Sequence[str] | None = None,
        safesearch: int | None = None,
        pageno: int | None = None,
    ) -> dict[str, Any]:
        """Веб-поиск. Возвращает ``{"results": [...], "meta": {...}}``.

        :param num: сколько результатов (1–30). Просите столько, сколько
            действительно обработаете: остальное лишь занимает контекст.
        :param depth: ``"flash"`` — быстрее и уже, для одного факта;
            ``"auto"`` — больше движков.
        :param excerpts: подтянуть реальный текст топ-страниц. Медленнее на
            пару секунд, зато не нужен отдельный ``read_url``.
        :param include_domains: искать только на этих сайтах (до 10).
        """
        return self._t.post(
            "/api/v1/search",
            {
                "query": query,
                "num": num,
                "category": category,
                "language": language,
                "timeRange": time_range,
                "depth": depth,
                "excerpts": excerpts,
                "includeDomains": list(include_domains) if include_domains else None,
                "excludeDomains": list(exclude_domains) if exclude_domains else None,
                "engines": list(engines) if engines else None,
                "safesearch": safesearch,
                "pageno": pageno,
            },
        )

    def image_search(
        self,
        query: str,
        *,
        num: int | None = None,
        safe: bool | None = None,
        time_range: TimeRange | None = None,
    ) -> dict[str, Any]:
        """Поиск изображений: прямые ссылки, источник и разрешение.

        Картинки не скачиваются — в ответе только ссылки.
        """
        return self._t.post(
            "/api/v1/media",
            {"query": query, "num": num, "safe": safe, "timeRange": time_range},
        )

    # --- Чтение страниц ---

    def read_url(
        self,
        url: str,
        *,
        max_chars: int | None = None,
        engine: Engine | None = None,
    ) -> dict[str, Any]:
        """Текст страницы в чистом markdown: ``{title, markdown, engine, meta}``.

        Дешевле и быстрее :meth:`fetch_page`, потому что не делает скриншот.

        :param engine: ``"auto"`` сам поднимается до браузера, если текста не
            оказалось. Указывайте явно только если знаете сайт.
        :param max_chars: сколько символов вернуть (200–50000).
        """
        return self._t.post(
            "/api/v1/read",
            {"url": url, "maxChars": max_chars, "engine": engine},
        )

    def read_urls(
        self,
        urls: Sequence[str],
        *,
        max_chars: int | None = None,
        engine: Engine | None = None,
    ) -> dict[str, Any]:
        """Читает до 5 страниц за один вызов. Возвращает ``{"pages": [...]}``.

        Страницы читаются параллельно и тарифицируются как отдельные чтения.
        Неудачная ссылка не роняет остальные: у неё в элементе будут ``error``
        и ``code`` вместо ``markdown``.

        На батче ставьте ``max_chars`` скромнее: пять больших страниц вытеснят
        из контекста модели всё остальное.
        """
        return self._t.post(
            "/api/v1/read",
            {"urls": list(urls), "maxChars": max_chars, "engine": engine},
        )

    def fetch_page(self, url: str, *, max_chars: int | None = None) -> dict[str, Any]:
        """Скриншот страницы в реальном браузере плюс её текст.

        Нужен, когда важно *увидеть* вёрстку, цвета и типографику. Если нужен
        только текст — берите :meth:`read_url`, он втрое дешевле.
        """
        return self._t.post("/api/v1/fetch", {"url": url, "maxChars": max_chars})

    # --- Структурированное извлечение ---

    def extract(
        self,
        schema: Mapping[str, Any] | str,
        *,
        url: str | None = None,
        urls: Sequence[str] | None = None,
        instruction: str | None = None,
        engine: Engine | None = None,
    ) -> dict[str, Any]:
        """Возвращает только поля вашей схемы, без текста страницы.

        Экономит контекст против :meth:`read_url`, когда нужны конкретные
        значения: цена, характеристики, автор и дата. Чего на странице нет,
        приходит как ``None`` — значения не выдумываются.

        Схему можно задать сокращённо::

            {"title": "string", "price": "number?", "tags": "string[]"}

        где ``?`` помечает поле необязательным, а ``[]`` — массивом. Полный
        JSON Schema тоже принимается; описания полей повышают точность.

        :param url: одна страница. Взаимоисключающе с ``urls``.
        :param urls: до 5 страниц, одна схема на все. Каждая тарифицируется
            отдельно.
        :param instruction: уточнение, если из схемы неочевидно — например
            «бери цену со скидкой».
        """
        if (url is None) == (urls is None):
            raise ValueError("Передайте либо url=, либо urls= — ровно одно из двух.")
        return self._t.post(
            "/api/v1/extract",
            {
                "url": url,
                "urls": list(urls) if urls else None,
                "schema": schema,
                "instruction": instruction,
                "engine": engine,
            },
        )

    # --- Глубокое исследование ---

    def deep_research(self, query: str) -> dict[str, Any]:
        """Агентное исследование: ищет, читает источники, возвращает ответ.

        Занимает от 10 секунд до 2 минут — под сложные аналитические вопросы,
        не под быстрые факты.

        Вызов синхронный: соединение держится открытым до готовности ответа, а
        job id и колбэков пока нет. Если соединение оборвётся, результат
        потеряется, а повтор спишет кредиты заново — поэтому не ставьте
        ``timeout`` ниже значения по умолчанию и не оборачивайте вызов в
        агрессивный внешний таймаут.
        """
        return self._t.post("/api/v1/deep", {"query": query})

    # --- Answer Search ---

    def answer_search(
        self,
        query: str,
        *,
        depth: AnswerDepth | None = None,
        language: Language | None = None,
    ) -> dict[str, Any]:
        """RAG-ответ по вебу с семантическим ранжированием источников.

        В отличие от :meth:`deep_research`, цена фиксирована по ``depth``, а не
        по объёму ответа: ``"fast"`` — 50 кредитов, ``"balanced"`` (по
        умолчанию на сервере) — 100, ``"deep"`` — 200.

        :param depth: ``"fast"`` — 2 страницы, ``"balanced"`` — 5,
            ``"deep"`` — 10.
        """
        return self._t.post(
            "/api/v1/answer",
            {"query": query, "depth": depth, "language": language},
        )
