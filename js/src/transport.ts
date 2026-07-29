import {
  ERROR_CLASSES,
  RateLimited,
  SrezAIError,
} from "./errors.js";

export const DEFAULT_BASE_URL = "https://srezai.ru";

/**
 * DeepResearch синхронный и занимает до двух минут: общий таймаут должен быть
 * заметно больше, иначе клиент оборвёт соединение раньше, чем сервер ответит,
 * и кредиты спишутся без результата.
 */
export const DEFAULT_TIMEOUT_MS = 180_000;

/**
 * Повторяем только то, что имеет смысл повторять: сбои апстрима и лимиты.
 * Ошибки запроса (400, 401) повторять бессмысленно — вернём сразу.
 */
const RETRY_CODES = new Set([
  "rate_limited",
  "service_unavailable",
  "search_unavailable",
  "upstream_timeout",
]);

export interface TransportOptions {
  apiKey?: string | undefined;
  baseUrl?: string;
  timeoutMs?: number;
  maxRetries?: number;
  fetch?: typeof globalThis.fetch;
}

const sleep = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

/** Пауза перед повтором: подсказка сервера в приоритете, иначе экспонента. */
export function backoff(attempt: number, retryAfterSec?: number): number {
  if (retryAfterSec !== undefined && retryAfterSec > 0) {
    return Math.min(retryAfterSec, 30) * 1000;
  }
  return Math.min(2 ** attempt, 8) * 1000;
}

/** Retry-After в секундах. Форму с датой не разбираем — API её не отдаёт. */
function headerSeconds(raw: string | null): number | undefined {
  if (!raw) return undefined;
  const n = Number.parseInt(raw.trim(), 10);
  return Number.isFinite(n) ? n : undefined;
}

function detail(payload: Record<string, unknown>, fallback: string): string {
  const err = payload["error"];
  return typeof err === "string" && err ? err : fallback;
}

/** Убирает ключи со значением undefined: сервер не должен видеть пустые поля. */
export function compact(
  body: Record<string, unknown>,
): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(body)) {
    if (v !== undefined) out[k] = v;
  }
  return out;
}

function raiseForPayload(
  status: number,
  payload: Record<string, unknown>,
  headerRetryAfter?: number,
): never {
  const rawCode = payload["code"];
  const code = typeof rawCode === "string" ? rawCode : undefined;
  const message = detail(payload, `HTTP ${status}`);
  const Cls = ERROR_CLASSES[code ?? ""] ?? SrezAIError;

  if (Cls === RateLimited) {
    // Поле называется retryAfterSec — так его отдаёт API и так оно описано в
    // документации. Заголовок Retry-After дублирует его и служит запасным
    // источником, если тело придёт без поля.
    const raw = payload["retryAfterSec"];
    const fromBody = typeof raw === "number" ? Math.trunc(raw) : undefined;
    throw new RateLimited(message, {
      code,
      status,
      retryAfter: fromBody ?? headerRetryAfter,
    });
  }

  throw new Cls(message, { code, status });
}

/** HTTP-транспорт с повторами по кодам из `RETRY_CODES`. */
export class Transport {
  readonly apiKey: string;
  readonly baseUrl: string;
  readonly timeoutMs: number;
  readonly maxRetries: number;
  private readonly fetchImpl: typeof globalThis.fetch;

  constructor(opts: TransportOptions = {}) {
    const key = opts.apiKey ?? process.env["SREZAI_API_KEY"];
    if (!key) {
      throw new Error(
        "Нужен API-ключ: передайте apiKey или задайте переменную окружения " +
          "SREZAI_API_KEY. Ключ создаётся в личном кабинете на " +
          "https://srezai.ru/dashboard.",
      );
    }
    this.apiKey = key;
    this.baseUrl = (opts.baseUrl ?? DEFAULT_BASE_URL).replace(/\/+$/, "");
    this.timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.maxRetries = Math.max(0, opts.maxRetries ?? 2);
    this.fetchImpl = opts.fetch ?? globalThis.fetch;
  }

  async post<T>(path: string, body: Record<string, unknown>): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const payload = JSON.stringify(compact(body));
    let last: unknown;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      let res: Response;
      try {
        res = await this.fetchImpl(url, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${this.apiKey}`,
            "Content-Type": "application/json",
          },
          body: payload,
          signal: AbortSignal.timeout(this.timeoutMs),
        });
      } catch (err) {
        // Сеть отвалилась или истёк таймаут: повторяем, пока есть попытки.
        last = err;
        if (attempt < this.maxRetries) {
          await sleep(backoff(attempt));
          continue;
        }
        const reason = err instanceof Error ? err.message : String(err);
        throw new SrezAIError(`Сетевая ошибка: ${reason}`);
      }

      let data: unknown;
      try {
        data = await res.json();
      } catch {
        throw new SrezAIError(
          `Ответ не является JSON (HTTP ${res.status}).`,
          { status: res.status },
        );
      }

      if (res.ok) return data as T;

      const map =
        data !== null && typeof data === "object"
          ? (data as Record<string, unknown>)
          : {};
      const rawCode = map["code"];
      const code = typeof rawCode === "string" ? rawCode : undefined;
      const headerHint = headerSeconds(res.headers.get("Retry-After"));

      if (code !== undefined && RETRY_CODES.has(code) && attempt < this.maxRetries) {
        const raw = map["retryAfterSec"];
        const hint = typeof raw === "number" ? Math.trunc(raw) : headerHint;
        await sleep(backoff(attempt, hint));
        continue;
      }

      raiseForPayload(res.status, map, headerHint);
    }

    // Недостижимо: цикл либо вернул результат, либо бросил исключение.
    throw last instanceof Error ? last : new SrezAIError("Запрос не выполнен.");
  }
}
