import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { API, fail, http, ok, renderAt, server, signInAs } from "./utils";

describe("CQ-1 sign in", () => {
  it("blank fields show the exact message", async () => {
    renderAt("/console/login");
    await userEvent.click(await screen.findByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Enter your work email and password");
  });

  it("the password is hidden by default and can be shown", async () => {
    renderAt("/console/login");
    const pw = await screen.findByLabelText("Password");
    expect(pw).toHaveAttribute("type", "password");
    await userEvent.click(screen.getByRole("button", { name: "Show" }));
    expect(pw).toHaveAttribute("type", "text");
  });

  it("lands each role on its own screen, with no centre/desk/role selectors", async () => {
    server.use(
      http.post(`${API}/auth/login`, () =>
        ok({ access: "a", refresh: "r", user: { id: 1, name: "Meera Iyer", role: "counsellor", email: "m@c.com", title: "", counsellor: 2, default_view: "queue", nav: [], centre: null, posting: { id: 1, desk_label: "Desk 1", duty: "on_desk" } }, failed_attempts: 0 }),
      ),
      http.get(`${API}/desk/queue`, () => ok({ centre: null, message: "You're not posted to a live centre today.", queue: [], current: null })),
    );
    const { router } = renderAt("/console/login");
    await userEvent.type(await screen.findByLabelText("Work email"), "meera@careers360.com");
    await userEvent.type(screen.getByLabelText("Password"), "desk123");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/console/queue"));
    expect(screen.queryByRole("combobox", { name: /centre|desk|role/i })).toBeNull();
    expect(screen.getByText(/Meera Iyer · Counsellor/)).toBeInTheDocument();
  });
});

describe("CQ-2 failed sign in", () => {
  it("shows one generic error, keeps the email, clears the password, and adds the helpdesk on the 3rd failure", async () => {
    let n = 0;
    server.use(
      http.post(`${API}/auth/login`, () => {
        n += 1;
        return fail(400, "invalid_credentials", "That email and password don't match an account.", {
          failed_attempts: n,
          show_helpdesk: n >= 3,
          helpdesk_notice: n >= 3 ? "Three failed attempts — contact the IT helpdesk: 1800 572 9877 · it-support@careers360.com" : null,
        });
      }),
    );
    renderAt("/console/login");
    const email = await screen.findByLabelText("Work email");
    for (let i = 1; i <= 3; i++) {
      await userEvent.clear(email);
      await userEvent.type(email, "Meera@Careers360.com");
      await userEvent.type(screen.getByLabelText("Password"), "wrong");
      await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
      await screen.findByText("That email and password don't match an account.");
      expect(screen.getByLabelText("Password")).toHaveValue("");
      expect(email).toHaveValue("Meera@Careers360.com");
      if (i < 3) expect(screen.queryByText(/Three failed attempts/)).toBeNull();
    }
    expect(await screen.findByText(/Three failed attempts/)).toBeInTheDocument();
    expect(screen.queryByText(/reset/i)).toBeNull(); // no self-service reset in this release
  });
});

describe("CQ-3 / CQ-4 role guard and sign out", () => {
  it("sends a signed-out visitor to sign in", async () => {
    const { router } = renderAt("/console/hall");
    await waitFor(() => expect(router.state.location.pathname).toBe("/console/login"));
  });

  it("returns a receptionist to their own screen when they open a screen outside their role", async () => {
    signInAs("reception");
    server.use(http.get(`${API}/ops/live`, () => ok([])), http.get(`${API}/hall/centres/1/queue`, () => ok({ centre: {}, header: { waiting: 0, late: 0, wait_promise_min: 30 }, tabs: [], rows: [], query: "", count: 0 })));
    const { router } = renderAt("/console/insights");
    await waitFor(() => expect(router.state.location.pathname).toBe("/console/hall"));
    expect(screen.queryByRole("link", { name: "Insights" })).toBeNull();
    expect(screen.queryByRole("link", { name: "All students" })).toBeNull();
    expect(screen.getByRole("link", { name: "Add a student" })).toBeInTheDocument();
  });

  it("sign out is on every screen, clears the session and can't be undone with back", async () => {
    signInAs("reception");
    server.use(
      http.post(`${API}/auth/logout`, () => ok({ signed_out: true })),
      http.get(`${API}/hall/centres/1/queue`, () => ok({ centre: {}, header: { waiting: 0, late: 0, wait_promise_min: 30 }, tabs: [], rows: [], query: "", count: 0 })),
    );
    const { router } = renderAt("/console/hall");
    await userEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/console/login"));
    expect(window.sessionStorage.getItem("cq.access")).toBeNull();
    await router.navigate(-1).catch(() => undefined);
    await waitFor(() => expect(router.state.location.pathname).toBe("/console/login"));
  });
});
