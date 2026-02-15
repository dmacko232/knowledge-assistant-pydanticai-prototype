import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";
import type { Source, ToolCall } from "../types";

export interface DisplayMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: Source[];
  toolCalls: ToolCall[];
  latencyMs: number | null;
  streaming?: boolean;
}

interface Props {
  messages: DisplayMessage[];
}

export default function MessageList({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  const lastMessageContent = messages[messages.length - 1]?.content;
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, lastMessageContent]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="text-center">
          <div className="mb-3 text-5xl">🧠</div>
          <h2 className="text-lg font-semibold text-slate-700">
            How can I help?
          </h2>
          <p className="mt-1 max-w-sm text-sm text-slate-400">
            Ask about company policies, runbooks, KPIs, employee directory, or
            anything in the internal knowledge base.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">
      <div className="mx-auto max-w-3xl space-y-4">
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            role={msg.role}
            content={msg.content}
            sources={msg.sources}
            toolCalls={msg.toolCalls}
            latencyMs={msg.latencyMs}
            streaming={msg.streaming}
          />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
