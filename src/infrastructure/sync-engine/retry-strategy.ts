import { logger } from "@/shared/lib/logger";
import { SyncConfig } from "./sync.types";

export class RetryStrategy {
  static async execute<T>(
    operation: () => Promise<T>,
    policy: SyncConfig['retryPolicy'],
    isRetryable: (error: any) => boolean
  ): Promise<T> {
    let attempt = 0;
    while (true) {
      try {
        return await operation();
      } catch (error) {
        if (attempt >= policy.maxRetries || !isRetryable(error)) {
          throw error;
        }
        
        attempt++;
        const delayMs = policy.type === 'EXPONENTIAL' 
          ? policy.baseDelayMs * Math.pow(2, attempt - 1)
          : policy.type === 'FIXED' 
            ? policy.baseDelayMs 
            : 0;

        logger.warn({ attempt, maxRetries: policy.maxRetries, delayMs, error: error instanceof Error ? error.message : "Unknown" }, "Operation failed. Retrying...");
        await new Promise(resolve => setTimeout(resolve, delayMs));
      }
    }
  }
}
