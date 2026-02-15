import { useState } from "react";
import { ChevronDown, ChevronUp, FileText } from "lucide-react";
import type { Source, ToolCall } from "../types";

interface Props {
  sources: Source[];
  toolCalls: ToolCall[];
  latencyMs: number | null;
}

export default function SourcesBadge({ sources, toolCalls, latencyMs }: Props) {
  const [open, setOpen] = useState(false);

  if (sources.length === 0 && toolCalls.length === 0) return null;

  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 text-xs text-slate-400 transition hover:text-slate-600"
      >
        <FileText className="h-3 w-3" />
        {sources.length} source{sources.length !== 1 && "s"}
        {toolCalls.length > 0 && ` · ${toolCalls.length} tool call${toolCalls.length !== 1 ? "s" : ""}`}
        {latencyMs != null && ` · ${(latencyMs / 1000).toFixed(1)}s`}
        {open ? (
          <ChevronUp className="h-3 w-3" />
        ) : (
          <ChevronDown className="h-3 w-3" />
        )}
      </button>

      {open && (
        <div className="mt-2 space-y-1.5 rounded-lg bg-slate-50 p-3 text-xs">
          {sources.length > 0 && (
            <div>
              <p className="mb-1 font-semibold text-slate-500">Sources</p>
              {sources.map((s, i) => (
                <div key={i} className="flex gap-2 text-slate-600">
                  <span className="font-mono text-slate-400">[{i + 1}]</span>
                  <span>
                    {s.document} — {s.section}
                    {s.date && s.date !== "Unknown" && (
                      <span className="text-slate-400"> ({s.date})</span>
                    )}
                  </span>
                </div>
              ))}
            </div>
          )}
          {toolCalls.length > 0 && (
            <div>
              <p className="mb-1 font-semibold text-slate-500">Tool Calls</p>
              {toolCalls.map((tc, i) => (
                <div key={i} className="text-slate-600">
                  <span className="font-mono text-blue-600">{tc.name}</span>
                  {"args" in tc && tc.args && (
                    <span className="ml-1 text-slate-400">
                      ({Object.entries(tc.args)
                        .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
                        .join(", ")})
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
