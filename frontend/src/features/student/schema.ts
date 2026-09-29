import { z } from "zod";
import { validEmail, validMobile } from "../../lib/mobile";
import { STREAMS } from "../../lib/format";

/** Exact messages from counselqueue-ui-spec; the backend returns the same strings. */
export const MSG = {
  name: "Enter your name (at least 3 letters).",
  school: "Enter your school.",
  mobile: "A 10-digit mobile number is needed for the turn alert.",
  parent: "Parent's number should be 10 digits.",
  email: "That email doesn't look right.",
  stream: "Pick the stream you're in.",
  course: "Tell us the course or career you're aiming for — 'not sure yet' is fine.",
  help: "Pick at least one thing you'd like help with.",
  consent: "Tick the consent line so a counsellor can advise you",
} as const;

const STREAM_CODES = STREAMS.map((s) => s.code) as [string, ...string[]];

export const detailsSchema = z.object({
  name: z.string().trim().min(3, MSG.name),
  school: z.string().trim().min(1, MSG.school),
  mobile: z.string().refine((v) => validMobile(v), MSG.mobile),
  parent_mobile: z.string().refine((v) => !v.trim() || validMobile(v), MSG.parent),
  email: z.string().refine((v) => !v.trim() || validEmail(v), MSG.email),
  stream: z.enum(STREAM_CODES, { errorMap: () => ({ message: MSG.stream }) }),
  klass: z.string(),
});

export const goalsSchema = z.object({
  course: z.string().trim().min(1, MSG.course),
  exams: z.array(z.string()),
  clarity: z.string(),
  help: z.array(z.string()).min(1, MSG.help),
  consent: z.literal(true, { errorMap: () => ({ message: MSG.consent }) }),
});

export type CheckInForm = z.infer<typeof detailsSchema> & Omit<z.infer<typeof goalsSchema>, "consent"> & { consent: boolean };
export const DETAILS_FIELDS = ["name", "school", "mobile", "parent_mobile", "email", "stream", "klass"] as const;
export const GOALS_FIELDS = ["course", "exams", "clarity", "help", "consent"] as const;

export const EMPTY_FORM: CheckInForm = {
  name: "", school: "", mobile: "", parent_mobile: "", email: "", stream: "" as never, klass: "",
  course: "", exams: [], clarity: "", help: [], consent: false,
};

/** "None / not sure" clears the others; picking anything else clears "None / not sure". */
export function toggleExam(current: string[], exam: string): string[] {
  if (exam === "None / not sure") return current.includes(exam) ? [] : [exam];
  const without = current.filter((e) => e !== "None / not sure");
  return without.includes(exam) ? without.filter((e) => e !== exam) : [...without, exam];
}

export const tokenStoreKey = (slug: string) => `cq.token.${slug}`;
export const savedToken = (slug: string): string | null => {
  try {
    return window.localStorage.getItem(tokenStoreKey(slug));
  } catch {
    return null;
  }
};
export const saveToken = (slug: string, key: string | null) => {
  try {
    if (key) window.localStorage.setItem(tokenStoreKey(slug), key);
    else window.localStorage.removeItem(tokenStoreKey(slug));
  } catch {
    /* the page works without storage; the WhatsApp link is the fallback */
  }
};
