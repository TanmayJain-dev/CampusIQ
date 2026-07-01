import { logger } from "@/shared/lib/logger";

export class RateLimiter {
  private lastRequestTime = 0;
  
  constructor(private readonly requestsPerMinute: number) {}
  
  async enforce(): Promise<void> {
    const minIntervalMs = 60000 / this.requestsPerMinute;
    const now = Date.now();
    const timeSinceLastRequest = now - this.lastRequestTime;
    
    if (timeSinceLastRequest < minIntervalMs) {
      const delay = minIntervalMs - timeSinceLastRequest;
      logger.debug({ delayMs: Math.round(delay) }, "RateLimiter: Delaying request to respect rate limit.");
      await new Promise(resolve => setTimeout(resolve, delay));
    }
    
    this.lastRequestTime = Date.now();
  }
}
