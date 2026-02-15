import { loadAuth } from "./auth";
import { logger } from "./logger";
import type { ChatSummary, Message } from "./types";

const log = logger("api");
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
  email: string
): Promise<{ token: string; user_id: string; name: string }> {
  log.info("Login attempt", { email });
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (res.status === 401) {
    const body = await res.json().catch(() => null);
    const msg = body?.detail ?? "No account found for this email.";
    log.warn("Login rejected (401)", { email, detail: msg });
    throw new Error(msg);
  }
  if (!res.ok) {
    log.error("Login failed", { email, status: res.status });
    throw new Error(`Login failed: ${res.status}`);
  }
  const data = await res.json();
  log.info("Login succeeded", { userId: data.user_id, name: data.name });
  return data;
}

export async function fetchChats(): Promise<ChatSummary[]> {
  log.debug("Fetching chat list");
  const res = await fetch(`${BASE}/chats`, { headers: headers() });
  if (res.status === 401) {
    log.warn("Unauthorized when fetching chats");
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    log.error("Failed to fetch chats", { status: res.status });
    throw new Error(`Failed to fetch chats: ${res.status}`);
  }
  const data = await res.json();
  log.debug("Chat list loaded", { count: data.length });
  return data;
}

export async function fetchMessages(chatId: string): Promise<Message[]> {
  log.debug("Fetching messages", { chatId });
  const res = await fetch(`${BASE}/chats/${chatId}/messages`, {
    headers: headers(),
  });
  if (res.status === 401) {
    log.warn("Unauthorized when fetching messages", { chatId });
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    log.error("Failed to fetch messages", { chatId, status: res.status });
    throw new Error(`Failed to fetch messages: ${res.status}`);
  }
  const data = await res.json();
  log.debug("Messages loaded", { chatId, count: data.length });
  return data;
}

export async function generateTitle(
  chatId: string
): Promise<{ chat_id: string; title: string }> {
  log.debug("Generating title", { chatId });
  const res = await fetch(`${BASE}/chats/${chatId}/title`, {
    method: "POST",
    headers: headers(),
  });
  if (res.status === 401) {
    log.warn("Unauthorized when generating title", { chatId });
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    log.error("Title generation failed", { chatId, status: res.status });
    throw new Error(`Title generation failed: ${res.status}`);
  }
  const data = await res.json();
  log.info("Title generated", { chatId, title: data.title });
  return data;
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
  const msgPreview = message.length > 80 ? message.slice(0, 80) + "..." : message;
  log.info("Sending message (stream)", { chatId, message: msgPreview });

  const res = await fetch(`${BASE}/chat/stream`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({
      message,
      chat_id: chatId,
    }),
  });

  if (res.status === 401) {
    log.warn("Unauthorized when sending message");
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    log.error("Chat stream failed", { chatId, status: res.status });
    throw new Error(`Chat failed: ${res.status}`);
  }

  const reader = res.body?.getReader();
  if (!reader) {
    log.error("No response body on stream");
    throw new Error("No response body");
  }

  const decoder = new TextDecoder();
  let buffer = "";
  let tokenCount = 0;

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
          tokenCount++;
          break;
        case "2":
          // Data annotation
          try {
            const annotations = JSON.parse(payload);
            if (Array.isArray(annotations) && annotations.length > 0) {
              const meta = annotations[0];
              log.info("Stream complete", {
                chatId: meta.chat_id,
                messageId: meta.message_id,
                tokens: tokenCount,
                toolCalls: (meta.tool_calls ?? []).length,
                sources: (meta.sources ?? []).length,
              });
              onDone(meta);
            }
          } catch {
            log.warn("Failed to parse stream annotation", { payload });
          }
          break;
        case "d":
          // Done signal
          log.debug("Stream done signal received");
          break;
      }
    }
  }
}
