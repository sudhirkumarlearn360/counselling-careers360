/** Mirrors backend apps.common.validators: strip spaces and '-', then one leading '+91' or '0'. */
export function normaliseMobile(raw: string | null | undefined): string {
  let value = (raw ?? "").trim().replace(/[\s-]/g, "");
  if (value.startsWith("+91")) value = value.slice(3);
  else if (value.startsWith("0")) value = value.slice(1);
  return value;
}

export const validMobile = (raw: string | null | undefined): boolean => /^\d{10}$/.test(normaliseMobile(raw));

export const validEmail = (raw: string): boolean => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(raw.trim());
