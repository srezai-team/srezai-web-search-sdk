# SDK срезAI

Официальные клиенты [срезAI](https://srezai.ru) — поиск по вебу, чтение страниц
и извлечение структурированных данных для LLM-агентов.

Official [SrezAI](https://srezai.ru) clients: web search, page reading and
structured extraction for LLM agents.

| Пакет | Язык | Установка | Документация |
| --- | --- | --- | --- |
| [`srezai`](https://pypi.org/project/srezai/) | Python 3.10+ | `pip install srezai` | [python/README.md](python/README.md) |
| [`srezai`](https://www.npmjs.com/package/srezai) | Node 18+ | `npm install srezai` | [js/README.md](js/README.md) |

Оба клиента лежат в одном репозитории намеренно: контракт API у них общий, и
менять его нужно в одном месте, одним pull request. Так они не расходятся между
собой — а расхождение SDK с API замечает не разработчик, а его пользователь.

## Быстрый старт / Quickstart

```python
from srezai import SrezAI

with SrezAI() as client:            # ключ из SREZAI_API_KEY
    found = client.search("новости про ИИ", num=5)
```

```ts
import { SrezAI } from "srezai";

const client = new SrezAI();        // ключ из SREZAI_API_KEY
const found = await client.search("новости про ИИ", { num: 5 });
```

Ключ создаётся в [личном кабинете](https://srezai.ru/dashboard).

## Возможности / Capabilities

| Метод | Что делает |
| --- | --- |
| `search` | Поиск по вебу: десятки движков одним запросом |
| `image_search` / `imageSearch` | Поиск картинок: ссылки, источник, разрешение |
| `read_url` / `readUrl` | Страница → плотный Markdown без навигации и рекламы |
| `read_urls` / `readUrls` | То же, до 5 страниц за вызов, параллельно |
| `fetch_page` / `fetchPage` | Скриншот и Markdown через реальный браузер |
| `extract` | Данные строго по вашей схеме, без выдуманных значений |
| `deep_research` / `deepResearch` | Агентное исследование: ищет, читает, синтезирует |

Инструмент `get_usage` (баланс, квота, цены) есть только в
[MCP-сервере](https://github.com/srezai-team/srezai-mcp): REST-эндпоинта для него
пока не существует, в REST это делают заголовки `X-RateLimit-*`.

## Разработка / Development

```bash
cd python && pip install -e ".[dev]" && pytest -q
cd js && npm ci && npm test
```

## Лицензия / License

MIT
