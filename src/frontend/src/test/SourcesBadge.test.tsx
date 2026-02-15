import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SourcesBadge from "../components/SourcesBadge";

describe("SourcesBadge", () => {
  it("returns null when no sources and no tool calls", () => {
    const { container } = render(
      <SourcesBadge sources={[]} toolCalls={[]} latencyMs={null} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("shows source count", () => {
    render(
      <SourcesBadge
        sources={[
          { document: "a.md", section: "S1", date: "2026-01-01" },
          { document: "b.md", section: "S2", date: "2026-01-02" },
        ]}
        toolCalls={[]}
        latencyMs={null}
      />
    );
    expect(screen.getByText(/2 sources/)).toBeInTheDocument();
  });

  it("shows tool call count", () => {
    render(
      <SourcesBadge
        sources={[]}
        toolCalls={[{ name: "search_knowledge_base", args: { query: "test" } }]}
        latencyMs={null}
      />
    );
    expect(screen.getByText(/1 tool call/)).toBeInTheDocument();
  });

  it("shows latency", () => {
    render(
      <SourcesBadge
        sources={[{ document: "a.md", section: "S1", date: "2026-01-01" }]}
        toolCalls={[]}
        latencyMs={1500}
      />
    );
    expect(screen.getByText(/1\.5s/)).toBeInTheDocument();
  });

  it("expands to show source details on click", async () => {
    const user = userEvent.setup();
    render(
      <SourcesBadge
        sources={[{ document: "policy.md", section: "Password", date: "2026-01-15" }]}
        toolCalls={[]}
        latencyMs={null}
      />
    );

    expect(screen.queryByText("policy.md")).not.toBeInTheDocument();

    await user.click(screen.getByText(/1 source/));

    expect(screen.getByText(/policy\.md/)).toBeInTheDocument();
    expect(screen.getByText(/Password/)).toBeInTheDocument();
    expect(screen.getByText(/2026-01-15/)).toBeInTheDocument();
  });

  it("shows tool call names when expanded", async () => {
    const user = userEvent.setup();
    render(
      <SourcesBadge
        sources={[]}
        toolCalls={[
          { name: "search_knowledge_base", args: { query: "rotation" } },
          { name: "lookup_structured_data", args: {} },
        ]}
        latencyMs={null}
      />
    );

    await user.click(screen.getByText(/2 tool calls/));

    expect(screen.getByText("search_knowledge_base")).toBeInTheDocument();
    expect(screen.getByText("lookup_structured_data")).toBeInTheDocument();
  });

  it("collapses on second click", async () => {
    const user = userEvent.setup();
    render(
      <SourcesBadge
        sources={[{ document: "a.md", section: "S", date: "2026" }]}
        toolCalls={[]}
        latencyMs={null}
      />
    );

    const toggle = screen.getByText(/1 source/);
    await user.click(toggle);
    expect(screen.getByText(/a\.md/)).toBeInTheDocument();

    await user.click(toggle);
    expect(screen.queryByText("Sources")).not.toBeInTheDocument();
  });
});
