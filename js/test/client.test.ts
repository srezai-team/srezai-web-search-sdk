/** Проверяем то, что легко сломать незаметно: разбор ошибок, повторы, тело запроса. */

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  BadRequest,
  HostUnresolved,
  RateLimited,
  SrezAI,
  SrezAIError,
  SsrfBlocked,
  Unauthorized,
} from "../src/index.js";
import { withServer } from "./server.js";

const KEY = "srz_live_test";

test("ключ берётся из окружения", () => {
  process.env["SREZAI_API_KEY"] = "srz_live_from_env";
  try {
    assert.doesNotThrow(() => new SrezAI());
  } finally {
    delete process.env["SREZAI_API_KEY"];
  }
});

test("без ключа объясняет, где его взять", () => {
  const saved = process.env["SREZAI_API_KEY"];
  delete process.env["SREZAI_API_KEY"];
  try {
    assert.throws(() => new SrezAI(), /SREZAI_API_KEY/);
  } finally {
    if (saved !== undefined) process.env["SREZAI_API_KEY"] = saved;
  }
});

test("шлёт Bearer и не отправляет пустые поля", async () => {
  await withServer([{ json: { results: [] } }], async (baseUrl, captured) => {
    const client = new SrezAI({ apiKey: KEY, baseUrl, maxRetries: 0 });
    await client.search("тест", { num: 3 });

    const req = captured[0];
    assert.equal(req?.auth, `Bearer ${KEY}`);
    assert.equal(req?.path, "/api/v1/search");
    assert.deepEqual(req?.body, { query: "тест", num: 3 });
    assert.ok(!("category" in (req?.body ?? {})));
  });
});

test("camelCase уходит на сервер как есть", async () => {
  await withServer([{ json: {} }], async (baseUrl, captured) => {
    const client = new SrezAI({ apiKey: KEY, baseUrl, maxRetries: 0 });
    await client.search("тест", {
      timeRange: "week",
      includeDomains: ["habr.com"],
    });
    assert.deepEqual(captured[0]?.body, {
      query: "тест",
      timeRange: "week",
      includeDomains: ["habr.com"],
    });
  });
});

const CASES: Array<[string, number, new (...a: never[]) => Error]> = [
  ["unauthorized", 401, Unauthorized],
  ["ssrf_blocked", 400, SsrfBlocked],
  ["host_unresolved", 400, HostUnresolved],
];

for (const [code, status, Cls] of CASES) {
  test(`код ${code} превращается в ${Cls.name}`, async () => {
    await withServer(
      [{ status, json: { code, error: "текст" } }],
      async (baseUrl) => {
        const client = new SrezAI({ apiKey: KEY, baseUrl, maxRetries: 0 });
        await assert.rejects(() => client.search("тест"), Cls);
      },
    );
  });
}

test("host_unresolved — это не ssrf_blocked", async () => {
  await withServer(
    [{ status: 400, json: { code: "host_unresolved", error: "нет домена" } }],
    async (baseUrl) => {
      const client = new SrezAI({ apiKey: KEY, baseUrl, maxRetries: 0 });
      await assert.rejects(
        () => client.readUrl("https://exmaple.com"),
        (err: unknown) => err instanceof HostUnresolved && !(err instanceof SsrfBlocked),
      );
    },
  );
});

test("неизвестный код не ломает клиент", async () => {
  await withServer(
    [{ status: 418, json: { code: "brand_new", error: "?" } }],
    async (baseUrl) => {
      const client = new SrezAI({ apiKey: KEY, baseUrl, maxRetries: 0 });
      await assert.rejects(
        () => client.search("тест"),
        (err: unknown) => err instanceof SrezAIError && err.code === "brand_new",
      );
    },
  );
});

test("retryAfterSec доходит до вызывающего", async () => {
  await withServer(
    [{ status: 429, json: { code: "rate_limited", error: "лимит", retryAfterSec: 7 } }],
    async (baseUrl) => {
      const client = new SrezAI({ apiKey: KEY, baseUrl, maxRetries: 0 });
      await assert.rejects(
        () => client.search("тест"),
        (err: unknown) => err instanceof RateLimited && err.retryAfter === 7,
      );
    },
  );
});

test("без поля в теле берётся заголовок Retry-After", async () => {
  await withServer(
    [
      {
        status: 429,
        json: { code: "rate_limited", error: "лимит" },
        headers: { "Retry-After": "11" },
      },
    ],
    async (baseUrl) => {
      const client = new SrezAI({ apiKey: KEY, baseUrl, maxRetries: 0 });
      await assert.rejects(
        () => client.search("тест"),
        (err: unknown) => err instanceof RateLimited && err.retryAfter === 11,
      );
    },
  );
});

test("сбой апстрима повторяется и запрос проходит", async () => {
  await withServer(
    [
      { status: 503, json: { code: "service_unavailable", error: "сбой" } },
      { json: { results: [{ title: "ок" }] } },
    ],
    async (baseUrl, captured) => {
      const client = new SrezAI({ apiKey: KEY, baseUrl, maxRetries: 1 });
      const res = await client.search<{ results: Array<{ title: string }> }>("тест");
      assert.equal(res.results[0]?.title, "ок");
      assert.equal(captured.length, 2);
    },
  );
});

test("ошибку запроса не повторяем: это трата денег и времени", async () => {
  await withServer(
    [{ status: 400, json: { code: "bad_request", error: "не то" } }],
    async (baseUrl, captured) => {
      const client = new SrezAI({ apiKey: KEY, baseUrl, maxRetries: 3 });
      await assert.rejects(() => client.search("тест"), BadRequest);
      assert.equal(captured.length, 1);
    },
  );
});

test("extract требует ровно одну цель", async () => {
  const client = new SrezAI({ apiKey: KEY, maxRetries: 0 });
  await assert.rejects(
    () => client.extract({ t: "string" }, { url: "https://a.com", urls: ["https://b.com"] }),
    /ровно одно/,
  );
  await assert.rejects(() => client.extract({ t: "string" }), /ровно одно/);
});

test("answerSearch шлёт query и depth на /api/v1/answer", async () => {
  await withServer(
    [{ json: { answer: "ответ", sources: [], confidence: 0.9 } }],
    async (baseUrl, captured) => {
      const client = new SrezAI({ apiKey: KEY, baseUrl, maxRetries: 0 });
      const res = await client.answerSearch<{ answer: string }>("вопрос", { depth: "fast" });
      assert.equal(res.answer, "ответ");
      assert.equal(captured[0]?.path, "/api/v1/answer");
      assert.deepEqual(captured[0]?.body, { query: "вопрос", depth: "fast" });
    },
  );
});

test("transcript: один ролик уходит массивом, поля — как есть", async () => {
  await withServer([{ json: { results: [{ videoId: "dQw4w9WgXcQ" }], errors: [] } }], async (baseUrl, captured) => {
    const client = new SrezAI({ apiKey: KEY, baseUrl, maxRetries: 0 });
    const res = await client.transcript("https://youtu.be/dQw4w9WgXcQ", {
      languages: ["ru", "en"],
      maxChars: 8000,
    });

    assert.equal(captured[0]?.path, "/api/v1/transcript");
    assert.deepEqual(captured[0]?.body, {
      videos: ["https://youtu.be/dQw4w9WgXcQ"],
      languages: ["ru", "en"],
      maxChars: 8000,
    });
    assert.ok(!("from" in (captured[0]?.body ?? {})), "не заданное окно не отправляется");
    assert.deepEqual((res as { results: unknown[] }).results, [{ videoId: "dQw4w9WgXcQ" }]);
  });
});
