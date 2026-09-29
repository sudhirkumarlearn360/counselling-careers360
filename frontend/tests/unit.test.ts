import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { canOpen, defaultPath, NAV } from "../src/lib/nav";
import { normaliseMobile, validEmail, validMobile } from "../src/lib/mobile";
import { toggleExam } from "../src/features/student/schema";
import { detailsSchema, goalsSchema } from "../src/features/student/schema";

describe("normaliseMobile (same fixtures as the backend)", () => {
  it.each([
    ["+91 98110 22001", "9811022001"],
    ["098110 22001", "9811022001"],
    ["98110-22001", "9811022001"],
    ["9811022001", "9811022001"],
  ])("%s -> %s", (raw, expected) => expect(normaliseMobile(raw)).toBe(expected));

  it("CQ-15 accepts exactly ten digits", () => {
    expect(validMobile("98110 22001")).toBe(true);
    expect(validMobile("12345")).toBe(false);
    expect(validMobile("98110220011")).toBe(false);
    expect(validEmail("a@b.co")).toBe(true);
    expect(validEmail("nope")).toBe(false);
  });
});

describe("CQ-3 navigation is built from the role alone", () => {
  it("matches the domain matrix", () => {
    expect(NAV.reception.map((n) => n.label)).toEqual(["Hall queue", "Add a student", "Hall board"]);
    expect(NAV.counsellor.map((n) => n.label)).toEqual(["My queue", "Live session", "My students", "My centres"]);
    expect(NAV.ops_lead.map((n) => n.label)).toEqual([
      "Live centres", "Centres & dates", "Counsellors", "All students", "Insights", "Hall queue", "Hall board",
    ]);
  });
  it("no role has an empty nav and each has a default screen", () => {
    for (const role of Object.keys(NAV) as (keyof typeof NAV)[]) {
      expect(NAV[role].length).toBeGreaterThan(0);
      expect(canOpen(role, defaultPath(role))).toBe(true);
    }
  });
  it("blocks screens outside the role; only ops can open a desk", () => {
    expect(canOpen("reception", "/console/students")).toBe(false);
    expect(canOpen("counsellor", "/console/centres")).toBe(false);
    expect(canOpen("counsellor", "/console/desk/3/queue")).toBe(false);
    expect(canOpen("ops_lead", "/console/desk/3/queue")).toBe(true);
    expect(NAV.ops_lead.some((n) => n.path.includes("/desk/"))).toBe(false); // never a permanent item
  });
});

describe("CQ-15/16 student form rules", () => {
  it("reports every failing details field together with the exact messages", () => {
    const r = detailsSchema.safeParse({ name: "Al", school: "", mobile: "12", parent_mobile: "9", email: "x", stream: "", klass: "" });
    expect(r.success).toBe(false);
    const msgs = Object.fromEntries((r.success ? [] : r.error.issues).map((i) => [String(i.path[0]), i.message]));
    expect(msgs).toMatchObject({
      name: "Enter your name (at least 3 letters).",
      school: "Enter your school.",
      mobile: "A 10-digit mobile number is needed for the turn alert.",
      parent_mobile: "Parent's number should be 10 digits.",
      email: "That email doesn't look right.",
      stream: "Pick the stream you're in.",
    });
  });
  it("goals need a course, one help option and an explicit consent tick", () => {
    const r = goalsSchema.safeParse({ course: "", exams: [], clarity: "", help: [], consent: false });
    const msgs = Object.fromEntries((r.success ? [] : r.error.issues).map((i) => [String(i.path[0]), i.message]));
    expect(msgs.consent).toBe("Tick the consent line so a counsellor can advise you");
    expect(msgs.help).toBe("Pick at least one thing you'd like help with.");
    expect(msgs.course).toContain("not sure yet");
  });
  it("'None / not sure' is exclusive", () => {
    expect(toggleExam(["JEE", "NEET"], "None / not sure")).toEqual(["None / not sure"]);
    expect(toggleExam(["None / not sure"], "JEE")).toEqual(["JEE"]);
    expect(toggleExam(["JEE"], "JEE")).toEqual([]);
  });
});

describe("student pages are fully responsive (CQ-12, user priority)", () => {
  const css = readFileSync(resolve(__dirname, "../src/styles/student.css"), "utf8");
  it("is a fluid single column that becomes a centred card, then two columns", () => {
    expect(css).toMatch(/max-width:\s*560px/);
    expect(css).toMatch(/@media \(min-width: 600px\)/);
    expect(css).toMatch(/@media \(min-width: 900px\)/);
    expect(css).toMatch(/grid-template-columns:\s*minmax\(0, 1\.05fr\) minmax\(0, 1fr\)/);
  });
  it("scales type with clamp(), keeps 44px tap targets and never fixes a width above 320px", () => {
    expect(css).toMatch(/clamp\(/);
    expect(css).toMatch(/min-height:\s*var\(--tap\)/);
    const fixedWidths = [...css.matchAll(/(?<![-\w])width:\s*(\d+)px/g)].map((m) => Number(m[1]));
    expect(fixedWidths.filter((w) => w > 320)).toEqual([]);
  });
  it("uses a 16px+ input font so phones don't zoom on focus", () => {
    const global = readFileSync(resolve(__dirname, "../src/styles/global.css"), "utf8");
    expect(global).toMatch(/\.input[^}]*font-size:\s*1rem/s);
  });
});
