import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { setPhase2 } from "../src/lib/phase";
import { API, centre, fail, http, ok, renderAt, server, signInAs } from "./utils";

const row = (over: Record<string, unknown> = {}) => ({
  id: 1, token: "PCM-01", name: "Priya Nair", mobile: "9811022001", stream: "PCM", status: "waiting", source: "self",
  counsellor: { id: 3, name: "Meera Iyer", desk: "Desk 1" }, checked_in_at: "10:00", waited_min: 42, late: true,
  consent_pending: false, recalls: 0, alert_failed: false, alert_failed_message: "", ...over,
});
const hall = (over: Record<string, unknown> = {}) => ({
  centre, header: { waiting: 2, late: 1, wait_promise_min: 30 },
  tabs: [
    { key: "all", label: "All students", counsellor_id: null, count: 2, late: 1 },
    { key: "c3", label: "Meera Iyer · Desk 1", counsellor_id: 3, count: 2, late: 1, duty: "on_desk" },
    { key: "c4", label: "Rahul Sen · Desk 2", counsellor_id: 4, count: 0, late: 0, duty: "off_duty" },
  ],
  rows: [row(), row({ id: 2, token: "PCM-02", name: "Sahil", late: false, waited_min: 5, consent_pending: true, alert_failed: true, alert_failed_message: "WhatsApp didn't reach them — turn alert. Call out their token." })],
  query: "", count: 2, ...over,
});

