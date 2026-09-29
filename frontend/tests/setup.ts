import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";
import { session } from "../src/api/client";
import { server } from "./utils";

// React logs "not wrapped in act" for updates that resolve between Testing Library polls; the
// assertions already wait for them, so keep the test output readable.
const realError = console.error;
console.error = (...args: unknown[]) => {
  if (typeof args[0] === "string" && args[0].includes("not wrapped in act")) return;
  realError(...args);
};

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterAll(() => server.close());

afterEach(() => {
  cleanup(); // unmount first so background polling stops before handlers are reset
  server.resetHandlers();
  session.clear(); // the in-memory access token must not leak between tests
  window.sessionStorage.clear();
  window.localStorage.clear();
});
