import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Login from "../pages/Login";
import { renderWithProviders } from "./helpers";
import * as api from "../api";

vi.mock("../api", () => ({
  login: vi.fn(),
}));

describe("Login page", () => {
  beforeEach(() => {
    vi.mocked(api.login).mockReset();
  });

  it("renders the login form", () => {
    renderWithProviders(<Login />, { user: null, route: "/login" });

    expect(
      screen.getByText("Northwind Knowledge Assistant")
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("shows validation error when email is empty", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Login />, { user: null, route: "/login" });

    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(
      screen.getByText("Email is required")
    ).toBeInTheDocument();
    expect(api.login).not.toHaveBeenCalled();
  });

  it("calls api.login and auth.login on successful submit", async () => {
    const user = userEvent.setup();
    vi.mocked(api.login).mockResolvedValue({
      token: "jwt-tok",
      user_id: "u-1",
      name: "Alice",
    });

    const { authValue } = renderWithProviders(<Login />, {
      user: null,
      route: "/login",
    });

    await user.type(screen.getByLabelText("Email"), "alice@northwind.com");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(api.login).toHaveBeenCalledWith("alice@northwind.com");
    });

    await waitFor(() => {
      expect(authValue.login).toHaveBeenCalledWith({
        token: "jwt-tok",
        user_id: "u-1",
        name: "Alice",
      });
    });
  });

  it("shows error message when login fails", async () => {
    const user = userEvent.setup();
    vi.mocked(api.login).mockRejectedValue(new Error("No account found for this email."));

    renderWithProviders(<Login />, { user: null, route: "/login" });

    await user.type(screen.getByLabelText("Email"), "unknown@evil.com");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText("No account found for this email.")).toBeInTheDocument();
    });
  });
});
