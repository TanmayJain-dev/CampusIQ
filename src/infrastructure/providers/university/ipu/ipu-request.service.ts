import { NetworkError } from "@/core/errors/provider.error";
import { logger } from "@/shared/lib/logger";
import { IPUProviderConfig, IPURawStudentProfile, IPURawSemesterResult } from "./ipu.types";

/**
 * Internal Request abstraction for the IPU Provider.
 * This class isolates HTTP request logic (or mock responses) from the main provider logic.
 * Later, this will use Axios or Fetch to perform actual scraping.
 */
export class IPURequestService {
  constructor(private readonly config: IPUProviderConfig) {}

  private async simulateNetworkDelay() {
    return new Promise((resolve) => setTimeout(resolve, 150));
  }

  async login(enrollmentNo: string, password?: string): Promise<boolean> {
    logger.debug({ enrollmentNo }, "RequestService: Simulating login request");
    await this.simulateNetworkDelay();
    
    // Simulate failure for specific mock credentials if needed
    if (enrollmentNo === "00000000000") return false;
    
    return true;
  }

  async fetchRawProfile(enrollmentNo: string): Promise<IPURawStudentProfile> {
    logger.debug({ enrollmentNo }, "RequestService: Simulating profile fetch");
    await this.simulateNetworkDelay();
    
    if (!this.config.featureFlags.useMockData) {
      throw new NetworkError("IPU", "Real scraping not implemented yet. Enable useMockData feature flag.");
    }
    
    return {
      student_name: "John Doe",
      enrollment_number: enrollmentNo,
      programme_name: "B.Tech CSE",
      admission_year: "2022",
    };
  }

  async fetchRawResults(enrollmentNo: string): Promise<IPURawSemesterResult[]> {
    logger.debug({ enrollmentNo }, "RequestService: Simulating results fetch");
    await this.simulateNetworkDelay();
    
    if (!this.config.featureFlags.useMockData) {
      throw new NetworkError("IPU", "Real scraping not implemented yet. Enable useMockData feature flag.");
    }
    
    return [
      {
        semester: "1",
        sgpa: "8.5",
        cgpa: "8.5",
        total_credits: "24",
        papers: [
          {
            paper_id: "ETCS-101",
            paper_name: "Introduction to Programming",
            credits: "4",
            internal: "22",
            external: "60",
            total: "82",
            grade: "A",
          }
        ]
      },
      {
        semester: "2",
        sgpa: "9.0",
        cgpa: "8.75",
        total_credits: "24",
        papers: [
          {
            paper_id: "ETCS-102",
            paper_name: "Data Structures",
            credits: "4",
            internal: "24",
            external: "65",
            total: "89",
            grade: "O",
          }
        ]
      }
    ];
  }
}
