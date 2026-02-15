/**
 * Lightweight structured logger for the frontend.
 *
 * Wraps `console.*` with a consistent format:
 *   [HH:MM:SS.mmm] LEVEL  module | message  {context}
 *
 * Log level is controlled by the `VITE_LOG_LEVEL` env var
 * (default: "debug" in dev, "warn" in production).
 *
 * Usage:
 *   import { logger } from "../logger";
 *   const log = logger("api");
 *   log.info("Login succeeded", { userId: "abc" });
 *   log.error("Request failed", { status: 500, url: "/chat" });
 */

type LogLevel = "debug" | "info" | "warn" | "error";

const LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

function getMinLevel(): number {
  const env = import.meta.env.VITE_LOG_LEVEL as string | undefined;
  if (env && env in LEVELS) return LEVELS[env as LogLevel];
  return import.meta.env.DEV ? LEVELS.debug : LEVELS.warn;
}

const MIN_LEVEL = getMinLevel();

function timestamp(): string {
  const d = new Date();
  const h = String(d.getHours()).padStart(2, "0");
  const m = String(d.getMinutes()).padStart(2, "0");
  const s = String(d.getSeconds()).padStart(2, "0");
  const ms = String(d.getMilliseconds()).padStart(3, "0");
  return `${h}:${m}:${s}.${ms}`;
}

function format(level: string, module: string, message: string): string {
  return `[${timestamp()}] ${level.toUpperCase().padEnd(5)} ${module} | ${message}`;
}

export interface Logger {
  debug: (message: string, context?: Record<string, unknown>) => void;
  info: (message: string, context?: Record<string, unknown>) => void;
  warn: (message: string, context?: Record<string, unknown>) => void;
  error: (message: string, context?: Record<string, unknown>) => void;
}

/**
 * Create a namespaced logger for a module.
 *
 * @param module Short name like "api", "auth", "chat"
 */
export function logger(module: string): Logger {
  const make =
    (level: LogLevel, fn: (...args: unknown[]) => void) =>
    (message: string, context?: Record<string, unknown>) => {
      if (LEVELS[level] < MIN_LEVEL) return;
      if (context) {
        fn(format(level, module, message), context);
      } else {
        fn(format(level, module, message));
      }
    };

  return {
    debug: make("debug", console.debug),
    info: make("info", console.info),
    warn: make("warn", console.warn),
    error: make("error", console.error),
  };
}
