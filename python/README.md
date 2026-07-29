# srezai-python

Официальный Python-клиент [SrezAI](https://srezai.ru) — поиск, чтение страниц и
извлечение структурированных данных для LLM-агентов.

Official Python client for [SrezAI](https://srezai.ru): search, page reading and
structured extraction built for LLM agents.

```bash
pip install srezai
```

## Быстрый старт / Quickstart

```python
from srezai import SrezAI

client = SrezAI(api_key="srz_...")  # или переменная окружения SREZAI_API_KEY

results = client.search("новости про ИИ", num=5, time_range="week")
for item in results["results"]:
    print(item["title"], item["url"])

page = client.read_url("https://example.com", max_chars=8000)
print(page["markdown"])
```

Ключ берётся из аргумента `api_key`, а если его нет — из переменной окружения
`SREZAI_API_KEY`. Получить ключ можно в [дашборде](https://srezai.ru/dashboard).

## Методы / Methods

| Метод | Что делает |
| --- | --- |
| `search(query, ...)` | Поиск по вебу: десятки движков одним запросом |
| `image_search(query, ...)` | Поиск картинок |
| `read_url(url, ...)` | Страница → плотный Markdown |
| `read_urls(urls, ...)` | То же, до 5 страниц за один вызов |
| `fetch_page(url, ...)` | Скриншот + Markdown через реальный браузер |
| `extract(schema, url=...)` | Данные по вашей JSON-схеме, без выдуманных значений |
| `deep_research(query)` | Агентное исследование: ищет, читает, синтезирует ответ |

Полный список параметров каждого метода — в
[документации API](https://srezai.ru/docs).

`get_usage` (баланс и цены) в SDK нет: этот инструмент доступен только через
MCP-сервер, REST-эндпоинта для него пока не существует.

## Ошибки / Errors

Каждая ошибка API приходит с машинным кодом, и клиент поднимает свой класс
исключения на каждый код. Ловите базовый `SrezAIError`, если код не важен.

```python
from srezai import SrezAI, HostUnresolved, RateLimited, SsrfBlocked

client = SrezAI()
try:
    client.read_url("https://exmaple.com")
except HostUnresolved:
    print("домена не существует — скорее всего опечатка в адресе")
except SsrfBlocked:
    print("адрес запрещён: локальная сеть или нестандартный порт")
except RateLimited as err:
    print("лимит; повторить через", err.retry_after, "с")
```

`HostUnresolved` и `SsrfBlocked` — разные вещи: первое значит «проверьте адрес
на опечатку», второе — «такой адрес запрашивать нельзя». Каталог всех кодов
лежит на [srezai.ru/docs/errors](https://srezai.ru/docs/errors).

Клиент сам повторяет запрос при `rate_limited`, `service_unavailable`,
`search_unavailable` и `upstream_timeout` — с экспоненциальной задержкой и с
учётом `retry_after` от сервера. Остальные коды возвращаются сразу: повтор
`bad_request` ничего не изменит.

## Настройка / Configuration

```python
client = SrezAI(
    api_key="srz_...",
    base_url="https://srezai.ru",  # для self-hosted или стейджинга
    timeout=180.0,  # секунды; deep_research идёт до 2 минут
    max_retries=2,
)
```

`SrezAI` работает как контекстный менеджер и закрывает HTTP-соединения на
выходе:

```python
with SrezAI() as client:
    client.search("запрос")
```

## Лицензия / License

MIT
