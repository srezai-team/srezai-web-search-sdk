import { Transport, type TransportOptions } from "./transport.js";
import type {
  AnswerSearchOptions,
  ExtractOptions,
  ImageSearchOptions,
  ReadOptions,
  SearchOptions,
} from "./types.js";

export type { TransportOptions as SrezAIOptions };

/**
 * Клиент поискового API срезAI.
 *
 * Ключ берётся из `apiKey`, а если его нет — из переменной окружения
 * `SREZAI_API_KEY`.
 *
 * ```ts
 * const client = new SrezAI();
 * const { results } = await client.search("новости про ИИ", { num: 5 });
 * ```
 */
export class SrezAI {
  private readonly t: Transport;

  constructor(opts: TransportOptions = {}) {
    this.t = new Transport(opts);
  }

  /** Веб-поиск. Возвращает `{ results, meta }`. */
  async search<T = Record<string, unknown>>(
    query: string,
    opts: SearchOptions = {},
  ): Promise<T> {
    return this.t.post<T>("/api/v1/search", { query, ...opts });
  }

  /** Поиск изображений: ссылки, источник и разрешение. Картинки не скачиваются. */
  async imageSearch<T = Record<string, unknown>>(
    query: string,
    opts: ImageSearchOptions = {},
  ): Promise<T> {
    return this.t.post<T>("/api/v1/media", { query, ...opts });
  }

  /** Страница → плотный markdown без навигации, рекламы и HTML. */
  async readUrl<T = Record<string, unknown>>(
    url: string,
    opts: ReadOptions = {},
  ): Promise<T> {
    return this.t.post<T>("/api/v1/read", { url, ...opts });
  }

  /**
   * До 5 страниц за один вызов; читаются параллельно.
   *
   * Если какая-то не открылась, остальные всё равно вернутся. На батче ставьте
   * `maxChars` скромнее: пять больших страниц вытеснят из контекста всё
   * остальное.
   */
  async readUrls<T = Record<string, unknown>>(
    urls: string[],
    opts: ReadOptions = {},
  ): Promise<T> {
    return this.t.post<T>("/api/v1/read", { urls, ...opts });
  }

  /**
   * Скриншот и markdown через реальный браузер.
   *
   * Нужен, когда важно увидеть страницу: раскладку, цвета, вёрстку. Если нужен
   * только текст — `readUrl` дешевле.
   */
  async fetchPage<T = Record<string, unknown>>(
    url: string,
    opts: { maxChars?: number } = {},
  ): Promise<T> {
    return this.t.post<T>("/api/v1/fetch", { url, ...opts });
  }

  /**
   * Данные строго по вашей схеме: только запрошенные поля, без текста страницы.
   *
   * Чего на странице нет, приходит как `null` — значения не выдумываются.
   * Схему можно задать сокращённо (`{ title: "string", price: "number?" }`)
   * или полным JSON Schema. Описания полей заметно повышают точность.
   *
   * Укажите ровно одно: `url` или `urls`.
   */
  async extract<T = Record<string, unknown>>(
    schema: Record<string, unknown>,
    opts: ExtractOptions = {},
  ): Promise<T> {
    const hasUrl = opts.url !== undefined;
    const hasUrls = opts.urls !== undefined;
    if (hasUrl === hasUrls) {
      throw new Error(
        "Укажите ровно одно: url для одной страницы или urls для нескольких.",
      );
    }
    return this.t.post<T>("/api/v1/extract", { schema, ...opts });
  }

  /**
   * Агентное исследование: ищет, читает источники, возвращает связный ответ.
   *
   * Занимает от 10 секунд до двух минут. Для быстрых фактов берите `search`.
   */
  async deepResearch<T = Record<string, unknown>>(query: string): Promise<T> {
    return this.t.post<T>("/api/v1/deep", { query });
  }

  /**
   * RAG-ответ по вебу с семантическим ранжированием источников.
   *
   * В отличие от `deepResearch`, цена фиксирована по `depth`, а не по объёму
   * ответа: fast — 50 кредитов, balanced — 100, deep — 200.
   */
  async answerSearch<T = Record<string, unknown>>(
    query: string,
    opts: AnswerSearchOptions = {},
  ): Promise<T> {
    return this.t.post<T>("/api/v1/answer", { query, ...opts });
  }
}
