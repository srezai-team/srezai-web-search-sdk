# srezai — JS/TypeScript-клиент срезAI

[![npm](https://img.shields.io/npm/v/srezai)](https://www.npmjs.com/package/srezai)
[![Node](https://img.shields.io/node/v/srezai)](https://www.npmjs.com/package/srezai)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Официальный JS/TypeScript-клиент [срезAI](https://srezai.ru) — платформы
веб-доступа для LLM-агентов и RAG-систем: поиск по вебу, чтение страниц в
Markdown, извлечение структурированных данных по схеме и агентное исследование.

Official JS/TypeScript client for [срезAI (SrezAI)](https://srezai.ru), a
web-access platform for LLM agents and RAG systems: web search, page reading as
Markdown, schema-driven structured extraction and agentic research.

```bash
npm install srezai
```

Требования: Node.js 18 и выше. Зависимостей нет — клиент работает на встроенном
`fetch`. Пакет публикуется в ESM и CommonJS с отдельными декларациями типов для
каждого формата.

## Быстрый старт / Quickstart

```ts
import { SrezAI } from "srezai";

const client = new SrezAI();                  // ключ из SREZAI_API_KEY

const { results } = await client.search<{
  results: Array<{ title: string; url: string }>;
}>("новости про ИИ", { num: 5, timeRange: "week" });

for (const item of results) console.log(item.title, item.url);

const page = await client.readUrl("https://example.com", { maxChars: 8000 });
```

Ключ передаётся параметром `apiKey`, а при его отсутствии берётся из переменной
окружения `SREZAI_API_KEY`. Создать ключ можно в
[личном кабинете](https://srezai.ru/dashboard).

Методы принимают параметр типа для формы ответа — это позволяет типизировать
результат под конкретный запрос, не полагаясь на общий индексный тип.

## Методы / Methods

| Метод | Назначение | Стоимость вызова |
| --- | --- | --- |
| `search(query, opts?)` | Веб-поиск по десяткам движков одним запросом | 1 кредит |
| `imageSearch(query, opts?)` | Поиск изображений: ссылки, источник, разрешение | 1 кредит |
| `readUrl(url, opts?)` | Страница → плотный Markdown без навигации и рекламы | 1 кредит |
| `readUrls(urls, opts?)` | То же для группы страниц (до 10 за вызов на платном тарифе, до 5 на бесплатном, параллельно) | 1 кредит за страницу |
| `fetchPage(url, opts?)` | Рендер страницы браузером: скриншот и Markdown | 3 кредита |
| `extract(schema, opts)` | Данные строго по схеме, без выдуманных значений | 2 кредита за страницу |
| `deepResearch(query)` | Агентное исследование: поиск, чтение, синтез ответа | 20 кредитов + 3 за 1000 токенов ответа |
| `answerSearch(query, opts?)` | RAG-ответ по вебу с семантическим ранжированием источников | 3 / 5 / 10 кредитов — по `depth` |

Тарифная сетка и калькулятор — на странице
[цен](https://srezai.ru/pricing); полное описание параметров — в
[документации API](https://srezai.ru/docs).

Инструмент учёта `get_usage` (баланс, квота, цены) в SDK отсутствует: он доступен
только через [MCP-сервер](https://github.com/srezai-team/srezai-mcp-web-search),
REST-эндпоинта для него не предусмотрено. В REST эту роль выполняют заголовки
`X-RateLimit-*` в каждом ответе.

### Поиск

```ts
const found = await client.search("векторные базы данных", {
  num: 10,
  category: "it",                 // general | news | it | science
  language: "ru",                 // auto | ru | en
  timeRange: "month",             // "" | day | week | month | year
  depth: "auto",                  // flash — быстрее и уже; auto — шире
  excerpts: true,                 // подтянуть текст топ-страниц
  includeDomains: ["habr.com"],   // только эти сайты и их поддомены
});
```

Все перечисления описаны литеральными типами, поэтому опечатка в значении
`category` или `timeRange` обнаруживается на этапе компиляции, а не в рантайме.

### Чтение страниц

```ts
const page = await client.readUrl("https://example.com", {
  maxChars: 8000,
  engine: "auto",
});

const batch = await client.readUrls(
  ["https://a.example", "https://b.example"],
  { maxChars: 4000 },
);
```

Параметр `engine` управляет способом загрузки. По умолчанию `auto`: клиент
начинает с быстрого способа и повышает ступень самостоятельно, если содержимое не
получено. Явное значение имеет смысл указывать только для заранее известного
сайта — `fast` для статики и документации, `dynamic` для SPA, требующих
выполнения JavaScript, `stealth` для максимально приближенного к браузеру
поведения.

На батче стоит задавать `maxChars` скромнее: пять больших страниц вытеснят из
контекста модели всё остальное. Если часть адресов не открылась, остальные
возвращаются, а неудачи перечисляются в ответе.

### Извлечение структурированных данных

```ts
const data = await client.extract<{ title: string; price: number | null }>(
  { title: "string", price: "number?", tags: "string[]" },
  {
    url: "https://shop.example/item/42",
    instruction: "использовать цену со скидкой",
  },
);
```

Схема задаётся сокращённой формой (`?` — необязательное поле, `[]` — массив) или
полным JSON Schema; описания полей в полной форме заметно повышают точность
разбора. Значения, которых на странице нет, возвращаются как `null` и никогда не
достраиваются моделью. Для группы страниц под одну схему используется `urls`
(до 10 адресов на платном тарифе, до 5 на бесплатном; каждый тарифицируется
отдельно) — взаимоисключимо с `url`.

### Answer Search

```ts
const { answer, sources, confidence } = await client.answerSearch(
  "как работает BGE-reranker",
  { depth: "balanced" },   // fast | balanced (по умолчанию) | deep
);
console.log(answer);
for (const s of sources) console.log(s.title, s.url, s.relevance);
```

В отличие от `deepResearch`, стоимость фиксирована по `depth` и не зависит от
объёма ответа: `fast` — 50 кредитов, `balanced` — 100, `deep` — 200. `sources`
отсортированы по релевантности через семантический реранкер, а не только по
порядку поиска.

## Обработка ошибок / Errors

Каждая ошибка API содержит машинный код, которому соответствует отдельный класс
исключения. Это позволяет ветвиться по типу ошибки, не разбирая текст сообщения.
Если код не важен, достаточно перехватить базовый `SrezAIError`.

```ts
import { SrezAI, HostUnresolved, RateLimited, SsrfBlocked } from "srezai";

try {
  await client.readUrl("https://exmaple.com");
} catch (err) {
  if (err instanceof HostUnresolved) {
    // домена не существует — вероятна опечатка в адресе
  } else if (err instanceof SsrfBlocked) {
    // адрес запрашивать нельзя: локальная сеть или служебный диапазон
  } else if (err instanceof RateLimited) {
    console.log("лимит; повторить через", err.retryAfter, "с");
  } else throw err;
}
```

`HostUnresolved` и `SsrfBlocked` различаются намеренно: первое означает
«проверьте адрес на опечатку», второе — «такой адрес запрашивать нельзя». Полный
каталог кодов — на [srezai.ru/docs/errors](https://srezai.ru/docs/errors).

Клиент автоматически повторяет запрос при временных сбоях — `rate_limited`,
`service_unavailable`, `search_unavailable`, `upstream_timeout` — с
экспоненциальной задержкой и приоритетом подсказки `retryAfterSec` от сервера.
Ошибки запроса (`bad_request`, `schema_invalid`, `unauthorized`, `ssrf_blocked`)
возвращаются немедленно: их повтор не изменит результат.

## Конфигурация / Configuration

```ts
const client = new SrezAI({
  apiKey: "srz_live_…",         // по умолчанию — SREZAI_API_KEY
  baseUrl: "https://srezai.ru", // для стейджинга или изолированного контура
  timeoutMs: 180_000,           // deepResearch выполняется до двух минут
  maxRetries: 2,
  fetch: instrumentedFetch,     // своя реализация fetch
});
```

Подстановка `fetch` предусмотрена для сред, где исходящие запросы проходят через
трассировку, корпоративный прокси или собственный слой политик — клиент не
навязывает свой транспорт.

Таймаут по умолчанию выбран с запасом под `deepResearch`: он синхронный и
занимает до двух минут. Уменьшать его стоит только если этот метод не
используется — оборванное соединение не отменяет уже начатую работу на сервере.

## Ограничения частоты / Rate limits

Ключ API: 10 запросов за 10 секунд и 200 запросов в сутки. Батчевые методы
`readUrls` и `extract` принимают до 10 адресов за вызов на платном тарифе
(до 5 на бесплатном). Текущее состояние квоты
возвращается в заголовках `X-RateLimit-*`. Лимиты выше базовых согласуются
индивидуально — [support@srezai.ru](mailto:support@srezai.ru).

## Разработка / Development

```bash
npm ci && npm run typecheck && npm test && npm run build
```

Тесты выполняются локально против HTTP-сервера из `test/` и обращений к рабочему
API не требуют.

## Поддержка и лицензия / Support and license

- Документация API — [srezai.ru/docs](https://srezai.ru/docs)
- Вопросы и дефекты — [GitHub Issues](https://github.com/srezai-team/srezai-web-search-sdk/issues)
- Техническая поддержка — [support@srezai.ru](mailto:support@srezai.ru)

Лицензия — [MIT](LICENSE).
