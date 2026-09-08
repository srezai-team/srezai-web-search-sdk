/** Общие типы параметров. Держим их узкими: опечатка ловится на этапе сборки. */

export type Category = "general" | "news" | "it" | "science";
export type Language = "auto" | "ru" | "en";
export type TimeRange = "" | "day" | "week" | "month" | "year";
export type Depth = "flash" | "auto";

/** Глубина answerSearch: не путать с Depth у search — другая шкала. */
export type AnswerDepth = "fast" | "balanced" | "deep";

/**
 * Как забирать страницу.
 *
 * `auto` начинает с быстрого способа и сам поднимается, если текста не
 * оказалось. Указывать явно стоит только если вы знаете сайт.
 */
export type Engine = "auto" | "fast" | "dynamic" | "stealth";

export interface SearchOptions {
  /** Сколько результатов (1–30). Просите столько, сколько обработаете. */
  num?: number;
  category?: Category;
  language?: Language;
  timeRange?: TimeRange;
  /** `flash` — быстрее и уже, для одного факта; `auto` — больше движков. */
  depth?: Depth;
  /** Подтянуть текст топ-страниц: медленнее, зато не нужен отдельный readUrl. */
  excerpts?: boolean;
  /** Искать только на этих сайтах, вместе с поддоменами (до 10). */
  includeDomains?: string[];
  /** Исключить эти сайты и их поддомены (до 10). */
  excludeDomains?: string[];
  engines?: string[];
  safesearch?: number;
  pageno?: number;
}

export interface ImageSearchOptions {
  num?: number;
  safe?: boolean;
  timeRange?: TimeRange;
}

export interface ReadOptions {
  /** Сколько символов вернуть (200–50000). Поднимайте, если нужен весь текст. */
  maxChars?: number;
  engine?: Engine;
}

export interface AnswerSearchOptions {
  /** fast — 2 страницы, balanced (по умолчанию) — 5, deep — 10. Цена тарифа фиксирована по depth, не зависит от объёма ответа. */
  depth?: AnswerDepth;
  language?: Language;
}

export interface ExtractOptions {
  /** Одна страница. Взаимоисключимо с `urls`. */
  url?: string;
  /** До 5 страниц под одну схему. Каждая тарифицируется отдельно. */
  urls?: string[];
  /** Уточнение для разбора, если из схемы неочевидно. */
  instruction?: string;
  engine?: Engine;
}
