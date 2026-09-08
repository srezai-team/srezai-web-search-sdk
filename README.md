# срезAI SDK

[![PyPI](https://img.shields.io/pypi/v/srezai?label=pypi%20srezai)](https://pypi.org/project/srezai/)
[![npm](https://img.shields.io/npm/v/srezai?label=npm%20srezai)](https://www.npmjs.com/package/srezai)
[![CI](https://github.com/srezai-team/srezai-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/srezai-team/srezai-sdk/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Официальные клиентские библиотеки [срезAI](https://srezai.ru) — платформы
веб-доступа для LLM-агентов и RAG-систем: поиск по вебу, чтение страниц в
Markdown, извлечение структурированных данных по схеме и агентное исследование
через единый REST API.

Official client libraries for [срезAI (SrezAI)](https://srezai.ru), a web-access
platform for LLM agents and RAG systems: web search, page reading as Markdown,
schema-driven structured extraction and agentic research over a single REST API.

## Пакеты / Packages

| Пакет | Среда выполнения | Установка | Документация |
| --- | --- | --- | --- |
| [`srezai`](https://pypi.org/project/srezai/) (PyPI) | Python 3.10 – 3.13 | `pip install srezai` | [python/README.md](python/README.md) |
| [`srezai`](https://www.npmjs.com/package/srezai) (npm) | Node.js 18, 20, 22 | `npm install srezai` | [js/README.md](js/README.md) |

Дополнительно платформа доступна как
[MCP-сервер](https://github.com/srezai-team/srezai-mcp) — для сред, работающих по
Model Context Protocol.

Оба клиента находятся в одном репозитории намеренно: контракт API у них общий и
изменяется одним pull request. Это исключает расхождение реализаций между собой и
с сервером — расхождение, которое обнаруживает не разработчик библиотеки, а
пользователь его продукта.

## Быстрый старт / Quickstart

Ключ API создаётся в [личном кабинете](https://srezai.ru/dashboard) и передаётся
либо аргументом конструктора, либо переменной окружения `SREZAI_API_KEY`.

```python
from srezai import SrezAI

with SrezAI() as client:                      # ключ из SREZAI_API_KEY
    found = client.search("новости про ИИ", num=5, time_range="week")
    for item in found["results"]:
        print(item["title"], item["url"])

    page = client.read_url("https://example.com", max_chars=8000)
    print(page["markdown"])
```

```ts
import { SrezAI } from "srezai";

const client = new SrezAI();                  // ключ из SREZAI_API_KEY

const { results } = await client.search("новости про ИИ", {
  num: 5,
  timeRange: "week",
});
for (const item of results) console.log(item.title, item.url);

const page = await client.readUrl("https://example.com", { maxChars: 8000 });
```

## Возможности / Capabilities

| Метод (Python / JS) | Назначение | Стоимость вызова |
| --- | --- | --- |
| `search` | Веб-поиск по десяткам движков одним запросом; фильтры по категории, языку, свежести и домену | 1 кредит |
| `image_search` / `imageSearch` | Поиск изображений: прямые ссылки, страница-источник, разрешение | 1 кредит |
| `read_url` / `readUrl` | Страница → плотный Markdown без навигации, рекламы и разметки | 1 кредит |
| `read_urls` / `readUrls` | То же для группы страниц (до 5 за вызов, параллельно) | 1 кредит за страницу |
| `fetch_page` / `fetchPage` | Рендер страницы полноценным браузером: скриншот и Markdown | 3 кредита |
| `extract` | Данные строго по заданной схеме; отсутствующие поля возвращаются как `null` | 4 кредита за страницу |
| `deep_research` / `deepResearch` | Агентное исследование: поиск, чтение источников, синтез связного ответа со ссылками | 20 кредитов + 3 за 1000 токенов ответа |
| `answer_search` / `answerSearch` | RAG-ответ по вебу с семантическим ранжированием источников (BGE-reranker) | 50 / 100 / 200 кредитов — по `depth` |

Актуальная тарифная сетка и калькулятор — на странице
[цен и тарифов](https://srezai.ru/pricing). Полное описание параметров каждого
метода — в [документации API](https://srezai.ru/docs).

Инструмент учёта `get_usage` (баланс, квота, цены) доступен только через
MCP-сервер: REST-эндпоинта для него не предусмотрено, в REST эту роль выполняют
заголовки `X-RateLimit-*` в каждом ответе.

### Способ получения страницы

Параметр `engine` управляет тем, как загружается страница. По умолчанию
используется `auto`: клиент начинает с быстрого способа и повышает ступень
самостоятельно, если содержимое не получено. Явное значение имеет смысл
указывать только для заранее известного сайта.

| Значение | Применение |
| --- | --- |
| `auto` | По умолчанию. Подбирает способ автоматически |
| `fast` | Статические страницы и документация |
| `dynamic` | SPA и страницы, требующие выполнения JavaScript |
| `stealth` | Максимально приближенное к браузеру поведение; самый медленный |

### Извлечение структурированных данных

Схема задаётся сокращённой формой или полным JSON Schema. Значения, которых на
странице нет, возвращаются как `null` и никогда не достраиваются моделью.

```python
data = client.extract(
    {"title": "string", "price": "number?", "tags": "string[]"},
    url="https://shop.example/item/42",
    instruction="использовать цену со скидкой",
)
```

```ts
const data = await client.extract<{ title: string; price: number | null }>(
  { title: "string", price: "number?" },
  { url: "https://shop.example/item/42", instruction: "использовать цену со скидкой" },
);
```

В сокращённой форме `?` помечает поле необязательным, `[]` — массивом. Описания
полей в полной форме JSON Schema заметно повышают точность разбора.

## Обработка ошибок и устойчивость / Errors and resilience

Каждая ошибка API содержит машинный код в теле ответа. Клиенты сопоставляют коды
с типизированными классами исключений, что позволяет ветвиться по типу ошибки, а
не разбирать текст сообщения.

```python
from srezai import SrezAI, HostUnresolved, RateLimited, SsrfBlocked

try:
    client.read_url("https://exmaple.com")
except HostUnresolved:
    ...  # домена не существует — вероятна опечатка в адресе
except SsrfBlocked:
    ...  # адрес запрашивать нельзя: локальная сеть или служебный диапазон
except RateLimited as err:
    ...  # лимит; err.retry_after — секунды до следующей попытки
```

Транспорт автоматически повторяет запрос при временных сбоях — `rate_limited`,
`service_unavailable`, `search_unavailable`, `upstream_timeout` — с
экспоненциальной задержкой и приоритетом подсказки `retryAfterSec` от сервера.
Ошибки запроса (`bad_request`, `schema_invalid`, `unauthorized`, `ssrf_blocked`)
возвращаются немедленно: их повтор не изменит результат.

Полный перечень кодов — в [справочнике ошибок](https://srezai.ru/docs/errors).

## Конфигурация / Configuration

```ts
const client = new SrezAI({
  apiKey: "srz_live_…",         // по умолчанию — SREZAI_API_KEY
  baseUrl: "https://srezai.ru", // для стейджинга или изолированного контура
  timeoutMs: 180_000,           // deepResearch выполняется до двух минут
  maxRetries: 2,
});
```

Оба клиента принимают эквивалентный набор параметров. Python-клиент поддерживает
контекстный менеджер и переиспользует HTTP-соединение; JS-клиент допускает
подстановку собственной реализации `fetch` — например, обёрнутой в трассировку
или направленной через корпоративный прокси.

## Ограничения частоты / Rate limits

| Область | Пиковый лимит | Суточная квота |
| --- | --- | --- |
| API-ключ | 10 запросов / 10 с | 200 запросов |

Батчевые методы `read_urls` и `extract` принимают до 5 адресов за вызов; каждый
адрес тарифицируется отдельно. Текущее состояние квоты возвращается в заголовках
`X-RateLimit-Limit`, `X-RateLimit-Remaining` и `X-RateLimit-Reset`. Лимиты выше
базовых согласуются индивидуально — [support@srezai.ru](mailto:support@srezai.ru).

## Инженерные гарантии / Engineering guarantees

- **Строгая типизация.** Python-пакет поставляется с маркером `py.typed` и
  проходит `mypy --strict`; JS-пакет собирается в строгом режиме TypeScript и
  экспортирует декларации типов.
- **Двойная сборка JS.** Пакет публикуется в ESM и CommonJS с отдельными
  декларациями для каждого формата — подключается и в современных сборках, и в
  унаследованных.
- **Минимум зависимостей.** JS-клиент работает на встроенном в Node.js `fetch` и
  не имеет зависимостей вовсе; Python-клиент зависит только от `httpx`.
- **Матричное тестирование.** CI проверяет Python 3.10 – 3.13 и Node.js 18, 20,
  22 на каждый push и pull request. Python-сборка дополнительно устанавливается в
  чистое окружение — так выявляются необъявленные зависимости, которые в
  dev-окружении приезжают попутно с линтерами.
- **Семантическое версионирование.** Ломающие изменения публичного контракта
  выпускаются только с повышением мажорной версии.

## Структура репозитория / Repository layout

```
python/   Python-клиент: src/srezai, tests, pyproject.toml
js/       JS/TypeScript-клиент: src, test, package.json
.github/  CI и публикация пакетов в PyPI и npm
```

## Разработка / Development

```bash
cd python && pip install -e ".[dev]" && ruff check . && mypy src && pytest -q
```

```bash
cd js && npm ci && npm run typecheck && npm test && npm run build
```

Тесты выполняются полностью локально и обращений к рабочему API не требуют:
Python использует `pytest-httpx`, JS — локальный HTTP-сервер из `js/test`.

Pull request принимаются. Изменение контракта API затрагивает оба клиента
одновременно: правка в одном без второго приводит к расхождению поверхностей.

## Поддержка и лицензия / Support and license

- Документация API — [srezai.ru/docs](https://srezai.ru/docs)
- Вопросы и дефекты — [GitHub Issues](https://github.com/srezai-team/srezai-sdk/issues)
- Техническая поддержка — [support@srezai.ru](mailto:support@srezai.ru)
- Коммерческие условия и интеграция — [hello@srezai.ru](mailto:hello@srezai.ru)

Исходный код распространяется по лицензии [MIT](LICENSE).
