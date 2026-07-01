import { ProviderError, NetworkError, RateLimitError } from "@/core/errors/provider.error";
import { ProviderCredentials } from "@/core/interfaces/university-provider.interface";
import { MetricsCollector } from "@/infrastructure/sync-engine/metrics-collector";
import { RetryStrategy } from "@/infrastructure/sync-engine/retry-strategy";
import { SyncConfig, SyncResult, AcademicSyncData } from "@/infrastructure/sync-engine/sync.types";
import { logger } from "@/shared/lib/logger";
import { IPUMapper } from "../ipu-mapper";
import { IPUCaptchaDetector } from "./ipu-captcha-detector";
import { IPUParsers } from "./ipu-parsers";
import { IPUPortalClient } from "./ipu-portal-client";
import { IPUSessionManager, IPUSessionContext } from "./ipu-session-manager";
import { IPUVersionDetector } from "./ipu-version-detector";

/**
 * IPU Academic Synchronization Engine.
 * Responsible for securely orchestrating the retrieval of academic data,
 * handling retries, session recovery, and returning normalized models.
 */
export class IPUSyncEngine {
  private readonly client: IPUPortalClient;
  private readonly sessionManager: IPUSessionManager;
  private readonly metrics = new MetricsCollector();

  constructor(private readonly config: SyncConfig) {
    this.client = new IPUPortalClient(this.config);
    this.sessionManager = new IPUSessionManager(this.client);
    logger.info("IPUSyncEngine: Initialized");
  }

  private isRetryableError(error: any): boolean {
    if (error instanceof NetworkError) return true;
    if (error instanceof RateLimitError) return true;
    // Do not retry AuthenticationError or CaptchaRequiredError
    return false;
  }

  async executeSync(credentials: ProviderCredentials): Promise<SyncResult<AcademicSyncData>> {
    const startTime = Date.now();
    logger.info({ enrollmentNo: credentials.enrollmentNo }, "IPUSyncEngine: Starting synchronization");
    
    let session: IPUSessionContext | null = null;
    let portalVersion = "unknown";
    
    try {
      // 1. Session Management & Auth (Wrapped in Retry Strategy)
      session = await RetryStrategy.execute(
        async () => {
          return await this.sessionManager.createSession(credentials);
        },
        this.config.retryPolicy,
        this.isRetryableError.bind(this)
      );

      // 2. Fetch & Parse Profile
      const profileHtml = await RetryStrategy.execute(
        () => this.client.get("/api/profile"),
        this.config.retryPolicy,
        this.isRetryableError.bind(this)
      );
      
      IPUCaptchaDetector.detect(profileHtml);
      portalVersion = IPUVersionDetector.detect(profileHtml);
      
      const rawProfile = IPUParsers.parseStudentProfile(profileHtml, credentials.enrollmentNo);
      const profile = IPUMapper.toStudentProfile(rawProfile);

      // 3. Fetch & Parse Results
      const resultsHtml = await RetryStrategy.execute(
        () => this.client.get("/api/results"),
        this.config.retryPolicy,
        this.isRetryableError.bind(this)
      );
      
      IPUCaptchaDetector.detect(resultsHtml);
      const rawResults = IPUParsers.parseSemesterResults(resultsHtml);
      const results = rawResults.map(r => IPUMapper.toSemesterResult(r));

      // 4. Cleanup
      await this.sessionManager.destroySession(session);

      const durationMs = Date.now() - startTime;
      this.metrics.recordSync(durationMs, true);

      logger.info({ enrollmentNo: credentials.enrollmentNo, durationMs }, "IPUSyncEngine: Synchronization complete");

      return {
        success: true,
        durationMs,
        recordsSynced: results.length,
        portalVersion,
        warnings: [],
        errors: [],
        data: { profile, results }
      };

    } catch (error: any) {
      const durationMs = Date.now() - startTime;
      this.metrics.recordSync(durationMs, false);
      if (error.name === "ParsingError") this.metrics.recordParserError();

      logger.error({ 
        enrollmentNo: credentials.enrollmentNo, 
        durationMs, 
        error: error.message 
      }, "IPUSyncEngine: Synchronization failed");

      if (session) {
        try {
          await this.sessionManager.destroySession(session);
        } catch (e) {
          // Ignore cleanup errors
        }
      }

      return {
        success: false,
        durationMs,
        recordsSynced: 0,
        portalVersion,
        warnings: [],
        errors: [error instanceof Error ? error : new Error(String(error))],
        data: null
      };
    }
  }

  getMetrics() {
    return this.metrics.getMetrics();
  }
}
