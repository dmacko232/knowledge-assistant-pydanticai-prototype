import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { User, Bot } from "lucide-react";
import SourcesBadge from "./SourcesBadge";
import type { Source, ToolCall } from "../types";

interface Props {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  toolCalls?: ToolCall[];
  latencyMs?: number | null;
  streaming?: boolean;
}

export default function MessageBubble({
  role,
  content,
  sources = [],
  toolCalls = [],
  latencyMs = null,
  streaming = false,
}: Props) {
  const isUser = role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : ""}`}>
      {!isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
          <Bot className="h-4 w-4" />
        </div>
      )}

      <div
        className={`max-w-2xl rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-blue-600 text-white"
            : "border border-slate-200 bg-white text-slate-800"
        }`}
      >
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap">{content}</p>
        ) : (
          <div className="prose prose-sm prose-slate max-w-none prose-p:my-1 prose-li:my-0.5 prose-headings:mt-3 prose-headings:mb-1">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
            {streaming && (
              <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse rounded-sm bg-slate-400" />
            )}
          </div>
        )}

        {!isUser && !streaming && (
          <SourcesBadge
            sources={sources}
            toolCalls={toolCalls}
            latencyMs={latencyMs}
          />
        )}
      </div>

      {isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 text-blue-700">
          <User className="h-4 w-4" />
        </div>
      )}
    </div>
  );
}
