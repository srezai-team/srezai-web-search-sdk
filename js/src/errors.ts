/**
 * Коды ошибок API и классы под каждый из них.
 *
 * Код в теле ответа — машинный: по нему решают, что делать дальше, не разбирая
 * человеческий текст. Отдельные классы нужны, чтобы вызывающий писал
 * `catch (e) { if (e instanceof HostUnresolved) ... }` вместо сравнения строк.
 */

export class SrezAIError extends Error {
  readonly code: string | undefined;
  readonly status: number | undefined;

  constructor(
    message: string,
    opts: { code?: string | undefined; status?: number | undefined } = {},
  ) {
    super(opts.code ? `[${opts.code}] ${message}` : message);
    this.name = new.target.name;
    this.code = opts.code;
    this.status = opts.status;
  }
}

/** Ключа нет, он отозван или не начинается с srz_live_. */
export class Unauthorized extends SrezAIError {}

/** Сработал лимит. `retryAfter` — секунды до следующей попытки, если сервер их назвал. */
export class RateLimited extends SrezAIError {
  readonly retryAfter: number | undefined;

  constructor(
    message: string,
    opts: {
      code?: string | undefined;
      status?: number | undefined;
      retryAfter?: number | undefined;
    } = {},
  ) {
    super(message, opts);
    this.retryAfter = opts.retryAfter;
  }
}

/** Запрос не прошёл проверку: не хватает поля, значение вне диапазона. */
export class BadRequest extends SrezAIError {}

/** Схема для extract составлена неверно. */
export class SchemaInvalid extends BadRequest {}

/** Адрес запрашивать нельзя: локальная сеть, служебный диапазон, чужой порт. */
export class SsrfBlocked extends SrezAIError {}

/** Имя хоста не разрешается: домена нет или молчит DNS. Это не запрет — опечатка. */
export class HostUnresolved extends SrezAIError {}

/** Страницу открыть не удалось: сайт ответил ошибкой, отдал пустоту или закрылся. */
export class ReadFailed extends SrezAIError {}

/** Страница прочитана, но данные по схеме из неё не извлеклись. */
export class ExtractFailed extends SrezAIError {}

/** Поиск временно недоступен. */
export class SearchUnavailable extends SrezAIError {}

/** Внешний сервис не ответил за отведённое время. */
export class UpstreamTimeout extends SrezAIError {}

/** Сервис временно недоступен. */
export class ServiceUnavailable extends SrezAIError {}

/**
 * Соответствие кодов классам.
 *
 * `empty_result` намеренно ведёт на базовый класс: это не поломка, а честный
 * ответ «ничего не нашлось», и заводить под него отдельный тип незачем.
 * Неизвестный код тоже даёт базовый класс — новый код на сервере не должен
 * ломать старый клиент.
 */
export const ERROR_CLASSES: Record<string, typeof SrezAIError> = {
  unauthorized: Unauthorized,
  rate_limited: RateLimited,
  bad_request: BadRequest,
  schema_invalid: SchemaInvalid,
  method_not_allowed: BadRequest,
  ssrf_blocked: SsrfBlocked,
  host_unresolved: HostUnresolved,
  read_failed: ReadFailed,
  extract_failed: ExtractFailed,
  search_unavailable: SearchUnavailable,
  upstream_timeout: UpstreamTimeout,
  service_unavailable: ServiceUnavailable,
  empty_result: SrezAIError,
};
