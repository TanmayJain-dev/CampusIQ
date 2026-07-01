import { ParsingError } from "@/core/errors/provider.error";
import { IPURawStudentProfile, IPURawSemesterResult } from "../ipu.types";

/**
 * Isolated parsers.
 * Never performs networking. Only receives HTML string and extracts data.
 */
export class IPUParsers {
  static parseStudentProfile(html: string, enrollmentNo: string): IPURawStudentProfile {
    try {
      // Mock parsing logic based on mock HTML
      if (html.includes("Profile: John Doe")) {
        return {
          student_name: "John Doe",
          enrollment_number: enrollmentNo,
          programme_name: "B.Tech CSE",
          admission_year: "2022",
        };
      }
      throw new Error("Profile elements not found");
    } catch (error) {
      throw new ParsingError("IPU", `Failed to parse student profile: ${error instanceof Error ? error.message : 'Unknown'}`);
    }
  }

  static parseSemesterResults(html: string): IPURawSemesterResult[] {
    try {
      // Mock parsing logic
      if (html.includes("Results Table Data")) {
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
          }
        ];
      }
      return [];
    } catch (error) {
      throw new ParsingError("IPU", `Failed to parse semester results: ${error instanceof Error ? error.message : 'Unknown'}`);
    }
  }
}
