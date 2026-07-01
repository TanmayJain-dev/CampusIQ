export enum IPUProviderState {
  UNINITIALIZED = "UNINITIALIZED",
  READY = "READY",
  AUTHENTICATED = "AUTHENTICATED",
  SYNCING = "SYNCING",
  FAILED = "FAILED",
  LOCKED = "LOCKED",
}

export interface IPUProviderConfig {
  baseUrl: string;
  timeoutMs: number;
  retryPolicy: {
    maxRetries: number;
    backoffMs: number;
  };
  userAgent: string;
  rateLimitSettings: {
    requestsPerMinute: number;
  };
  featureFlags: {
    enableHtmlParsing: boolean;
    useMockData: boolean;
  };
}

export interface IPURawStudentProfile {
  student_name: string;
  enrollment_number: string;
  programme_name: string;
  admission_year: string;
}

export interface IPURawCourse {
  paper_id: string;
  paper_name: string;
  credits: string;
  internal: string;
  external: string;
  total: string;
  grade: string;
}

export interface IPURawSemesterResult {
  semester: string;
  sgpa: string;
  cgpa: string;
  total_credits: string;
  papers: IPURawCourse[];
}
