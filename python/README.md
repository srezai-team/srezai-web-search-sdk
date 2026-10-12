# srezai — Python-клиент срезAI

[![PyPI](https://img.shields.io/pypi/v/srezai)](https://pypi.org/project/srezai/)
[![Python](https://img.shields.io/pypi/pyversions/srezai)](https://pypi.org/project/srezai/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Официальный Python-клиент [срезAI](https://srezai.ru) — платформы веб-доступа для
LLM-агентов и RAG-систем: поиск по вебу, чтение страниц в Markdown, извлечение
структурированных данных по схеме и агентное исследование.

Official Python client for [срезAI (SrezAI)](https://srezai.ru), a web-access
platform for LLM agents and RAG systems: web search, page reading as Markdown,
schema-driven structured extraction and agentic research.

```bash
pip install srezai
```

Требования: Python 3.10 – 3.13. Единственная зависимость — `httpx`.

## Быстрый старт / Quickstart

```python
from srezai import SrezAI

with SrezAI() as client:  # ключ из SREZAI_API_KEY
    found = client.search("новости про ИИ", num=5, time_range="week")
    for item in found["results"]:
        print(item["title"], item["url"])

    page = client.read_url("https://example.com", max_chars=8000)
    print(page["markdown"])
```

Ключ передаётся аргументом `api_key`, а при его отсутствии берётся из переменной
окружения `SREZAI_API_KEY`. Создать ключ можно в
[личном кабинете](https://srezai.ru/dashboard).

Клиент работает как контекстный менеджер и переиспользует HTTP-соединение внутри
блока `with`, закрывая его на выходе. Для долгоживущего процесса допустимо
создать клиент один раз и вызвать `close()` при завершении.

## Методы / Methods

| Метод | Назначение | Стоимость вызова |
| --- | --- | --- |
| `search(query, ...)` | Веб-поиск по десяткам движков одним запросом | 1 кредит |
| `image_search(query, ...)` | Поиск изображений: ссылки, источник, разрешение | 1 кредит |
| `read_url(url, ...)` | Страница → плотный Markdown без навигации и рекламы | 1 кредит |
| `read_urls(urls, ...)` | То же для группы страниц (до 10 за вызов на платном тарифе, до 5 на бесплатном, параллельно) | 1 кредит за страницу |
| `fetch_page(url, ...)` | Рендер страницы браузером: скриншот и Markdown | 3 кредита |
| `extract(schema, url=...)` | Данные строго по схеме, без выдуманных значений | 2 кредита за страницу |
| `deep_research(query)` | Агентное исследование: поиск, чтение, синтез ответа | 20 кредитов + 3 за 1000 токенов ответа |
| `answer_search(query, ...)` | RAG-ответ по вебу с семантическим ранжированием источников | 3 / 5 / 10 кредитов — по `depth` |

Тарифная сетка и калькулятор — на странице
[цен](https://srezai.ru/pricing); полное описание параметров — в
[документации API](https://srezai.ru/docs).

Инструмент учёта `get_usage` (баланс, квота, цены) в SDK отсутствует: он доступен
только через [MCP-сервер](https://github.com/srezai-team/srezai-mcp), REST-
эндпоинта для него не предусмотрено. В REST эту роль выполняют заголовки
`X-RateLimit-*` в каждом ответе.

### Поиск

```python
found = client.search(
    "векторные базы данных",
    num=10,
    category="it",  # general | news | it | science
    language="ru",  # auto | ru | en
    time_range="month",  # "" | day | week | month | year
    depth="auto",  # flash — быстрее и уже; auto — шире
    excerpts=True,  # подтянуть текст топ-страниц
    include_domains=["habr.com"],  # только эти сайты и их поддомены
)
```

### Чтение страниц

```python
page = client.read_url("https://example.com", max_chars=8000, engine="auto")
batch = client.read_urls(["https://a.example", "https://b.example"], max_chars=4000)
```

Параметр `engine` управляет способом загрузки. По умолчанию `auto`: клиент
начинает с быстрого способа и повышает ступень самостоятельно, если содержимое не
получено. Явное значение имеет смысл указывать только для заранее известного
сайта — `fast` для статики и документации, `dynamic` для SPA, требующих
выполнения JavaScript, `stealth` для максимально приближенного к браузеру
поведения.

На батче стоит задавать `max_chars` скромнее: пять больших страниц вытеснят из
контекста модели всё остальное. Если часть адресов не открылась, остальные
возвращаются, а неудачи перечисляются в ответе.

### Извлечение структурированных данных

```python
data = client.extract(
    {"title": "string", "price": "number?", "tags": "string[]"},
    url="https://shop.example/item/42",
    instruction="использовать цену со скидкой",
)
```

Схема задаётся сокращённой формой (`?` — необязательное поле, `[]` — массив) или
полным JSON Schema; описания полей в полной форме заметно повышают точность
разбора. Значения, которых на странице нет, возвращаются как `null` и никогда не
достраиваются моделью. Для группы страниц под одну схему используется `urls=`
(до 10 адресов на платном тарифе, до 5 на бесплатном; каждый тарифицируется
отдельно) — взаимоисключимо с `url=`.

### Answer Search

```python
result = client.answer_search(
    "как работает BGE-reranker",
    depth="balanced",  # fast | balanced (по умолчанию) | deep
)
print(result["answer"])
for s in result["sources"]:
    print(s["title"], s["url"], s["relevance"])
```

В отличие от `deep_research`, стоимость фиксирована по `depth` и не зависит от
объёма ответа: `fast` — 50 кредитов, `balanced` — 100, `deep` — 200. `sources`
отсортированы по релевантности через семантический реранкер, а не только по
порядку поиска.

## Обработка ошибок / Errors

Каждая ошибка API содержит машинный код, которому соответствует отдельный класс
исключения. Это позволяет ветвиться по типу ошибки, не разбирая текст сообщения.
Если код не важен, достаточно перехватить базовый `SrezAIError`.

```python
from srezai import SrezAI, HostUnresolved, RateLimited, SsrfBlocked

with SrezAI() as client:
    try:
        client.read_url("https://exmaple.com")
    except HostUnresolved:
        ...  # домена не существует — вероятна опечатка в адресе
    except SsrfBlocked:
        ...  # адрес запрашивать нельзя: локальная сеть или служебный диапазон
    except RateLimited as err:
        ...  # лимит; err.retry_after — секунды до следующей попытки
```

`HostUnresolved` и `SsrfBlocked` различаются намеренно: первое означает
«проверьте адрес на опечатку», второе — «такой адрес запрашивать нельзя». Полный
каталог кодов — на [srezai.ru/docs/errors](https://srezai.ru/docs/errors).

Клиент автоматически повторяет запрос при временных сбоях — `rate_limited`,
`service_unavailable`, `search_unavailable`, `upstream_timeout` — с
экспоненциальной задержкой и приоритетом подсказки `retry_after` от сервера.
Ошибки запроса (`bad_request`, `schema_invalid`, `unauthorized`, `ssrf_blocked`)
возвращаются немедленно: их повтор не изменит результат.

## Конфигурация / Configuration

```python
client = SrezAI(
    api_key="srz_live_…",  # по умолчанию — SREZAI_API_KEY
    base_url="https://srezai.ru",  # для стейджинга или изолированного контура
    timeout=180.0,  # секунды; deep_research идёт до двух минут
    max_retries=2,
)
```

Таймаут по умолчанию выбран с запасом под `deep_research`: он синхронный и
занимает до двух минут. Уменьшать его стоит только если этот метод не
используется — оборванное соединение не отменяет уже начатую работу на сервере.

## Ограничения частоты / Rate limits

Ключ API: 10 запросов за 10 секунд и 200 запросов в сутки. Батчевые методы
`read_urls` и `extract` принимают до 10 адресов за вызов на платном тарифе
(до 5 на бесплатном). Текущее состояние квоты
возвращается в заголовках `X-RateLimit-*`. Лимиты выше базовых согласуются
индивидуально — [support@srezai.ru](mailto:support@srezai.ru).

## Типизация и разработка / Typing and development

Пакет поставляется с маркером `py.typed` и проходит `mypy --strict`, поэтому
подсказки типов доступны в потребляющем коде без дополнительных заглушек.

```bash
pip install -e ".[dev]" && ruff check . && mypy src && pytest -q
```

Тесты выполняются локально на `pytest-httpx` и обращений к рабочему API не
требуют.

## Поддержка и лицензия / Support and license

- Документация API — [srezai.ru/docs](https://srezai.ru/docs)
- Вопросы и дефекты — [GitHub Issues](https://github.com/srezai-team/srezai-sdk/issues)
- Техническая поддержка — [support@srezai.ru](mailto:support@srezai.ru)

Лицензия — [MIT](LICENSE).
