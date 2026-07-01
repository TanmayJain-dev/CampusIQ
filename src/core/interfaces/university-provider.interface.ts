import { StudentProfile, SemesterResult, ProviderStatus } from "../entities/academic.entity";

export interface ProviderCredentials {
  enrollmentNo: string;
  password?: string;
  token?: string;
}

export interface IUniversityProvider {
  /** Uniquely identifies the provider (e.g., 'IPU', 'DU') */
  getProviderId(): string;
  
  /** Validates credentials and establishes a session if necessary */
  authenticate(credentials: ProviderCredentials): Promise<boolean>;
  
  /** Fetches basic student details */
  fetchStudentProfile(credentials: ProviderCredentials): Promise<StudentProfile>;
  
  /** Fetches all historical semester results */
  fetchSemesterResults(credentials: ProviderCredentials): Promise<SemesterResult[]>;
  
  /** Fetches only the latest declared semester result */
  fetchLatestResult(credentials: ProviderCredentials): Promise<SemesterResult | null>;
  
  /** Checks if any new results have been published since the last check */
  checkForUpdates(credentials: ProviderCredentials, lastKnownTerm: number): Promise<boolean>;
  
  /** Invalidates any active session on the university portal */
  logout(credentials: ProviderCredentials): Promise<void>;
  
  /** Validates if the provided credentials format is correct before attempting auth */
  validateCredentialsFormat(credentials: ProviderCredentials): boolean;
  
  /** Returns the current operational status of the university portal */
  healthCheck(): Promise<ProviderStatus>;
}
