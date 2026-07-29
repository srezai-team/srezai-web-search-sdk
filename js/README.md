# srezai

Официальный JS/TypeScript-клиент [срезAI](https://srezai.ru) — поиск, чтение
страниц и извлечение структурированных данных для LLM-агентов.

Official JS/TypeScript client for [SrezAI](https://srezai.ru): search, page
reading and structured extraction built for LLM agents.

```bash
npm install srezai
```

## Быстрый старт / Quickstart

```ts
import { SrezAI } from "srezai";

const client = new SrezAI(); // ключ из SREZAI_API_KEY

const { results } = await client.search<{ results: Array<{ title: string; url: string }> }>(
  "новости про ИИ",
  { num: 5, timeRange: "week" },
);
for (const item of results) console.log(item.title, item.url);

const page = await client.readUrl("https://example.com", { maxChars: 8000 });
```

Ключ берётся из `apiKey`, а если его нет — из переменной окружения
`SREZAI_API_KEY`. Получить ключ можно в [дашборде](https://srezai.ru/dashboard).

Работает в Node 18+ на встроенном `fetch`, без зависимостей. Можно передать свой
`fetch` — например, обёрнутый в трассировку.

## Методы / Methods

| Метод | Что делает |
| --- | --- |
| `search(query, opts?)` | Поиск по вебу: десятки движков одним запросом |
| `imageSearch(query, opts?)` | Поиск картинок |
| `readUrl(url, opts?)` | Страница → плотный Markdown |
| `readUrls(urls, opts?)` | То же, до 5 страниц за один вызов |
| `fetchPage(url, opts?)` | Скриншот и Markdown через реальный браузер |
| `extract(schema, opts)` | Данные по вашей схеме, без выдуманных значений |
| `deepResearch(query)` | Агентное исследование: ищет, читает, синтезирует |

Полный список параметров — в [документации API](https://srezai.ru/docs).

`get_usage` (баланс и цены) в SDK нет: этот инструмент доступен только через
MCP-сервер, REST-эндпоинта для него пока не существует.

## Извлечение по схеме / Structured extraction

```ts
const data = await client.extract<{ title: string; price: number | null }>(
  { title: "string", price: "number?" },
  { url: "https://shop.example/item/42", instruction: "бери цену со скидкой" },
);
```

Схему можно задать сокращённо (`"number?"` — необязательное, `"string[]"` —
массив) или полным JSON Schema. Чего на странице нет, приходит как `null`:
значения не выдумываются. Описания полей заметно повышают точность.

## Ошибки / Errors

Каждая ошибка API приходит с машинным кодом, и клиент поднимает свой класс на
каждый код. Ловите базовый `SrezAIError`, если код не важен.

```ts
import { SrezAI, HostUnresolved, RateLimited, SsrfBlocked } from "srezai";

try {
  await client.readUrl("https://exmaple.com");
} catch (err) {
  if (err instanceof HostUnresolved) {
    // домена не существует — скорее всего опечатка в адресе
  } else if (err instanceof SsrfBlocked) {
    // адрес запрещён: локальная сеть или нестандартный порт
  } else if (err instanceof RateLimited) {
    console.log("лимит; повторить через", err.retryAfter, "с");
  } else throw err;
}
```

`HostUnresolved` и `SsrfBlocked` — разные вещи: первое значит «проверьте адрес
на опечатку», второе — «такой адрес запрашивать нельзя».

Клиент сам повторяет запрос при `rate_limited`, `service_unavailable`,
`search_unavailable` и `upstream_timeout` — с экспоненциальной задержкой и с
учётом `retryAfterSec` от сервера. Остальные коды возвращаются сразу: повтор
`bad_request` ничего не изменит.

## Настройка / Configuration

```ts
const client = new SrezAI({
  apiKey: "srz_live_...",
  baseUrl: "https://srezai.ru", // для self-hosted или стейджинга
  timeoutMs: 180_000,           // deepResearch идёт до двух минут
  maxRetries: 2,
});
```

## Лицензия / License

MIT
