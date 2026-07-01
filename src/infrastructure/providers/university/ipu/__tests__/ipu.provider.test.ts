// Using Jest-like structure for the foundation

import { InvalidCredentialsError, AuthenticationError, NetworkError } from "@/core/errors/provider.error";
import { IPUProvider } from "../ipu.provider";
import { IPUProviderConfig, IPUProviderState } from "../ipu.types";

const mockConfig: IPUProviderConfig = {
  baseUrl: "https://mock.ipu.ac.in",
  timeoutMs: 5000,
  retryPolicy: { maxRetries: 3, backoffMs: 1000 },
  userAgent: "CampusIQ-Bot",
  rateLimitSettings: { requestsPerMinute: 30 },
  featureFlags: { enableHtmlParsing: false, useMockData: true }
};

describe("IPUProvider", () => {
  let provider: IPUProvider;

  beforeEach(() => {
    provider = new IPUProvider(mockConfig);
  });

  describe("Initialization & Health", () => {
    it("should initialize with correct provider ID", () => {
      expect(provider.getProviderId()).toBe("IPU");
    });

    it("should perform health check successfully", async () => {
      const health = await provider.healthCheck();
      expect(health.isAvailable).toBe(true);
      expect(health.version).toBeDefined();
    });
  });

  describe("Authentication", () => {
    it("should validate valid enrollment numbers", () => {
      expect(provider.validateCredentialsFormat({ enrollmentNo: "12345678901" })).toBe(true);
    });

    it("should reject invalid enrollment numbers", () => {
      expect(provider.validateCredentialsFormat({ enrollmentNo: "123" })).toBe(false);
      expect(provider.validateCredentialsFormat({ enrollmentNo: "abcdefghijk" })).toBe(false);
    });

    it("should authenticate successfully with valid credentials", async () => {
      const result = await provider.authenticate({ enrollmentNo: "12345678901" });
      expect(result).toBe(true);
    });

    it("should throw AuthenticationError on invalid login", async () => {
      await expect(provider.authenticate({ enrollmentNo: "00000000000" })).rejects.toThrow(AuthenticationError);
    });
  });

  describe("Data Fetching", () => {
    const validCredentials = { enrollmentNo: "12345678901" };

    it("should fetch and map student profile", async () => {
      const profile = await provider.fetchStudentProfile(validCredentials);
      expect(profile.enrollmentNo).toBe("12345678901");
      expect(profile.name).toBe("John Doe");
      expect(profile.batchYear).toBe(2022);
    });

    it("should fetch and map all semester results", async () => {
      const results = await provider.fetchSemesterResults(validCredentials);
      expect(results.length).toBeGreaterThan(0);
      expect(results[0].termNumber).toBe(1);
      expect(results[0].courses.length).toBeGreaterThan(0);
    });

    it("should fetch the latest result correctly", async () => {
      const latest = await provider.fetchLatestResult(validCredentials);
      expect(latest).not.toBeNull();
      expect(latest!.termNumber).toBe(2); // Mock data returns semester 2 as latest
    });

    it("should detect updates correctly", async () => {
      // Last known term is 1, latest is 2, so it should be true
      const hasUpdates = await provider.checkForUpdates(validCredentials, 1);
      expect(hasUpdates).toBe(true);
      
      // Last known term is 2, latest is 2, so it should be false
      const hasUpdatesFalse = await provider.checkForUpdates(validCredentials, 2);
      expect(hasUpdatesFalse).toBe(false);
    });
  });

  describe("Error Handling", () => {
    it("should throw NetworkError if useMockData is false and scraping is not implemented", async () => {
      const prodProvider = new IPUProvider({
        ...mockConfig,
        featureFlags: { enableHtmlParsing: true, useMockData: false }
      });
      
      await expect(prodProvider.fetchStudentProfile({ enrollmentNo: "12345678901" })).rejects.toThrow(NetworkError);
    });
  });
});
