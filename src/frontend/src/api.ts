import { loadAuth } from "./auth";
import type { ChatSummary, Message } from "./types";

const BASE = "/api";

function headers(): HeadersInit {
  const h: HeadersInit = { "Content-Type": "application/json" };
  const auth = loadAuth();
  if (auth?.token) {
    h["Authorization"] = `Bearer ${auth.token}`;
  }
  return h;
}

export async function login(
  name: string,
  email: string
): Promise<{ token: string; user_id: string; name: string }> {
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email }),
  });
  if (!res.ok) throw new Error(`Login failed: ${res.status}`);
  return res.json();
}

export async function fetchChats(): Promise<ChatSummary[]> {
  const res = await fetch(`${BASE}/chats`, { headers: headers() });
  if (res.status === 401) throw new Error("Unauthorized");
  if (!res.ok) throw new Error(`Failed to fetch chats: ${res.status}`);
  return res.json();
}

export async function fetchMessages(chatId: string): Promise<Message[]> {
  const res = await fetch(`${BASE}/chats/${chatId}/messages`, {
    headers: headers(),
  });
  if (res.status === 401) throw new Error("Unauthorized");
  if (!res.ok) throw new Error(`Failed to fetch messages: ${res.status}`);
  return res.json();
}

export async function generateTitle(
  chatId: string
): Promise<{ chat_id: string; title: string }> {
  const res = await fetch(`${BASE}/chats/${chatId}/title`, {
    method: "POST",
    headers: headers(),
  });
  if (res.status === 401) throw new Error("Unauthorized");
  if (!res.ok) throw new Error(`Title generation failed: ${res.status}`);
  return res.json();
}

export async function sendMessageStream(
  message: string,
  chatId: string | null,
  onToken: (token: string) => void,
  onDone: (metadata: {
    chat_id: string;
    message_id: string;
    tool_calls: unknown[];
    sources: unknown[];
  }) => void
): Promise<void> {
  const res = await fetch(`${BASE}/chat/stream`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({
      message,
      chat_id: chatId,
    }),
  });

  if (res.status === 401) throw new Error("Unauthorized");
  if (!res.ok) throw new Error(`Chat failed: ${res.status}`);

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.trim()) continue;

      const prefix = line[0];
      const payload = line.slice(2);

      switch (prefix) {
        case "0":
          // Text token
          try {
            onToken(JSON.parse(payload));
          } catch {
            onToken(payload);
          }
          break;
        case "2":
          // Data annotation
          try {
            const annotations = JSON.parse(payload);
            if (Array.isArray(annotations) && annotations.length > 0) {
              onDone(annotations[0]);
            }
          } catch {
            /* ignore parse errors */
          }
          break;
        case "d":
          // Done signal — no action needed
          break;
      }
    }
  }
}
