/**
 * Reduce any way of writing an Indian mobile number to its 10 digits (the backend does the same:
 * backend/apps/common/validators.py). Handles spaces, dashes, dots, brackets, `+91`, `91`, `0091`, `091`,
 * a leading `0`, and combinations. A 10-digit number is never trimmed: prefixes come off longer numbers only.
 */
export function normaliseMobile(raw: string | null | undefined): string {
  let digits = (raw ?? "").replace(/\D/g, "");
  if (digits.startsWith("00")) digits = digits.slice(2); // 0091 98110 22001
  if (digits.length === 12 && digits.startsWith("91")) digits = digits.slice(2);
  else if (digits.length === 13 && (digits.startsWith("910") || digits.startsWith("091"))) digits = digits.slice(3); // +91 0 98110 22001, 091 98110 22001
  if (digits.length === 11 && digits.startsWith("0")) digits = digits.slice(1);
  return digits;
}

export const validMobile = (raw: string | null | undefined): boolean => /^\d{10}$/.test(normaliseMobile(raw));

export const validEmail = (raw: string): boolean => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(raw.trim());
