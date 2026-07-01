import { StudentProfile, SemesterResult, CourseResult } from "@/core/entities/academic.entity";
import { ParsingError } from "@/core/errors/provider.error";
import { IPURawStudentProfile, IPURawSemesterResult, IPURawCourse } from "./ipu.types";

/**
 * Transforms raw provider responses into normalized domain models.
 * Never expose provider-specific response formats outside this module.
 */
export class IPUMapper {
  static toStudentProfile(raw: IPURawStudentProfile): StudentProfile {
    try {
      return {
        enrollmentNo: raw.enrollment_number,
        name: raw.student_name,
        program: raw.programme_name,
        batchYear: raw.admission_year ? parseInt(raw.admission_year, 10) : null,
      };
    } catch (error) {
      throw new ParsingError("IPU", "Failed to parse StudentProfile from raw IPU data.");
    }
  }

  static toSemesterResult(raw: IPURawSemesterResult): SemesterResult {
    try {
      return {
        termNumber: parseInt(raw.semester, 10),
        sgpa: parseFloat(raw.sgpa),
        cgpa: raw.cgpa ? parseFloat(raw.cgpa) : null,
        totalCreditsEarned: parseInt(raw.total_credits, 10),
        courses: raw.papers.map(this.toCourseResult),
      };
    } catch (error) {
      throw new ParsingError("IPU", "Failed to parse SemesterResult from raw IPU data.");
    }
  }

  static toCourseResult(raw: IPURawCourse): CourseResult {
    try {
      const internal = raw.internal ? parseFloat(raw.internal) : null;
      const external = raw.external ? parseFloat(raw.external) : null;
      const total = parseFloat(raw.total);
      
      let points = null;
      switch (raw.grade) {
        case 'O': points = 10; break;
        case 'A+': points = 9; break;
        case 'A': points = 8; break;
        case 'B+': points = 7; break;
        case 'B': points = 6; break;
        case 'C': points = 5; break;
        case 'P': points = 4; break;
        case 'F': points = 0; break;
      }

      return {
        courseCode: raw.paper_id,
        courseName: raw.paper_name,
        credits: parseInt(raw.credits, 10),
        internalMarks: internal,
        externalMarks: external,
        totalMarks: total,
        grade: raw.grade,
        points: points,
        passed: raw.grade !== 'F' && total >= 40, // Mock passing criteria
      };
    } catch (error) {
      throw new ParsingError("IPU", "Failed to parse CourseResult from raw IPU data.");
    }
  }
}
