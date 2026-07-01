import { NetworkError } from "@/core/errors/provider.error";
import { IPortalClient } from "@/infrastructure/sync-engine/portal-client.interface";
import { RateLimiter } from "@/infrastructure/sync-engine/rate-limiter";
import { SyncConfig } from "@/infrastructure/sync-engine/sync.types";
import { logger } from "@/shared/lib/logger";

/**
 * IPU specific HTTP client abstraction.
 * Currently uses mock responses based on feature flags.
 * Later, this will be swapped for Axios/Fetch without modifying parsing/sync logic.
 */
export class IPUPortalClient implements IPortalClient {
  private rateLimiter: RateLimiter;
  private headers: Record<string, string> = {};

  constructor(private readonly config: SyncConfig) {
    this.rateLimiter = new RateLimiter(config.rateLimits.requestsPerMinute);
    this.setHeaders(config.headers || {});
  }

  setHeaders(headers: Record<string, string>): void {
    this.headers = { ...this.headers, ...headers, 'User-Agent': this.config.userAgent };
  }

  async get(path: string, options?: Record<string, any>): Promise<string> {
    await this.rateLimiter.enforce();
    logger.debug({ path }, "IPUPortalClient: Executing GET");

    if (!this.config.featureFlags.useMockData) {
      throw new NetworkError("IPU", "Real scraping not implemented yet. Enable useMockData.");
    }

    return this.mockResponseForPath(path);
  }

  async post(path: string, data?: Record<string, any>, options?: Record<string, any>): Promise<string> {
    await this.rateLimiter.enforce();
    logger.debug({ path, dataKeys: data ? Object.keys(data) : [] }, "IPUPortalClient: Executing POST");

    if (!this.config.featureFlags.useMockData) {
      throw new NetworkError("IPU", "Real scraping not implemented yet. Enable useMockData.");
    }

    return this.mockResponseForPath(path, data);
  }

  private async mockResponseForPath(path: string, data?: any): Promise<string> {
    // Simulate network latency
    await new Promise(resolve => setTimeout(resolve, 150));
    
    if (path.includes("login")) {
      if (data?.enrollmentNo === "00000000000") return "<html>Invalid Credentials</html>";
      return "<html>Dashboard Logged In v1.0</html>";
    }
    
    if (path.includes("profile")) {
      return "<html>Profile: John Doe | 12345678901 | B.Tech CSE | 2022</html>";
    }

    if (path.includes("results")) {
      return "<html>Results Table Data</html>";
    }

    return "<html>Default Page</html>";
  }
}
