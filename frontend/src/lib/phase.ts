/**
 * Scope flags from the CounselQueue scope discussion. Everything listed here is Phase 2 / future phase:
 * it is built and kept, but hidden until the flag is switched on (nav, routes and controls all read it).
 * Set `VITE_PHASE2=all` to switch everything on for a demo.
 */
export type Phase2Feature =
  | "hallBoard" // Hall Board
  | "studentStatus" // Student Status (status column / filter on the records lists)
  | "insights" // Insights
  | "opsHallQueue" // Hall Queue for the operations lead (reception keeps theirs)
  | "callFromQueue" // Call a student from My Queue (call by token)
  | "pullForward" // Pull forward from My Queue
  | "intakeSummary" // "What they said at check-in"
  | "studentTiming"; // Check-in / Waited / Session in Student Detail and the lists

const ALL: Phase2Feature[] = [
  "hallBoard", "studentStatus", "insights", "opsHallQueue", "callFromQueue", "pullForward", "intakeSummary", "studentTiming",
];
const on = (import.meta.env.VITE_PHASE2 as string | undefined) === "all";

/** Mutable on purpose: tests switch features on to keep covering the Phase 2 code. */
export const phase: Record<Phase2Feature, boolean> = Object.fromEntries(ALL.map((f) => [f, on])) as Record<Phase2Feature, boolean>;

export const setPhase2 = (enabled: boolean, ...features: Phase2Feature[]) => {
  (features.length ? features : ALL).forEach((f) => {
    phase[f] = enabled;
  });
};
