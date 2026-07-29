import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";

export interface Captured {
  path: string;
  auth: string | undefined;
  body: Record<string, unknown>;
}

export interface Reply {
  status?: number;
  json: unknown;
  headers?: Record<string, string>;
}

/**
 * Поднимает настоящий HTTP-сервер и отдаёт заготовленные ответы по очереди.
 *
 * Мок-библиотека здесь была бы лишней зависимостью: нам нужно проверить, что
 * клиент действительно шлёт по сети, а не что он вызвал подменённую функцию.
 */
export async function withServer(
  replies: Reply[],
  run: (baseUrl: string, captured: Captured[]) => Promise<void>,
): Promise<void> {
  const captured: Captured[] = [];
  let i = 0;

  const server: Server = createServer((req, res) => {
    const chunks: Buffer[] = [];
    req.on("data", (c: Buffer) => chunks.push(c));
    req.on("end", () => {
      const raw = Buffer.concat(chunks).toString("utf8");
      captured.push({
        path: req.url ?? "",
        auth: req.headers.authorization,
        body: raw ? (JSON.parse(raw) as Record<string, unknown>) : {},
      });
      const reply = replies[Math.min(i, replies.length - 1)];
      i++;
      res.writeHead(reply?.status ?? 200, {
        "Content-Type": "application/json",
        ...(reply?.headers ?? {}),
      });
      res.end(JSON.stringify(reply?.json ?? {}));
    });
  });

  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address() as AddressInfo;
  try {
    await run(`http://127.0.0.1:${port}`, captured);
  } finally {
    await new Promise<void>((resolve, reject) =>
      server.close((err) => (err ? reject(err) : resolve())),
    );
  }
}
