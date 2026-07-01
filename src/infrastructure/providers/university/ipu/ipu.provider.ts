import { StudentProfile, SemesterResult, ProviderStatus } from "@/core/entities/academic.entity";
import { InvalidCredentialsError, AuthenticationError } from "@/core/errors/provider.error";
import { IUniversityProvider, ProviderCredentials } from "@/core/interfaces/university-provider.interface";
import { logger } from "@/shared/lib/logger";
import { IPUMapper } from "./ipu-mapper";
import { IPURequestService } from "./ipu-request.service";
import { IPUProviderConfig, IPUProviderState } from "./ipu.types";

export class IPUProvider implements IUniversityProvider {
  private readonly providerId = "IPU";
  private state: IPUProviderState = IPUProviderState.UNINITIALIZED;
  private readonly requestService: IPURequestService;
  private lastSuccessfulSync?: Date;

  constructor(private readonly config: IPUProviderConfig) {
    this.requestService = new IPURequestService(this.config);
    this.state = IPUProviderState.READY;
    logger.info({ providerId: this.providerId }, "IPU Provider initialized");
  }

  getProviderId(): string {
    return this.providerId;
  }

  validateCredentialsFormat(credentials: ProviderCredentials): boolean {
    if (!credentials.enrollmentNo) return false;
    // IPU enrollment numbers are typically 11 digits
    return /^\d{11}$/.test(credentials.enrollmentNo);
  }

  async healthCheck(): Promise<ProviderStatus> {
    logger.debug({ providerId: this.providerId }, "Performing health check");
    return {
      isAvailable: this.state !== IPUProviderState.FAILED && this.state !== IPUProviderState.LOCKED,
      latencyMs: 150, // Mock response time
      lastChecked: new Date(),
      version: "1.0.0",
      lastSuccessfulSync: this.lastSuccessfulSync,
      message: `Provider state is ${this.state}`,
    };
  }

  async authenticate(credentials: ProviderCredentials): Promise<boolean> {
    logger.debug({ providerId: this.providerId, enrollmentNo: credentials.enrollmentNo }, "Authenticating");
    
    if (!this.validateCredentialsFormat(credentials)) {
      throw new InvalidCredentialsError(this.providerId, "Invalid enrollment number format for IPU");
    }

    const success = await this.requestService.login(credentials.enrollmentNo, credentials.password);
    if (!success) {
      this.state = IPUProviderState.READY;
      throw new AuthenticationError(this.providerId, "Invalid credentials provided to IPU portal.");
    }
    
    this.state = IPUProviderState.AUTHENTICATED;
    return true;
  }

  async fetchStudentProfile(credentials: ProviderCredentials): Promise<StudentProfile> {
    logger.info({ providerId: this.providerId, enrollmentNo: credentials.enrollmentNo }, "Fetching student profile");
    
    if (this.state !== IPUProviderState.AUTHENTICATED) {
      await this.authenticate(credentials);
    }
    
    this.state = IPUProviderState.SYNCING;
    const rawProfile = await this.requestService.fetchRawProfile(credentials.enrollmentNo);
    const mappedProfile = IPUMapper.toStudentProfile(rawProfile);
    
    this.state = IPUProviderState.AUTHENTICATED;
    return mappedProfile;
  }

  async fetchSemesterResults(credentials: ProviderCredentials): Promise<SemesterResult[]> {
    logger.info({ providerId: this.providerId, enrollmentNo: credentials.enrollmentNo }, "Fetching all semester results");
    
    if (this.state !== IPUProviderState.AUTHENTICATED) {
      await this.authenticate(credentials);
    }

    this.state = IPUProviderState.SYNCING;
    const rawResults = await this.requestService.fetchRawResults(credentials.enrollmentNo);
    const mappedResults = rawResults.map(raw => IPUMapper.toSemesterResult(raw));
    
    this.state = IPUProviderState.AUTHENTICATED;
    this.lastSuccessfulSync = new Date();
    return mappedResults;
  }

  async fetchLatestResult(credentials: ProviderCredentials): Promise<SemesterResult | null> {
    logger.info({ providerId: this.providerId, enrollmentNo: credentials.enrollmentNo }, "Fetching latest result");
    const results = await this.fetchSemesterResults(credentials);
    
    if (results.length === 0) return null;
    
    // Sort by termNumber to ensure we get the latest
    results.sort((a, b) => a.termNumber - b.termNumber);
    return results[results.length - 1];
  }

  async checkForUpdates(credentials: ProviderCredentials, lastKnownTerm: number): Promise<boolean> {
    logger.debug({ providerId: this.providerId, enrollmentNo: credentials.enrollmentNo }, "Checking for updates");
    const latestResult = await this.fetchLatestResult(credentials);
    if (!latestResult) return false;
    
    return latestResult.termNumber > lastKnownTerm;
  }

  async logout(credentials: ProviderCredentials): Promise<void> {
    logger.debug({ providerId: this.providerId, enrollmentNo: credentials.enrollmentNo }, "Logging out");
    this.state = IPUProviderState.READY;
  }
}
