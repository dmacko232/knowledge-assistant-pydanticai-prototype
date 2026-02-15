import { useState, useEffect, useCallback } from "react";
import Sidebar from "../components/Sidebar";
import MessageList from "../components/MessageList";
import type { DisplayMessage } from "../components/MessageList";
import ChatInput from "../components/ChatInput";
import {
  fetchChats,
  fetchMessages,
  generateTitle,
  sendMessageStream,
} from "../api";
import { logger } from "../logger";
import type { ChatSummary, Source, ToolCall } from "../types";

const log = logger("chat");

export default function Chat() {
  const [chats, setChats] = useState<ChatSummary[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [loading, setLoading] = useState(false);

  // Load chat list
  const loadChats = useCallback(async () => {
    try {
      const list = await fetchChats();
      setChats(list);
    } catch (err) {
      log.warn("Failed to load chat list", {
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }, []);

  useEffect(() => {
    loadChats();
  }, [loadChats]);

  // Load messages when selecting a chat
  const selectChat = useCallback(async (chatId: string) => {
    log.info("Selected chat", { chatId });
    setActiveChatId(chatId);
    try {
      const msgs = await fetchMessages(chatId);
      setMessages(
        msgs.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          sources: m.sources as Source[],
          toolCalls: m.tool_calls as ToolCall[],
          latencyMs: m.latency_ms,
        }))
      );
    } catch (err) {
      log.error("Failed to load messages", {
        chatId,
        error: err instanceof Error ? err.message : String(err),
      });
      setMessages([]);
    }
  }, []);

  const startNewChat = useCallback(() => {
    log.info("Starting new chat");
    setActiveChatId(null);
    setMessages([]);
  }, []);

  // Send message with streaming
  const handleSend = useCallback(
    async (text: string) => {
      const userMsg: DisplayMessage = {
        id: `tmp-user-${Date.now()}`,
        role: "user",
        content: text,
        sources: [],
        toolCalls: [],
        latencyMs: null,
      };

      const assistantMsg: DisplayMessage = {
        id: `tmp-assistant-${Date.now()}`,
        role: "assistant",
        content: "",
        sources: [],
        toolCalls: [],
        latencyMs: null,
        streaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setLoading(true);

      try {
        await sendMessageStream(
          text,
          activeChatId,
          // onToken
          (token) => {
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last && last.role === "assistant") {
                updated[updated.length - 1] = {
                  ...last,
                  content: last.content + token,
                };
              }
              return updated;
            });
          },
          // onDone
          (metadata) => {
            const isNewChat = !activeChatId && metadata.chat_id;
            if (isNewChat) {
              setActiveChatId(metadata.chat_id);
            }
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last && last.role === "assistant") {
                updated[updated.length - 1] = {
                  ...last,
                  id: metadata.message_id,
                  streaming: false,
                  sources: (metadata.sources ?? []) as Source[],
                  toolCalls: (metadata.tool_calls ?? []) as ToolCall[],
                };
              }
              return updated;
            });
            loadChats();

            // Generate LLM title for new chats after first reply
            if (isNewChat) {
              generateTitle(metadata.chat_id)
                .then(() => loadChats())
                .catch((err) => {
                  log.warn("Title generation failed (best-effort)", {
                    chatId: metadata.chat_id,
                    error: err instanceof Error ? err.message : String(err),
                  });
                });
            }
          }
        );
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : "Something went wrong";
        log.error("Chat message failed", { chatId: activeChatId, error: errorMsg });
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last && last.role === "assistant") {
            updated[updated.length - 1] = {
              ...last,
              content: last.content || `Error: ${errorMsg}`,
              streaming: false,
            };
          }
          return updated;
        });
      } finally {
        setLoading(false);
      }
    },
    [activeChatId, loadChats]
  );

  return (
    <div className="flex h-screen">
      <Sidebar
        chats={chats}
        activeChatId={activeChatId}
        onSelectChat={selectChat}
        onNewChat={startNewChat}
      />
      <main className="flex flex-1 flex-col">
        <MessageList messages={messages} />
        <ChatInput onSend={handleSend} disabled={loading} />
      </main>
    </div>
  );
}
