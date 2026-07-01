import { z } from "zod";

export const CourseResultSchema = z.object({
  courseCode: z.string(),
  courseName: z.string(),
  credits: z.number(),
  internalMarks: z.number().nullable(),
  externalMarks: z.number().nullable(),
  totalMarks: z.number(),
  grade: z.string().nullable(),
  points: z.number().nullable(),
  passed: z.boolean(),
});
export type CourseResult = z.infer<typeof CourseResultSchema>;

export const SemesterResultSchema = z.object({
  termNumber: z.number(),
  sgpa: z.number(),
  cgpa: z.number().nullable(),
  totalCreditsEarned: z.number(),
  courses: z.array(CourseResultSchema),
});
export type SemesterResult = z.infer<typeof SemesterResultSchema>;

export const StudentProfileSchema = z.object({
  enrollmentNo: z.string(),
  name: z.string(),
  program: z.string().nullable(),
  batchYear: z.number().nullable(),
});
export type StudentProfile = z.infer<typeof StudentProfileSchema>;

export const ProviderStatusSchema = z.object({
  isAvailable: z.boolean(),
  latencyMs: z.number(),
  lastChecked: z.date(),
  message: z.string().optional(),
  version: z.string().optional(),
  lastSuccessfulSync: z.date().optional(),
});
export type ProviderStatus = z.infer<typeof ProviderStatusSchema>;
