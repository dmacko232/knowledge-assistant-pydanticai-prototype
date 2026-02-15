import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Sidebar from "../components/Sidebar";
import { renderWithProviders } from "./helpers";
import type { ChatSummary } from "../types";

const CHATS: ChatSummary[] = [
  {
    id: "c1",
    title: "Password policy question",
    created_at: "2026-01-01",
    updated_at: "2026-01-01",
    message_count: 4,
  },
  {
    id: "c2",
    title: null,
    created_at: "2026-01-02",
    updated_at: "2026-01-02",
    message_count: 1,
  },
];

describe("Sidebar", () => {
  it("renders the app title", () => {
    renderWithProviders(
      <Sidebar
        chats={[]}
        activeChatId={null}
        onSelectChat={vi.fn()}
        onNewChat={vi.fn()}
      />
    );
    expect(screen.getByText("Knowledge Assistant")).toBeInTheDocument();
  });

  it("shows empty state when no chats", () => {
    renderWithProviders(
      <Sidebar
        chats={[]}
        activeChatId={null}
        onSelectChat={vi.fn()}
        onNewChat={vi.fn()}
      />
    );
    expect(screen.getByText(/no conversations yet/i)).toBeInTheDocument();
  });

  it("renders chat titles and message counts", () => {
    renderWithProviders(
      <Sidebar
        chats={CHATS}
        activeChatId={null}
        onSelectChat={vi.fn()}
        onNewChat={vi.fn()}
      />
    );
    expect(screen.getByText("Password policy question")).toBeInTheDocument();
    expect(screen.getByText("4 messages")).toBeInTheDocument();
    expect(screen.getByText("Untitled chat")).toBeInTheDocument();
    expect(screen.getByText("1 messages")).toBeInTheDocument();
  });

  it("calls onSelectChat when a chat is clicked", async () => {
    const user = userEvent.setup();
    const onSelectChat = vi.fn();

    renderWithProviders(
      <Sidebar
        chats={CHATS}
        activeChatId={null}
        onSelectChat={onSelectChat}
        onNewChat={vi.fn()}
      />
    );

    await user.click(screen.getByText("Password policy question"));
    expect(onSelectChat).toHaveBeenCalledWith("c1");
  });

  it("calls onNewChat when New Chat button is clicked", async () => {
    const user = userEvent.setup();
    const onNewChat = vi.fn();

    renderWithProviders(
      <Sidebar
        chats={CHATS}
        activeChatId={null}
        onSelectChat={vi.fn()}
        onNewChat={onNewChat}
      />
    );

    await user.click(screen.getByText("New Chat"));
    expect(onNewChat).toHaveBeenCalledOnce();
  });

  it("shows user name and initial in footer", () => {
    renderWithProviders(
      <Sidebar
        chats={[]}
        activeChatId={null}
        onSelectChat={vi.fn()}
        onNewChat={vi.fn()}
      />
    );
    expect(screen.getByText("Test User")).toBeInTheDocument();
    expect(screen.getByText("T")).toBeInTheDocument();
  });

  it("calls logout when sign out button is clicked", async () => {
    const user = userEvent.setup();
    const { authValue } = renderWithProviders(
      <Sidebar
        chats={[]}
        activeChatId={null}
        onSelectChat={vi.fn()}
        onNewChat={vi.fn()}
      />
    );

    await user.click(screen.getByTitle("Sign out"));
    expect(authValue.logout).toHaveBeenCalledOnce();
  });
});
