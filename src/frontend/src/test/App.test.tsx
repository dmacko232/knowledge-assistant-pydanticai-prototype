import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "../App";

vi.mock("../api", () => ({
  login: vi.fn(),
  fetchChats: vi.fn().mockResolvedValue([]),
  fetchMessages: vi.fn().mockResolvedValue([]),
  sendMessageStream: vi.fn(),
}));

describe("App routing", () => {
  it("redirects to /login when not authenticated", () => {
    localStorage.clear();
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>
    );
    expect(
      screen.getByText("Northwind Knowledge Assistant")
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
  });

  it("shows chat page when authenticated", () => {
    localStorage.setItem(
      "ka_auth",
      JSON.stringify({
        token: "tok",
        user_id: "u",
        name: "Alice",
      })
    );

    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>
    );

    expect(screen.getByText("Knowledge Assistant")).toBeInTheDocument();
    expect(screen.getByText(/how can i help/i)).toBeInTheDocument();
  });

  it("redirects /login to / when already authenticated", () => {
    localStorage.setItem(
      "ka_auth",
      JSON.stringify({
        token: "tok",
        user_id: "u",
        name: "Alice",
      })
    );

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <App />
      </MemoryRouter>
    );

    expect(screen.getByText("Knowledge Assistant")).toBeInTheDocument();
    expect(screen.queryByLabelText("Email")).not.toBeInTheDocument();
  });
});
