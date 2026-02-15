import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  login,
  fetchChats,
  fetchMessages,
  generateTitle,
  sendMessageStream,
} from "../api";
import { saveAuth } from "../auth";

function mockFetchResponse(body: unknown, status = 200) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    body: null,
  });
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

describe("login", () => {
  it("calls POST /api/auth/login with name and email", async () => {
    const mockResponse = {
      token: "tok-1",
      user_id: "u-1",
      name: "Alice",
    };
    vi.stubGlobal("fetch", mockFetchResponse(mockResponse));

    const result = await login("Alice", "alice@northwind.com");

    expect(fetch).toHaveBeenCalledWith("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "Alice", email: "alice@northwind.com" }),
    });
    expect(result).toEqual(mockResponse);
  });

  it("throws on non-OK response", async () => {
    vi.stubGlobal("fetch", mockFetchResponse({}, 500));
    await expect(login("A", "a@b.com")).rejects.toThrow("Login failed: 500");
  });
});

describe("fetchChats", () => {
  it("sends Authorization header when logged in", async () => {
    saveAuth({ token: "my-jwt", user_id: "u", name: "A" });
    vi.stubGlobal("fetch", mockFetchResponse([]));

    await fetchChats();

    expect(fetch).toHaveBeenCalledWith("/api/chats", {
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer my-jwt",
      },
    });
  });

  it("throws Unauthorized on 401", async () => {
    vi.stubGlobal("fetch", mockFetchResponse({}, 401));
    await expect(fetchChats()).rejects.toThrow("Unauthorized");
  });

  it("returns chat list", async () => {
    const chats = [
      {
        id: "c1",
        title: "Test",
        created_at: "2026-01-01",
        updated_at: "2026-01-01",
        message_count: 2,
      },
    ];
    vi.stubGlobal("fetch", mockFetchResponse(chats));
    const result = await fetchChats();
    expect(result).toEqual(chats);
  });
});

describe("fetchMessages", () => {
  it("fetches messages for a chat", async () => {
    const msgs = [
      {
        id: "m1",
        role: "user",
        content: "Hello",
        tool_calls: [],
        sources: [],
        model: null,
        latency_ms: null,
        created_at: "2026-01-01",
      },
    ];
    saveAuth({ token: "tok", user_id: "u", name: "A" });
    vi.stubGlobal("fetch", mockFetchResponse(msgs));

    const result = await fetchMessages("chat-123");

    expect(fetch).toHaveBeenCalledWith("/api/chats/chat-123/messages", {
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer tok",
      },
    });
    expect(result).toEqual(msgs);
  });
});

describe("generateTitle", () => {
  it("calls POST /api/chats/{chatId}/title with auth header", async () => {
    saveAuth({ token: "my-jwt", user_id: "u", name: "A" });
    const titleResp = { chat_id: "c1", title: "Production Deployment Guide" };
    vi.stubGlobal("fetch", mockFetchResponse(titleResp));

    const result = await generateTitle("c1");

    expect(fetch).toHaveBeenCalledWith("/api/chats/c1/title", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer my-jwt",
      },
    });
    expect(result).toEqual(titleResp);
  });

  it("throws on non-OK response", async () => {
    vi.stubGlobal("fetch", mockFetchResponse({}, 500));
    await expect(generateTitle("c1")).rejects.toThrow(
      "Title generation failed: 500"
    );
  });

  it("throws Unauthorized on 401", async () => {
    vi.stubGlobal("fetch", mockFetchResponse({}, 401));
    await expect(generateTitle("c1")).rejects.toThrow("Unauthorized");
  });
});

describe("sendMessageStream", () => {
  it("parses Vercel AI Data Stream Protocol tokens", async () => {
    const stream = new ReadableStream({
      start(controller) {
        const encoder = new TextEncoder();
        controller.enqueue(encoder.encode('0:"Hello "\n'));
        controller.enqueue(encoder.encode('0:"world"\n'));
        controller.enqueue(
          encoder.encode(
            '2:[{"chat_id":"c1","message_id":"m1","tool_calls":[],"sources":[]}]\n'
          )
        );
        controller.enqueue(encoder.encode('d:{"finishReason":"stop"}\n'));
        controller.close();
      },
    });

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        body: stream,
      })
    );

    const tokens: string[] = [];
    let doneData: unknown = null;

    await sendMessageStream(
      "Hi",
      null,
      (tok) => tokens.push(tok),
      (meta) => {
        doneData = meta;
      }
    );

    expect(tokens).toEqual(["Hello ", "world"]);
    expect(doneData).toEqual({
      chat_id: "c1",
      message_id: "m1",
      tool_calls: [],
      sources: [],
    });
  });

  it("throws on 401", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 401 })
    );

    await expect(
      sendMessageStream("Hi", null, vi.fn(), vi.fn())
    ).rejects.toThrow("Unauthorized");
  });
});
