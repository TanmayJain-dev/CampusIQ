import { StudentProfile, SemesterResult } from "@/core/entities/academic.entity";
import { ProviderCredentials } from "@/core/interfaces/university-provider.interface";

export interface SyncConfig {
  portalUrl: string;
  timeoutMs: number;
  userAgent: string;
  retryPolicy: {
    type: 'EXPONENTIAL' | 'FIXED' | 'IMMEDIATE';
    maxRetries: number;
    baseDelayMs: number;
  };
  rateLimits: {
    requestsPerMinute: number;
  };
  headers?: Record<string, string>;
  featureFlags: {
    useMockData: boolean;
  };
}

export interface AcademicSyncData {
  profile: StudentProfile | null;
  results: SemesterResult[];
}

export interface SyncResult<T> {
  success: boolean;
  durationMs: number;
  recordsSynced: number;
  portalVersion: string;
  warnings: string[];
  errors: Error[];
  data: T | null;
  metadata?: Record<string, any>;
}

export interface SyncMetrics {
  averageSyncTimeMs: number;
  failureRate: number;
  retryCount: number;
  portalAvailability: number;
  parserErrors: number;
}
