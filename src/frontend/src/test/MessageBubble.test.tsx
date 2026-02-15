import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import MessageBubble from "../components/MessageBubble";

describe("MessageBubble", () => {
  it("renders user message content", () => {
    render(<MessageBubble role="user" content="Hello there!" />);
    expect(screen.getByText("Hello there!")).toBeInTheDocument();
  });

  it("renders assistant message with markdown", () => {
    render(
      <MessageBubble role="assistant" content="The policy states **bold**." />
    );
    expect(screen.getByText(/the policy states/i)).toBeInTheDocument();
    expect(screen.getByText("bold")).toBeInTheDocument();
  });

  it("shows a cursor when streaming", () => {
    const { container } = render(
      <MessageBubble role="assistant" content="Loading..." streaming />
    );
    const cursor = container.querySelector(".animate-pulse");
    expect(cursor).toBeInTheDocument();
  });

  it("does NOT show cursor when not streaming", () => {
    const { container } = render(
      <MessageBubble role="assistant" content="Done." />
    );
    const cursor = container.querySelector(".animate-pulse");
    expect(cursor).not.toBeInTheDocument();
  });

  it("does not render SourcesBadge for user messages", () => {
    render(
      <MessageBubble
        role="user"
        content="Hi"
        sources={[
          { document: "doc.md", section: "Intro", date: "2026-01-01" },
        ]}
      />
    );
    expect(screen.queryByText(/source/i)).not.toBeInTheDocument();
  });

  it("renders SourcesBadge for assistant messages with sources", () => {
    render(
      <MessageBubble
        role="assistant"
        content="Answer [1]"
        sources={[
          { document: "doc.md", section: "Intro", date: "2026-01-01" },
        ]}
      />
    );
    expect(screen.getByText(/1 source/)).toBeInTheDocument();
  });

  it("does not render SourcesBadge when streaming", () => {
    render(
      <MessageBubble
        role="assistant"
        content="In progress..."
        sources={[
          { document: "doc.md", section: "Intro", date: "2026-01-01" },
        ]}
        streaming
      />
    );
    expect(screen.queryByText(/source/i)).not.toBeInTheDocument();
  });
});
