import { SyncConfig } from "@/infrastructure/sync-engine/sync.types";
import { IPUSyncEngine } from "../ipu-sync-engine";

const mockConfig: SyncConfig = {
  portalUrl: "https://mock.ipu.ac.in",
  timeoutMs: 5000,
  userAgent: "CampusIQ-Bot",
  retryPolicy: { type: 'IMMEDIATE', maxRetries: 1, baseDelayMs: 0 },
  rateLimits: { requestsPerMinute: 60 },
  featureFlags: { useMockData: true }
};

describe("IPUSyncEngine", () => {
  let engine: IPUSyncEngine;

  beforeEach(() => {
    engine = new IPUSyncEngine(mockConfig);
  });

  it("should execute successful sync with valid credentials", async () => {
    const result = await engine.executeSync({ enrollmentNo: "12345678901", password: "password123" });
    
    expect(result.success).toBe(true);
    expect(result.portalVersion).toBe("v1.0");
    expect(result.data).toBeDefined();
    expect(result.data?.profile?.name).toBe("John Doe");
    expect(result.data?.results.length).toBeGreaterThan(0);
  });

  it("should fail sync with invalid credentials and record failure metrics", async () => {
    const result = await engine.executeSync({ enrollmentNo: "00000000000", password: "wrong" });
    
    expect(result.success).toBe(false);
    expect(result.errors.length).toBeGreaterThan(0);
    expect(result.errors[0].message).toContain("Invalid credentials");
    
    const metrics = engine.getMetrics();
    expect(metrics.failureRate).toBe(1);
  });
});
