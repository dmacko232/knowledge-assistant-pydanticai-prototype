import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ChatInput from "../components/ChatInput";

describe("ChatInput", () => {
  it("renders a textarea and send button", () => {
    render(<ChatInput onSend={vi.fn()} />);
    expect(
      screen.getByPlaceholderText(/ask about policies/i)
    ).toBeInTheDocument();
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("send button is disabled when input is empty", () => {
    render(<ChatInput onSend={vi.fn()} />);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("calls onSend with trimmed text on submit", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByPlaceholderText(/ask about policies/i);
    await user.type(textarea, "  Hello world  ");
    await user.click(screen.getByRole("button"));

    expect(onSend).toHaveBeenCalledWith("Hello world");
  });

  it("clears input after sending", async () => {
    const user = userEvent.setup();
    render(<ChatInput onSend={vi.fn()} />);

    const textarea = screen.getByPlaceholderText(
      /ask about policies/i
    ) as HTMLTextAreaElement;
    await user.type(textarea, "Hello");
    await user.click(screen.getByRole("button"));

    expect(textarea.value).toBe("");
  });

  it("sends on Enter key (without Shift)", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByPlaceholderText(/ask about policies/i);
    await user.type(textarea, "Hello{Enter}");

    expect(onSend).toHaveBeenCalledWith("Hello");
  });

  it("does NOT send on Shift+Enter (allows newline)", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByPlaceholderText(/ask about policies/i);
    await user.type(textarea, "Hello{Shift>}{Enter}{/Shift}");

    expect(onSend).not.toHaveBeenCalled();
  });

  it("disables textarea and button when disabled prop is true", () => {
    render(<ChatInput onSend={vi.fn()} disabled />);
    expect(screen.getByPlaceholderText(/ask about policies/i)).toBeDisabled();
  });

  it("does not call onSend when disabled even with text", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    const { rerender } = render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByPlaceholderText(/ask about policies/i);
    await user.type(textarea, "Hello");

    rerender(<ChatInput onSend={onSend} disabled />);
    await user.click(screen.getByRole("button"));

    expect(onSend).not.toHaveBeenCalled();
  });
});
