export { SrezAI, type SrezAIOptions } from "./client.js";
export {
  BadRequest,
  ERROR_CLASSES,
  ExtractFailed,
  HostUnresolved,
  RateLimited,
  ReadFailed,
  SchemaInvalid,
  SearchUnavailable,
  ServiceUnavailable,
  SrezAIError,
  SsrfBlocked,
  Unauthorized,
  UpstreamTimeout,
} from "./errors.js";
export { DEFAULT_BASE_URL, DEFAULT_TIMEOUT_MS } from "./transport.js";
export type {
  AnswerDepth,
  AnswerSearchOptions,
  Category,
  Depth,
  Engine,
  ExtractOptions,
  ImageSearchOptions,
  Language,
  ReadOptions,
  SearchOptions,
  TimeRange,
  TranscriptOptions,
} from "./types.js";
