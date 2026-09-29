export const NO_DATA = "—";

export const minutesLabel = (m: number | null | undefined): string => (m == null ? NO_DATA : `${m} min`);

export function elapsedLabel(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${String(s).padStart(2, "0")}s`;
}

export const prettyDate = (iso: string): string =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });

export const initials = (name: string): string =>
  name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

export const STATUS_LABELS: Record<string, string> = {
  waiting: "Waiting",
  called: "Called",
  in_session: "In session",
  done: "Completed",
  no_show: "No-show",
  released: "Released",
  not_counselled: "Not counselled",
};

export const STREAMS = [
  { code: "PCM", name: "Science – PCM" },
  { code: "PCB", name: "Science – PCB" },
  { code: "PCMB", name: "Science – PCMB" },
  { code: "COM", name: "Commerce" },
  { code: "HUM", name: "Humanities / Arts" },
  { code: "OTH", name: "Other" },
] as const;
export const EXAMS = ["JEE", "NEET", "CUET", "CLAT", "Other", "None / not sure"] as const;
export const CLARITY = ["Very clear", "Have shortlisted options", "Need help shortlisting", "Completely confused"] as const;
export const HELP = [
  "College selection",
  "Course selection",
  "College & course comparison",
  "Admission / counselling",
  "Cut-offs & college chances",
  "Entrance exams",
  "Other",
] as const;
export const CLASSES = ["Class 11", "Class 12", "Dropper / repeat year", "Graduate", "Parent enquiring"] as const;
export const OUTCOMES = [
  { v: "ready", l: "Ready to apply" },
  { v: "interested", l: "Interested, needs time" },
  { v: "exploring", l: "Just exploring" },
  { v: "not_fit", l: "Not a fit" },
] as const;
export const streamName = (code: string): string => STREAMS.find((s) => s.code === code)?.name ?? code;
