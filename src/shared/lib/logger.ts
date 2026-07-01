import pino from "pino";
import { env } from "@/env.mjs";

/**
 * Singleton JSON logger for the application.
 * Uses pino-pretty in development for readable console output.
 */
export const logger = pino({
  level: env.NODE_ENV === "development" ? "debug" : "info",
  transport:
    env.NODE_ENV === "development"
      ? {
          target: "pino-pretty",
          options: {
            colorize: true,
            ignore: "pid,hostname",
          },
        }
      : undefined,
});
