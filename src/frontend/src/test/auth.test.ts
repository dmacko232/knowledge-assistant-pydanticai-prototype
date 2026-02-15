import { describe, it, expect } from "vitest";
import { saveAuth, loadAuth, clearAuth } from "../auth";
import type { AuthUser } from "../types";

const MOCK_USER: AuthUser = {
  token: "jwt-abc-123",
  user_id: "user-1",
  name: "Alice",
};

describe("auth helpers", () => {
  it("saveAuth stores user in localStorage", () => {
    saveAuth(MOCK_USER);
    const raw = localStorage.getItem("ka_auth");
    expect(raw).not.toBeNull();
    expect(JSON.parse(raw!)).toEqual(MOCK_USER);
  });

  it("loadAuth returns stored user", () => {
    saveAuth(MOCK_USER);
    const loaded = loadAuth();
    expect(loaded).toEqual(MOCK_USER);
  });

  it("loadAuth returns null when nothing stored", () => {
    expect(loadAuth()).toBeNull();
  });

  it("loadAuth returns null for corrupted data", () => {
    localStorage.setItem("ka_auth", "not-valid-json{{{");
    expect(loadAuth()).toBeNull();
  });

  it("clearAuth removes stored user", () => {
    saveAuth(MOCK_USER);
    clearAuth();
    expect(loadAuth()).toBeNull();
  });
});
