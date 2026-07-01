/**
 * Formats a number to exactly two decimal places, typical for CGPA/SGPA.
 */
export function formatGpa(gpa: number): string {
  return Number(gpa).toFixed(2);
}

/**
 * Formats a date string into a standard readable format (e.g., 'Oct 12, 2024').
 */
export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(date));
}

/**
 * Formats a large number into a compact representation (e.g., 10.5K).
 */
export function formatCompactNumber(number: number): string {
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(number);
}
