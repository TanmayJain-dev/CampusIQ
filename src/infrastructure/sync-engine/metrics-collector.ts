import { SyncMetrics } from "./sync.types";

export class MetricsCollector {
  private totalSyncTime = 0;
  private totalSyncs = 0;
  private failures = 0;
  private retries = 0;
  private parserErrors = 0;

  recordSync(durationMs: number, success: boolean) {
    this.totalSyncTime += durationMs;
    this.totalSyncs++;
    if (!success) this.failures++;
  }

  recordRetry() {
    this.retries++;
  }

  recordParserError() {
    this.parserErrors++;
  }

  getMetrics(): SyncMetrics {
    return {
      averageSyncTimeMs: this.totalSyncs > 0 ? this.totalSyncTime / this.totalSyncs : 0,
      failureRate: this.totalSyncs > 0 ? this.failures / this.totalSyncs : 0,
      retryCount: this.retries,
      portalAvailability: 1.0 - (this.totalSyncs > 0 ? this.failures / this.totalSyncs : 0),
      parserErrors: this.parserErrors
    };
  }
}
