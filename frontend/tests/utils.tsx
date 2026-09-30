import { render } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient } from "@tanstack/react-query";
import { Providers } from "../src/app/providers";
import { routes } from "../src/app/router";
import type { Me } from "../src/api/types";

export const API = "http://localhost:8000/api/1";

// Sidebar counts are background calls every test would otherwise have to mock; tests override any of these.
const baseHandlers = [
  http.get(`${API}/ops/live`, () => HttpResponse.json({ data: [] })),
  http.get(`${API}/ops/centres`, () => HttpResponse.json({ data: [] })),
  http.get(`${API}/ops/counsellors`, () => HttpResponse.json({ data: [] })),
  http.get(`${API}/ops/students`, () => HttpResponse.json({ data: [], count: 0, total: 0 })),
  http.get(`${API}/desk/my-students`, () => HttpResponse.json({ data: [] })),
  http.get(`${API}/desk/queue`, () => HttpResponse.json({ data: { centre: null, message: "", queue: [], current: null } })),
  http.get(`${API}/hall/centres/1/queue`, () =>
    HttpResponse.json({ data: { centre: {}, header: { waiting: 0, late: 0, wait_promise_min: 30 }, tabs: [], rows: [], query: "", count: 0 } }),
  ),
];
export const server = setupServer(...baseHandlers);

export const ok = (data: unknown, extra: Record<string, unknown> = {}) => HttpResponse.json({ data, ...extra });
export const fail = (status: number, code: string, message: string, data: Record<string, unknown> = {}) =>
  HttpResponse.json({ code, message, data }, { status });

export function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(routes, {
    initialEntries: [path],
    future: { v7_relativeSplatPath: true, v7_fetcherPersist: true, v7_normalizeFormMethod: true, v7_partialHydration: true, v7_skipActionErrorRevalidation: true },
  });
  const utils = render(
    <Providers client={client}>
      <RouterProvider router={router} future={{ v7_startTransition: true }} />
    </Providers>,
  );
  return { ...utils, router, client };
}

export const centre = {
  id: 1, city: "Gwalior", venue: "Hotel Landmark", date: "2026-09-29", slug: "gwalior-2026-09-29",
  status: "live" as const, opens_at: "10:00", closes_at: "18:00", front_desk_phone: "98110 00000",
  student_url: "http://localhost:5173/c/gwalior-2026-09-29",
};

export const meFor = (role: Me["role"], extra: Partial<Me> = {}): Me => ({
  id: 1, name: "Pooja Menon", email: "reception@careers360.com", title: "", role, counsellor: null,
  default_view: "hall", nav: [], centre: role === "reception" ? centre : null, posting: null, ...extra,
});

/** Start signed in as `role`: token in the session store and auth/me answered. */
export function signInAs(role: Me["role"], extra: Partial<Me> = {}) {
  window.sessionStorage.setItem("cq.access", "test-access");
  window.sessionStorage.setItem("cq.refresh", "test-refresh");
  server.use(http.get(`${API}/auth/me`, () => ok(meFor(role, extra))));
}
export { http, HttpResponse };
