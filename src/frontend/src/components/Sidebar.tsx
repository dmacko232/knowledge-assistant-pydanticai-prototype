import { MessageSquarePlus, LogOut, MessagesSquare } from "lucide-react";
import type { ChatSummary } from "../types";
import { useAuth } from "../auth";

interface Props {
  chats: ChatSummary[];
  activeChatId: string | null;
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
}

export default function Sidebar({
  chats,
  activeChatId,
  onSelectChat,
  onNewChat,
}: Props) {
  const { user, logout } = useAuth();

  return (
    <aside className="flex h-full w-72 flex-col border-r border-slate-200 bg-slate-50">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-3">
        <span className="text-xl">🧠</span>
        <h2 className="text-sm font-semibold text-slate-700">
          Knowledge Assistant
        </h2>
      </div>

      {/* New chat button */}
      <div className="p-3">
        <button
          onClick={onNewChat}
          className="flex w-full items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
        >
          <MessageSquarePlus className="h-4 w-4" />
          New Chat
        </button>
      </div>

      {/* Chat list */}
      <nav className="flex-1 overflow-y-auto px-3">
        {chats.length === 0 && (
          <p className="px-2 py-4 text-center text-xs text-slate-400">
            No conversations yet
          </p>
        )}
        {chats.map((chat) => (
          <button
            key={chat.id}
            onClick={() => onSelectChat(chat.id)}
            className={`mb-1 flex w-full items-start gap-2 rounded-lg px-3 py-2 text-left text-sm transition ${
              chat.id === activeChatId
                ? "bg-blue-50 text-blue-700"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            <MessagesSquare className="mt-0.5 h-4 w-4 shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">
                {chat.title || "Untitled chat"}
              </p>
              <p className="text-xs text-slate-400">
                {chat.message_count} messages
              </p>
            </div>
          </button>
        ))}
      </nav>

      {/* User footer */}
      <div className="flex items-center gap-2 border-t border-slate-200 px-4 py-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-sm font-bold text-blue-700">
          {user?.name?.charAt(0).toUpperCase() ?? "?"}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-slate-700">
            {user?.name}
          </p>
        </div>
        <button
          onClick={logout}
          title="Sign out"
          className="rounded p-1 text-slate-400 transition hover:bg-slate-200 hover:text-slate-600"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </aside>
  );
}
