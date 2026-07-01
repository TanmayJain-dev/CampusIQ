import { StudentProfile, SemesterResult, ProviderStatus } from "@/core/entities/academic.entity";
import { IUniversityProvider, ProviderCredentials } from "@/core/interfaces/university-provider.interface";

/**
 * A mock provider used strictly for unit testing the registry and factory.
 */
export class MockUniversityProvider implements IUniversityProvider {
  constructor(private readonly providerId: string) {}

  getProviderId(): string {
    return this.providerId;
  }

  validateCredentialsFormat(credentials: ProviderCredentials): boolean {
    return credentials.enrollmentNo.length > 0;
  }

  async healthCheck(): Promise<ProviderStatus> {
    return { isAvailable: true, latencyMs: 10, lastChecked: new Date() };
  }

  async authenticate(credentials: ProviderCredentials): Promise<boolean> {
    return true;
  }

  async fetchStudentProfile(credentials: ProviderCredentials): Promise<StudentProfile> {
    return { 
      enrollmentNo: credentials.enrollmentNo, 
      name: "Test Student", 
      program: "Test", 
      batchYear: 2024 
    };
  }

  async fetchSemesterResults(credentials: ProviderCredentials): Promise<SemesterResult[]> {
    return [];
  }

  async fetchLatestResult(credentials: ProviderCredentials): Promise<SemesterResult | null> {
    return null;
  }

  async checkForUpdates(credentials: ProviderCredentials, lastKnownTerm: number): Promise<boolean> {
    return false;
  }

  async logout(credentials: ProviderCredentials): Promise<void> {
    return;
  }
}