describe("CQ-31…34 front desk hall queue", () => {
  beforeEach(() => signInAs("reception"));

  it("lists the hall with late, consent-pending and failed-alert flags; tabs include an empty desk", async () => {
    server.use(http.get(`${API}/hall/centres/1/queue`, () => ok(hall())));
    renderAt("/console/hall");
    const list = await screen.findByRole("list", { name: "Students in the hall" });
    expect(within(list).getByText("PCM-01")).toBeInTheDocument();
    expect(within(list).getByText("late")).toBeInTheDocument();
    expect(within(list).getByText("consent pending")).toBeInTheDocument();
    expect(within(list).getByText("alert failed")).toHaveAttribute("title", expect.stringContaining("turn alert"));
    const tabs = screen.getAllByRole("tab");
    expect(tabs[0]).toHaveTextContent("All students");
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
    expect(tabs[2]).toHaveTextContent("Rahul Sen"); // an off-duty desk with zero students still has a tab
    expect(tabs[1]).toHaveTextContent("1 late");
  });

  it("selecting a tab asks for that counsellor only, and search takes over from the tab", async () => {
    const seen: string[] = [];
    server.use(http.get(`${API}/hall/centres/1/queue`, ({ request }) => { seen.push(new URL(request.url).search); return ok(hall()); }));
    renderAt("/console/hall");
    await screen.findByRole("list", { name: "Students in the hall" });
    await userEvent.click(screen.getAllByRole("tab")[1]);
    await waitFor(() => expect(seen.some((s) => s.includes("counsellor=3"))).toBe(true));
    await userEvent.type(screen.getByRole("searchbox"), "2001");
    await waitFor(() => expect(seen.some((s) => s.includes("q=2001"))).toBe(true));
    expect(screen.getAllByRole("tab").every((t) => t.getAttribute("aria-selected") === "false")).toBe(true);
  });

  it("empty states: nobody in the hall, and a search with no match suggests the last four digits", async () => {
    server.use(http.get(`${API}/hall/centres/1/queue`, ({ request }) => {
      const q = new URL(request.url).searchParams.get("q");
      return ok(hall({ rows: [], count: 0, query: q ?? "" }));
    }));
    renderAt("/console/hall");
    expect(await screen.findByText("No one in the hall yet — tokens appear here as students scan in.")).toBeInTheDocument();
    await userEvent.type(screen.getByRole("searchbox"), "zzzz");
    expect(await screen.findByText("No match for “zzzz”.")).toBeInTheDocument();
    expect(screen.getByText("Try the last four digits of their mobile.")).toBeInTheDocument();
    expect(await screen.findByText("0 results")).toBeInTheDocument();
  });

  it("moving a student to a counsellor who doesn't cover the stream asks first, and keeps the token", async () => {
    const moves: any[] = [];
    server.use(
      http.get(`${API}/hall/centres/1/queue`, () => ok(hall())),
      http.post(`${API}/hall/students/1/move`, async ({ request }) => {
        const body = (await request.json()) as any;
        moves.push(body);
        return body.confirm ? ok({}) : fail(409, "needs_confirmation", "Rahul Sen doesn't cover Science – PCM. Move anyway?");
      }),
    );
    renderAt("/console/hall");
    await userEvent.click((await screen.findAllByRole("button", { name: "Move" }))[0]);
    await userEvent.click(await screen.findByRole("button", { name: /Rahul Sen · Desk 2 — 0 in queue/ }));
    expect(await screen.findByText("Rahul Sen doesn't cover Science – PCM. Move anyway?")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Move anyway" }));
    await waitFor(() => expect(moves).toEqual([{ counsellor_id: 4, confirm: false }, { counsellor_id: 4, confirm: true }]));
  });

  it("CQ-30: a duplicate at the desk names the token, links to it and issues nothing", async () => {
    server.use(http.post(`${API}/hall/centres/1/check-in`, () => fail(409, "duplicate_token", "A token is already open for this number — PCM-01.", { student_id: 1, token: "PCM-01" })));
    renderAt("/console/add");
    await userEvent.type(await screen.findByLabelText("Student name"), "Walk In");
    await userEvent.type(screen.getByLabelText("Mobile"), "9811022001");
    await userEvent.click(screen.getByRole("button", { name: "College selection" }));
    await userEvent.click(screen.getByRole("button", { name: "Issue token" }));
    expect(await screen.findByText("A token is already open for this number — PCM-01.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open the existing token/ })).toBeInTheDocument();
    expect(screen.getByLabelText("Student name")).toHaveValue("Walk In");
  });

  it("CQ-29: a successful desk check-in confirms the counsellor and clears the form for the next student", async () => {
    server.use(http.post(`${API}/hall/centres/1/check-in`, () => ok({ token: "PCM-05" }, { message: "Token PCM-05 issued to Meera Iyer, Desk 1." })));
    renderAt("/console/add");
    await userEvent.type(await screen.findByLabelText("Student name"), "Walk In");
    await userEvent.type(screen.getByLabelText("Mobile"), "9811022001");
    await userEvent.click(screen.getByRole("button", { name: "College selection" }));
    await userEvent.click(screen.getByRole("button", { name: "Issue token" }));
    expect((await screen.findAllByText(/Token PCM-05 issued to Meera Iyer, Desk 1\./)).length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Student name")).toHaveValue("");
    expect(screen.getByRole("button", { name: "College selection" })).toHaveAttribute("aria-pressed", "false");
  });

  it("never asks for ops/live (it is ops-only)", async () => {
    let asked = 0;
    server.use(http.get(`${API}/ops/live`, () => { asked += 1; return fail(403, "role_not_allowed", "Your role can't open this screen."); }), http.get(`${API}/hall/centres/1/queue`, () => ok(hall())));
    renderAt("/console/hall");
    await screen.findByRole("list", { name: "Students in the hall" });
    expect(asked).toBe(0);
  });
});

describe("CQ-5 ops lead opens a desk", () => {
  const live = [{ ...centre, counsellors: [{ posting_id: 9, counsellor_id: 3, name: "Meera Iyer", streams: ["PCM"], desk_label: "Desk 1", duty: "on_desk", serving: { token: "PCM-04", status: "called" }, queue_length: 12, avg_session_min: 14, counselled_today: 5 }] }];
  beforeEach(() => signInAs("ops_lead", { name: "Nikhil Bhatia" }));

  it("every counsellor card has an Open desk control", async () => {
    server.use(http.get(`${API}/ops/live`, () => ok(live)));
    renderAt("/console/live");
    const link = await screen.findByRole("link", { name: "Open desk" });
    expect(link).toHaveAttribute("href", "/console/desk/3/queue");
    expect(screen.getByText(/Queue:/)).toHaveTextContent("Queue: 12");
  });

  it("a persistent banner names the desk, says actions are recorded against them, and goes back", async () => {
    server.use(
      http.get(`${API}/ops/live`, () => ok(live)),
      http.get(`${API}/desk/queue`, ({ request }) => {
        expect(new URL(request.url).searchParams.get("as_counsellor")).toBe("3");
        return ok({ centre: null, message: "You're not posted to a live centre today.", queue: [], current: null });
      }),
    );
    const { router } = renderAt("/console/desk/3/queue");
    const banner = await screen.findByRole("status", { name: "Desk context" });
    await waitFor(() => expect(banner).toHaveTextContent("Viewing Meera Iyer's desk"));
    expect(banner).toHaveTextContent("Anything you do here is recorded against that counsellor.");
    await userEvent.click(within(banner).getByRole("button", { name: "Back to live centres" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/console/live"));
    expect(screen.queryByText(/Viewing Meera Iyer/)).toBeNull();
  });

  it("a counsellor is sent back to their own screen if they try to open a desk", async () => {
    signInAs("counsellor", { counsellor: 3, name: "Meera Iyer" });
    server.use(http.get(`${API}/desk/queue`, () => ok({ centre: null, message: "You're not posted to a live centre today.", queue: [], current: null })));
    const { router } = renderAt("/console/desk/4/queue");
    await waitFor(() => expect(router.state.location.pathname).toBe("/console/queue"));
  });
});

describe("CQ-39…49 counsellor desk", () => {
  beforeEach(() => signInAs("counsellor", { counsellor: 3, name: "Meera Iyer" }));
  const student = (over: Record<string, unknown> = {}) => ({
    id: 7, token: "PCM-07", status: "called", source: "desk", name: "Sahil Yadav", school: "KV No.1", mobile: "9000010003", parent_mobile: "",
    email: "", stream: "PCM", stream_name: "Science – PCM", klass: "Class 12", course: "B.Tech", exams: ["JEE"], clarity: "", help: ["College selection"],
    consent: "pending", consent_at: null, consent_by: null, counsellor: { id: 3, name: "Meera Iyer", desk: "Desk 1" }, checked_in_at: "10:00",
    recalls: 0, rating: null, outcome: null, follow_up_on: null, colleges_discussed: "", home_city: "", target_exam: "", budget: "", accompanied_by: "",
    notes: [], timer: null, ...over,
  });
  const desk = (current: unknown, over: Record<string, unknown> = {}) => ({
    centre, desk: "Desk 1", duty: "on_desk", counsellor: { id: 3, name: "Meera Iyer" },
    figures: { in_queue: 2, waiting_hall: 5, counselled_today: 3, avg_session_min: null, target_session_min: 15, late: 1, wait_promise_min: 30 },
    next_token: "PCM-08", current, queue: [
      { id: 8, token: "PCM-08", name: "First", stream: "PCM", klass: "Class 12", waited_min: 40, source: "self", consent_pending: false, late: true, next: true },
      { id: 9, token: "PCM-09", name: "Second", stream: "PCM", klass: "", waited_min: 5, source: "desk", consent_pending: true, late: false, next: false },
    ], ...over,
  });

  it("CQ-38/39: header figures, next student highlighted, one control naming the token to call", async () => {
    server.use(http.get(`${API}/desk/queue`, () => ok(desk(null))));
    renderAt("/console/queue");
    expect(await screen.findByRole("button", { name: "Call PCM-08" })).toBeEnabled();
    expect(screen.getByText("in my queue")).toBeInTheDocument();
    expect(screen.getByText("Next")).toBeInTheDocument();
    expect(screen.getAllByText("consent pending").length).toBeGreaterThan(0);
    expect(screen.getByText(/Added at desk/)).toBeInTheDocument();
    expect(screen.getByText(/Hotel Landmark/)).toBeInTheDocument();
  });

  it("Phase 1 scope: no call-by-token, no pull forward, no 'what they said at check-in'", async () => {
    server.use(http.get(`${API}/desk/queue`, () => ok(desk(null))));
    renderAt("/console/queue");
    await screen.findByRole("button", { name: "Call PCM-08" });
    expect(screen.queryByLabelText("Call a token")).toBeNull();
    expect(screen.queryByRole("button", { name: "Pull forward" })).toBeNull();
  });

  it("Phase 2 (switched on): call by token and pull forward work", async () => {
    setPhase2(true, "callFromQueue", "pullForward");
    server.use(http.get(`${API}/desk/queue`, () => ok(desk(null))));
    renderAt("/console/queue");
    expect(await screen.findByLabelText("Call a token")).toBeInTheDocument();
    const rows = within(screen.getByRole("list", { name: "My queue" })).getAllByRole("listitem");
    expect(within(rows[0]).queryByRole("button", { name: "Pull forward" })).toBeNull(); // none on the top row
    expect(within(rows[1]).getByRole("button", { name: "Pull forward" })).toBeInTheDocument();
  });

  it("CQ-39: while a student is called the call control is replaced by the reason", async () => {
    server.use(http.get(`${API}/desk/queue`, () => ok(desk(student()))));
    renderAt("/console/queue");
    expect(await screen.findByText("Finish PCM-07 before calling the next student.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Call PCM-08" })).toBeNull();
  });

  it("CQ-37: switching duty sends the chosen state", async () => {
    const duties: string[] = [];
    server.use(http.get(`${API}/desk/queue`, () => ok(desk(null))), http.post(`${API}/desk/duty`, async ({ request }) => { duties.push(((await request.json()) as any).duty); return ok({}); }));
    renderAt("/console/queue");
    await userEvent.click(await screen.findByRole("button", { name: "On Break" }));
    await waitFor(() => expect(duties).toEqual(["on_break"]));
  });

  it("CQ-42: Start is blocked while consent is pending, with the reason, until verbal consent is recorded", async () => {
    let consent = "pending";
    server.use(
      http.get(`${API}/desk/queue`, () => ok(desk(student({ consent })))),
      http.post(`${API}/desk/students/7/consent`, () => { consent = "given"; return ok({}); }),
    );
    renderAt("/console/session");
    expect(await screen.findByRole("button", { name: "Start session" })).toBeDisabled();
    expect(screen.getByText("Consent is pending — record verbal consent or resend the request.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Record verbal consent" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Start session" })).toBeEnabled());
  });

  it("Phase 1 scope: the live session hides 'what they said at check-in'", async () => {
    server.use(http.get(`${API}/desk/queue`, () => ok(desk(student({ consent: "given", status: "in_session" })))));
    renderAt("/console/session");
    await screen.findByRole("button", { name: "Save details" });
    expect(screen.queryByLabelText("What the student told us")).toBeNull();
  });

  it("Phase 2 (switched on) CQ-43/47: what the student told us shows first with 'Not answered' for blanks; the timer shows only after start", async () => {
    setPhase2(true, "intakeSummary");
    server.use(http.get(`${API}/desk/queue`, () => ok(desk(student({ consent: "given", status: "in_session", timer: { elapsed_seconds: 65, target_min: 15, over_target: false, waiting: 2 } })))));
    renderAt("/console/session");
    const intake = await screen.findByLabelText("What the student told us");
    expect(within(intake).getByText("B.Tech")).toBeInTheDocument();
    expect(within(intake).getAllByText("Not answered").length).toBeGreaterThan(0); // parent contact, clarity
    expect(screen.getByText(/1m 0\d?s|1m 05s|1m 06s/)).toBeInTheDocument();
    expect(screen.getByText("target 15 min")).toBeInTheDocument();
  });

  it("CQ-47: over target changes the state and shows how many are still waiting; the session is never ended for you", async () => {
    server.use(http.get(`${API}/desk/queue`, () => ok(desk(student({ consent: "given", status: "in_session", timer: { elapsed_seconds: 1000, target_min: 15, over_target: true, waiting: 2 } })))));
    renderAt("/console/session");
    expect(await screen.findByText(/over the 15 min target · 2 still waiting for you/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mark done" })).toBeInTheDocument();
  });

  it("CQ-45: an empty note is refused with the exact message; notes show author and time", async () => {
    server.use(
      http.get(`${API}/desk/queue`, () => ok(desk(student({ consent: "given", notes: [{ id: 1, text: "Wants govt college.", author: "Meera Iyer", at: "2026-09-29T05:30:00Z" }] })))),
      http.post(`${API}/desk/students/7/notes`, () => fail(400, "invalid", "Write something before adding a note.", { fields: { text: "Write something before adding a note." } })),
    );
    renderAt("/console/session");
    expect(await screen.findByText("Wants govt college.")).toBeInTheDocument();
    const notes = screen.getByLabelText("Notes");
    expect(within(notes).getByText(/Meera Iyer ·/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Add note" }));
    expect(await screen.findByText("Write something before adding a note.")).toBeInTheDocument();
  });

  it("CQ-44: field errors from the server are shown against the field", async () => {
    server.use(
      http.get(`${API}/desk/queue`, () => ok(desk(student({ consent: "given" })))),
      http.patch(`${API}/desk/students/7`, () => fail(400, "invalid", "Name is required.", { fields: { name: "Name is required." } })),
    );
    renderAt("/console/session");
    await userEvent.clear(await screen.findByLabelText("Name"));
    await userEvent.click(screen.getByRole("button", { name: "Save details" }));
    expect((await screen.findAllByText("Name is required.")).length).toBeGreaterThan(0);
  });
});

describe("Phase 1 scope: Hall board, Insights and the ops Hall queue are hidden", () => {
  it("the public board says it is coming in Phase 2", async () => {
    renderAt(`/board/${centre.slug}`);
    expect(await screen.findByText("The hall board is coming in Phase 2.")).toBeInTheDocument();
  });
  it("an ops lead has no Insights / Hall queue / Hall board and is sent back if they open one", async () => {
    signInAs("ops_lead");
    server.use(http.get(`${API}/ops/live`, () => ok([])));
    const { router } = renderAt("/console/insights");
    await waitFor(() => expect(router.state.location.pathname).toBe("/console/live"));
    for (const name of ["Insights", "Hall queue", "Hall board"]) expect(screen.queryByRole("link", { name })).toBeNull();
    expect(screen.getByRole("link", { name: "All students" })).toBeInTheDocument();
  });
});

describe("Phase 2 code stays working when switched on", () => {
  it("CQ-51…53: the hall board shows big tokens, dimmed empty desks and the desk states", async () => {
    setPhase2(true, "hallBoard");
    server.use(http.get(`${API}/public/board/${centre.slug}`, () => ok({
      centre, now: "11:05", total_waiting: 3,
      panels: [
        { desk: "Desk 1", counsellor: "Meera Iyer", duty: "on_desk", serving: "PCM-04", next: "PCM-05", waiting: 2, line: "" },
        { desk: "Desk 2", counsellor: "Rahul Sen", duty: "on_break", serving: null, next: null, waiting: 1, line: "back shortly" },
        { desk: "Desk 3", counsellor: "Asha Nair", duty: "on_desk", serving: null, next: null, waiting: 0, line: "queue clear" },
      ],
      recently_called: ["PCM-04", "COM-02"], recently_called_empty: "", standing_line: "Scan the code at the entrance to check in — keep your phone on for your turn alert.",
    })));
    renderAt(`/board/${centre.slug}`);
    expect((await screen.findAllByText("PCM-04")).length).toBeGreaterThan(0);
    expect(screen.getByText("Next: PCM-05 · 2 waiting")).toBeInTheDocument();
    expect(screen.getByText("back shortly")).toBeInTheDocument();
    expect(screen.getByText("queue clear")).toBeInTheDocument();
    expect(screen.getAllByLabelText("Now serving").filter((n) => n.textContent === "—")).toHaveLength(2);
    expect(screen.getByLabelText("Recently called")).toHaveTextContent("COM-02");
  });

  it("CQ-61: thin data shows dashes, never zero, and averages state how many records they come from", async () => {
    setPhase2(true, "insights");
    signInAs("ops_lead");
    server.use(
      http.get(`${API}/ops/centres`, () => ok([])),
      http.get(`${API}/ops/insights`, () => ok({
        headline: { counselled_or_queued: 0, avg_wait: { value: null, n: 0, label: "—", promise_min: 30 }, avg_session: { value: 14, n: 3, label: "14 min (from 3)", target_min: 15 }, no_show_rate: { value: null, label: "—", n: 0 } },
        demand: [{ stream: "PCM", name: "Science – PCM", count: 4, share: 1 }], help: [{ option: "College selection", count: 3 }], clarity: [],
        outcomes: [{ outcome: "ready", label: "Ready to apply", count: 1 }, { outcome: null, label: "Not set", count: 2 }], follow_ups: 1, rating: { avg: null, n: 0, label: "—" },
      })),
    );
    renderAt("/console/insights");
    expect(await screen.findByText("14 min (from 3)")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(3);
    expect(screen.getByText("Not set")).toBeInTheDocument();
  });
});

describe("Add a Centre and All Students (agreed scope)", () => {
  const centreFull = (over: Record<string, unknown> = {}) => ({
    ...centre, id: 1, city: "Gwalior", venue: "Hotel Landmark", expected_students: 100, covered_streams: [], uncovered_streams: [], counsellor_count: 0,
    front_desk_email: "gwalior.desk@careers360.com", ...over,
  });
  beforeEach(() => signInAs("ops_lead"));

  it("Add a Centre asks for the front desk's email and password and shows the login on the card", async () => {
    const bodies: any[] = [];
    server.use(
      http.get(`${API}/ops/centres`, () => ok([centreFull()])),
      http.post(`${API}/ops/centres`, async ({ request }) => {
        bodies.push(await request.json());
        return bodies.length === 1
          ? fail(400, "invalid", "The password must be at least 8 characters.", { fields: { password: ["The password must be at least 8 characters."] } })
          : ok(centreFull({ id: 2 }));
      }),
    );
    renderAt("/console/centres");
    expect(await screen.findByText(/Front desk login: gwalior\.desk@careers360\.com/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "New centre" }));
    const dlg = await screen.findByRole("dialog", { name: "New centre" });
    await userEvent.type(within(dlg).getByLabelText("City"), "Indore");
    await userEvent.type(within(dlg).getByLabelText("Venue"), "Hotel Fortune");
    await userEvent.type(within(dlg).getByLabelText("Email"), "indore.desk@careers360.com");
    const pw = within(dlg).getByLabelText("Password");
    expect(pw).toHaveAttribute("type", "password");
    await userEvent.type(pw, "short");
    await userEvent.click(within(dlg).getByRole("button", { name: "Save centre" }));
    expect(await within(dlg).findByRole("alert")).toHaveTextContent("The password must be at least 8 characters.");
    await userEvent.clear(pw);
    await userEvent.type(pw, "frontdesk-1");
    await userEvent.click(within(dlg).getByRole("button", { name: "Save centre" }));
    await waitFor(() => expect(bodies).toHaveLength(2));
    expect(bodies[1]).toMatchObject({ city: "Indore", email: "indore.desk@careers360.com", password: "frontdesk-1" });
  });

  it("All Students: venue options depend on the selected centre; Apply commits the filters; Clear resets them", async () => {
    const seen: string[] = [];
    server.use(
      http.get(`${API}/ops/centres`, () => ok([
        centreFull({ id: 1, city: "Gwalior", venue: "Hotel Landmark" }),
        centreFull({ id: 2, city: "Gwalior", venue: "City Hall" }),
        centreFull({ id: 3, city: "Indore", venue: "Brilliant Convention Centre" }),
      ])),
      http.get(`${API}/ops/counsellors`, () => ok([])),
      http.get(`${API}/ops/students`, ({ request }) => { seen.push(new URL(request.url).search); return ok([], { count: 0, total: 12 }); }),
    );
    renderAt("/console/students");
    expect(await screen.findByText("0 of 12 students")).toBeInTheDocument();
    const venue = screen.getByLabelText("Venue");
    expect(venue).toBeDisabled(); // no centre chosen yet
    await userEvent.selectOptions(screen.getByLabelText("Centre"), "Gwalior");
    expect(venue).toBeEnabled();
    expect(within(venue).getAllByRole("option").map((o) => o.textContent)).toEqual(["Venue", "City Hall", "Hotel Landmark"]);
    await userEvent.selectOptions(venue, "City Hall");
    const before = seen.length;
    await userEvent.type(screen.getByRole("searchbox"), "priya");
    expect(seen.length).toBe(before); // nothing is sent until Apply
    await userEvent.click(screen.getByRole("button", { name: "Apply" }));
    await waitFor(() => expect(seen.some((s) => s.includes("city=Gwalior") && s.includes("venue=City+Hall") && s.includes("q=priya"))).toBe(true));
    await userEvent.selectOptions(screen.getByLabelText("Centre"), "Indore");
    expect(screen.getByLabelText("Venue")).toHaveValue(""); // changing the centre resets the venue
    expect(within(screen.getByLabelText("Venue")).getAllByRole("option").map((o) => o.textContent)).toEqual(["Venue", "Brilliant Convention Centre"]);
    await userEvent.click(screen.getByRole("button", { name: "Clear" }));
    expect(screen.getByRole("searchbox")).toHaveValue("");
    expect(screen.getByLabelText("Centre")).toHaveValue("");
    expect(screen.getByLabelText("Venue")).toBeDisabled();
    await waitFor(() => expect(seen[seen.length - 1]).toBe(""));
  });

  it("Phase 1 scope: no Status filter or Wait/Session columns on the records list", async () => {
    server.use(
      http.get(`${API}/ops/centres`, () => ok([])),
      http.get(`${API}/ops/counsellors`, () => ok([])),
      http.get(`${API}/ops/students`, () => ok([{ id: 1, token: "PCM-01", name: "Priya", mobile: "9811022001", school: "DPS", stream: "PCM", course: "B.Tech", centre: { id: 1, city: "Gwalior" }, date: "2026-09-29", counsellor: "Meera", wait_min: 5, session_min: 10, outcome: "ready", status: "done" }], { count: 1, total: 1 })),
    );
    renderAt("/console/students");
    const table = await screen.findByRole("table");
    expect(within(table).queryByRole("columnheader", { name: "Status" })).toBeNull();
    expect(within(table).queryByRole("columnheader", { name: "Wait" })).toBeNull();
    expect(within(table).queryByRole("columnheader", { name: "Session" })).toBeNull();
    expect(screen.queryByLabelText("Status")).toBeNull();
    expect(within(table).getByRole("columnheader", { name: "Outcome" })).toBeInTheDocument();
  });
});
