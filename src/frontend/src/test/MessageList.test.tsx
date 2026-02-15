import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import MessageList from "../components/MessageList";
import type { DisplayMessage } from "../components/MessageList";

describe("MessageList", () => {
  it("shows empty state when no messages", () => {
    render(<MessageList messages={[]} />);
    expect(screen.getByText(/how can i help/i)).toBeInTheDocument();
    expect(screen.getByText(/company policies/i)).toBeInTheDocument();
  });

  it("renders user and assistant messages", () => {
    const messages: DisplayMessage[] = [
      {
        id: "m1",
        role: "user",
        content: "What is the password policy?",
        sources: [],
        toolCalls: [],
        latencyMs: null,
      },
      {
        id: "m2",
        role: "assistant",
        content: "The password must be at least 12 characters [1].",
        sources: [
          { document: "security.md", section: "Passwords", date: "2026-01" },
        ],
        toolCalls: [],
        latencyMs: 500,
      },
    ];

    render(<MessageList messages={messages} />);

    expect(
      screen.getByText("What is the password policy?")
    ).toBeInTheDocument();
    expect(
      screen.getByText(/password must be at least 12 characters/i)
    ).toBeInTheDocument();
  });

  it("renders streaming message with cursor", () => {
    const messages: DisplayMessage[] = [
      {
        id: "m1",
        role: "user",
        content: "Hello",
        sources: [],
        toolCalls: [],
        latencyMs: null,
      },
      {
        id: "m2",
        role: "assistant",
        content: "Processing...",
        sources: [],
        toolCalls: [],
        latencyMs: null,
        streaming: true,
      },
    ];

    const { container } = render(<MessageList messages={messages} />);
    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
  });
});
