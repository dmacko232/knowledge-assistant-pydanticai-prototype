export interface ChatSummary {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  tool_calls: ToolCall[];
  sources: Source[];
  model: string | null;
  latency_ms: number | null;
  created_at: string;
}

export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  result?: string;
}

export interface Source {
  document: string;
  section: string;
  date: string;
}

export interface ChatResponse {
  chat_id: string;
  message_id: string;
  answer: string;
  tool_calls: ToolCall[];
  sources: Source[];
}

export interface AuthUser {
  token: string;
  user_id: string;
  name: string;
}
