import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { API, centre, fail, http, ok, renderAt, server } from "./utils";

const SLUG = centre.slug;
const landing = (over: Record<string, unknown> = {}) => ({
  centre, open: true, message: "",
  stats: { waiting: 4, counsellors_on_site: 3, avg_wait_min: null, avg_wait_label: "—" },
  steps: ["Fill in your details", "Receive your token on WhatsApp", "Sit anywhere until you're called"],
  bring: ["Marksheets", "Entrance scorecard", "Photo ID", "A parent or guardian"], bring_note: "All optional — come as you are.",
  ...over,
});
const tokenView = (state: Record<string, unknown>, over: Record<string, unknown> = {}) => ({
  token: "PCM-01", status: "waiting", state, stream: "PCM", stream_name: "Science – PCM", name: "Asha Rao", mobile: "9811022001",
  counsellor: "Meera Iyer", desk: "Desk 1", venue: "Hotel Landmark", city: "Gwalior", date: "2026-09-29", closes_at: "18:00",
  front_desk_phone: "98110 00000", checked_in_at: "10:40", consent: "given", rating: null, can_release: true, can_rate: false,
  centre_status: "live", centre_slug: SLUG, ...over,
});

describe("CQ-12/13/14 landing", () => {
  it("names the centre, shows a dash (not zero) before anyone is called, and the three steps", async () => {
    server.use(http.get(`${API}/public/centres/${SLUG}`, () => ok(landing())));
    renderAt(`/c/${SLUG}`);
    expect(await screen.findByRole("heading", { name: "Gwalior counselling" })).toBeInTheDocument();
    expect(screen.getAllByText(/Hotel Landmark/).length).toBeGreaterThan(0);
    const stats = screen.getByLabelText("How busy is the hall");
    expect(within(stats).getByText("—")).toBeInTheDocument();
    expect(within(stats).getByText("4")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Check in" })).toBeInTheDocument();
    expect(screen.getByText("Receive your token on WhatsApp")).toBeInTheDocument();
    expect(screen.getByText("All optional — come as you are.")).toBeInTheDocument();
    expect(screen.getByText(/98110 00000/)).toBeInTheDocument();
  });

  it("a centre that isn't open shows the message instead of the check-in button", async () => {
    server.use(http.get(`${API}/public/centres/${SLUG}`, () => ok(landing({ open: false, message: "This centre isn't open for check-in — it runs on 1 Oct 2026." }))));
    renderAt(`/c/${SLUG}`);
    expect(await screen.findByText(/This centre isn't open for check-in/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Check in" })).toBeNull();
  });

  it("CQ-26: reopening on the same phone returns to the live token, not a blank form", async () => {
    window.localStorage.setItem(`cq.token.${SLUG}`, "key123");
    server.use(http.get(`${API}/public/tokens/key123`, () => ok(tokenView({ kind: "next" }))));
    const { router } = renderAt(`/c/${SLUG}`);
    await waitFor(() => expect(router.state.location.pathname).toBe("/t/key123"));
    expect(await screen.findByLabelText("Token PCM-01")).toBeInTheDocument();
  });
});

describe("CQ-15/16/17/18 check-in flow", () => {
  beforeEach(() => server.use(http.get(`${API}/public/centres/${SLUG}`, () => ok(landing()))));

  async function fillDetails() {
    await userEvent.type(await screen.findByLabelText("Your name"), "Asha Rao");
    await userEvent.type(screen.getByLabelText("School"), "DPS Gwalior");
    await userEvent.type(screen.getByLabelText("Your mobile number"), "+91 98110 22001");
    await userEvent.click(screen.getByRole("button", { name: "Science – PCM" }));
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
  }
  async function fillGoals() {
    await userEvent.type(await screen.findByLabelText(/Course or career/), "B.Tech");
    await userEvent.click(screen.getByRole("button", { name: "College selection" }));
    await userEvent.click(screen.getByRole("checkbox"));
  }

  it("reports every failing details field together and keeps what was typed", async () => {
    renderAt(`/c/${SLUG}/check-in`);
    await userEvent.type(await screen.findByLabelText("Your name"), "Al");
    await userEvent.type(screen.getByLabelText("Your mobile number"), "12345");
    await userEvent.type(screen.getByLabelText("Email (optional)"), "nope");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByText("Enter your name (at least 3 letters).")).toBeInTheDocument();
    expect(screen.getByText("Enter your school.")).toBeInTheDocument();
    expect(screen.getByText("A 10-digit mobile number is needed for the turn alert.")).toBeInTheDocument();
    expect(screen.getByText("That email doesn't look right.")).toBeInTheDocument();
    expect(screen.getByText("Pick the stream you're in.")).toBeInTheDocument();
    expect(screen.getByLabelText("Your name")).toHaveValue("Al");
    expect(screen.getByLabelText("Your mobile number")).toHaveValue("12345");
    expect(screen.getByText("The stream you pick decides which counsellor you're sent to.")).toBeInTheDocument();
  });

  it("goals need a course, a help choice and an unticked-by-default consent; 'None' clears the other exams", async () => {
    renderAt(`/c/${SLUG}/check-in`);
    await fillDetails();
    expect(await screen.findByRole("checkbox")).not.toBeChecked();
    await userEvent.click(screen.getByRole("button", { name: "JEE" }));
    await userEvent.click(screen.getByRole("button", { name: "NEET" }));
    await userEvent.click(screen.getByRole("button", { name: "None / not sure" }));
    expect(screen.getByRole("button", { name: "JEE" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "None / not sure" })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(screen.getByRole("button", { name: "Send my code" }));
    expect(await screen.findByText(/Tell us the course or career/)).toBeInTheDocument();
    expect(screen.getByText("Pick at least one thing you'd like help with.")).toBeInTheDocument();
    expect(screen.getByText("Tick the consent line so a counsellor can advise you")).toBeInTheDocument();
  });

  it("verifies the number, allows changing it without losing answers, then issues the token", async () => {
    let sent = 0;
    const checkins: any[] = [];
    server.use(
      http.post(`${API}/public/centres/${SLUG}/otp/send`, () => { sent += 1; return ok({ resend_after_sec: 30, expires_in_min: 10 }); }),
      http.post(`${API}/public/centres/${SLUG}/otp/verify`, async ({ request }) => {
        const body = (await request.json()) as { code: string };
        return body.code === "1234" ? ok({ verification_id: "vid" }) : fail(400, "otp_mismatch", "That code doesn't match — check your WhatsApp");
      }),
      http.post(`${API}/public/centres/${SLUG}/check-in`, async ({ request }) => { checkins.push(await request.json()); return ok({ access_key: "key123", token: {} }); }),
      http.get(`${API}/public/tokens/key123`, () => ok(tokenView({ kind: "waiting", ahead: 2, minutes: 34, expected_at: "11:20", approximate: true }))),
    );
    renderAt(`/c/${SLUG}/check-in`);
    await fillDetails();
    await fillGoals();
    await userEvent.click(screen.getByRole("button", { name: "Send my code" }));
    expect(await screen.findByRole("heading", { name: /Check your WhatsApp/ })).toBeInTheDocument();
    expect(sent).toBe(1);
    expect(screen.getByText("9811022001")).toBeInTheDocument(); // normalised
    expect(screen.getByRole("button", { name: /Resend code in/ })).toBeDisabled();

    await userEvent.type(screen.getByLabelText("Your code"), "0000");
    await userEvent.click(screen.getByRole("button", { name: "Get my token" }));
    expect(await screen.findByText("That code doesn't match — check your WhatsApp")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "← Change number" }));
    expect(await screen.findByLabelText("Your name")).toHaveValue("Asha Rao"); // every answer kept
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByLabelText(/Course or career/)).toHaveValue("B.Tech");
    expect(screen.getByRole("checkbox")).toBeChecked();
    await userEvent.click(screen.getByRole("button", { name: "Send my code" }));
    await userEvent.type(await screen.findByLabelText("Your code"), "1234");
    await userEvent.click(screen.getByRole("button", { name: "Get my token" }));

    expect(await screen.findByLabelText("Token PCM-01")).toBeInTheDocument();
    expect(checkins[0]).toMatchObject({ mobile: "9811022001", verification_id: "vid", consent: true, stream: "PCM", help: ["College selection"] });
    expect(window.localStorage.getItem(`cq.token.${SLUG}`)).toBe("key123");
  });

  it("CQ-20: a duplicate is blocked with the open token named and a way to see it", async () => {
    server.use(
      http.post(`${API}/public/centres/${SLUG}/otp/send`, () => ok({ resend_after_sec: 30, expires_in_min: 10 })),
      http.post(`${API}/public/centres/${SLUG}/otp/verify`, () => ok({ verification_id: "vid" })),
      http.post(`${API}/public/centres/${SLUG}/check-in`, () =>
        fail(409, "duplicate_token", "A token is already open for this number — PCM-07.", { access_key: "dupkey", token: "PCM-07" })),
    );
    renderAt(`/c/${SLUG}/check-in`);
    await fillDetails();
    await fillGoals();
    await userEvent.click(screen.getByRole("button", { name: "Send my code" }));
    await userEvent.type(await screen.findByLabelText("Your code"), "1234");
    await userEvent.click(screen.getByRole("button", { name: "Get my token" }));
    expect(await screen.findByText("A token is already open for this number — PCM-07.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "See my token" })).toHaveAttribute("href", "/t/dupkey");
  });

  it("server-side field errors send the student back to the step with the problem", async () => {
    server.use(
      http.post(`${API}/public/centres/${SLUG}/otp/send`, () => ok({ resend_after_sec: 30, expires_in_min: 10 })),
      http.post(`${API}/public/centres/${SLUG}/otp/verify`, () => ok({ verification_id: "vid" })),
      http.post(`${API}/public/centres/${SLUG}/check-in`, () =>
        fail(400, "invalid", "That email doesn't look right.", { fields: { email: "That email doesn't look right." } })),
    );
    renderAt(`/c/${SLUG}/check-in`);
    await fillDetails();
    await fillGoals();
    await userEvent.click(screen.getByRole("button", { name: "Send my code" }));
    await userEvent.type(await screen.findByLabelText("Your code"), "1234");
    await userEvent.click(screen.getByRole("button", { name: "Get my token" }));
    expect(await screen.findByText("That email doesn't look right.")).toBeInTheDocument();
    expect(screen.getByLabelText("Your name")).toHaveValue("Asha Rao");
  });
});

describe("CQ-21…28 token page", () => {
  const at = (view: Record<string, unknown>) => {
    server.use(http.get(`${API}/public/tokens/k`, () => ok(view)));
    return renderAt("/t/k");
  };

  it("waiting: how many are ahead at my desk, about how long, and when", async () => {
    at(tokenView({ kind: "waiting", ahead: 2, minutes: 34, expected_at: "11:20", approximate: true }));
    expect(await screen.findByText("2 ahead of you at Desk 1")).toBeInTheDocument();
    expect(screen.getByText(/About 34 min · expected around 11:20/)).toBeInTheDocument();
    expect(screen.getByText(/This is an estimate/)).toBeInTheDocument();
    expect(screen.getByText("Meera Iyer")).toBeInTheDocument();
    expect(screen.getByText(/Lost this page\?/)).toBeInTheDocument();
  });

  it("next replaces the position block", async () => {
    at(tokenView({ kind: "next" }));
    expect(await screen.findByText("You're next")).toBeInTheDocument();
    expect(screen.getByText(/Stay near Desk 1/)).toBeInTheDocument();
    expect(screen.queryByText(/ahead of you/)).toBeNull();
  });

  it("called: names the desk and counsellor and says the place is held", async () => {
    at(tokenView({ kind: "called" }, { status: "called" }));
    expect(await screen.findByText("It's your turn")).toBeInTheDocument();
    expect(screen.getByText(/Go to Desk 1, Meera Iyer\. Your place is held for two calls\./)).toBeInTheDocument();
  });

  it("in session removes the release control and shows no queue position", async () => {
    at(tokenView({ kind: "in_session" }, { status: "in_session", can_release: false }));
    expect(await screen.findByText("Session in progress")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Give up my turn" })).toBeNull();
  });

  it("no-show sends the student to the front desk", async () => {
    at(tokenView({ kind: "no_show" }, { status: "no_show", can_release: false }));
    expect(await screen.findByText("We missed you twice")).toBeInTheDocument();
    expect(screen.getByText(/Visit the front desk and they'll put you back in the queue\./)).toBeInTheDocument();
  });

  it("releasing needs a confirmation", async () => {
    let released = 0;
    server.use(http.post(`${API}/public/tokens/k/release`, () => { released += 1; return ok({}); }));
    at(tokenView({ kind: "waiting", ahead: 1, minutes: 10, expected_at: "11:00", approximate: true }));
    await userEvent.click(await screen.findByRole("button", { name: "Give up my turn" }));
    expect(await screen.findByRole("dialog", { name: "Give up your turn?" })).toBeInTheDocument();
    expect(released).toBe(0);
    await userEvent.click(screen.getByRole("button", { name: "Yes, release" }));
    await waitFor(() => expect(released).toBe(1));
  });

  it("a desk-added student sees consent pending and can confirm it on their own phone", async () => {
    let confirmed = 0;
    server.use(http.post(`${API}/public/tokens/k/consent`, () => { confirmed += 1; return ok({}); }));
    at(tokenView({ kind: "next" }, { consent: "pending", source: "desk" }));
    expect(await screen.findByText("Consent pending")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Confirm it's me" }));
    await waitFor(() => expect(confirmed).toBe(1));
  });

  it("done: the rating is optional, appears once, and is sent as 1–5", async () => {
    const sent: number[] = [];
    server.use(http.post(`${API}/public/tokens/k/rating`, async ({ request }) => { sent.push(((await request.json()) as any).rating); return ok({}); }));
    at(tokenView({ kind: "done" }, { status: "done", can_release: false, can_rate: true }));
    expect(await screen.findByText("Session complete")).toBeInTheDocument();
    expect(screen.getByText("Optional — the page works fine without it.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "4 out of 5" }));
    await waitFor(() => expect(sent).toEqual([4]));
  });

  it("an unknown token explains how to recover", async () => {
    server.use(http.get(`${API}/public/tokens/nope`, () => fail(404, "not_found", "Not found.")));
    renderAt("/t/nope");
    expect(await screen.findByRole("heading", { name: "We can't find this token" })).toBeInTheDocument();
    expect(screen.getByText(/find your token from your mobile number/)).toBeInTheDocument();
  });

  it("polling: the screen moves from waiting to 'you're next' without a reload", async () => {
    let calls = 0;
    server.use(
      http.get(`${API}/public/tokens/k`, () => {
        calls += 1;
        return ok(calls === 1 ? tokenView({ kind: "waiting", ahead: 1, minutes: 12, expected_at: "11:00", approximate: true }) : tokenView({ kind: "next" }));
      }),
    );
    renderAt("/t/k");
    expect(await screen.findByText("1 ahead of you at Desk 1")).toBeInTheDocument();
    expect(await screen.findByText("You're next", {}, { timeout: 8000 })).toBeInTheDocument();
  }, 12000);
});
