"use client";

import { FormEvent, useRef, useState } from "react";
import { ChatMessage, streamChat } from "@/lib/api";

export function ChatWindow() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const send = async (e: FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || busy) return;

    const history = messages;
    const userMessage: ChatMessage = { role: "user", content: text };
    setMessages([...history, userMessage, { role: "assistant", content: "" }]);
    setInput("");
    setBusy(true);

    try {
      await streamChat(text, history, (token) => {
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = {
            role: "assistant",
            content: next[next.length - 1].content + token,
          };
          return next;
        });
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
      });
    } catch (err) {
      const content =
        err instanceof TypeError
          ? "Could not reach the backend. Is it running?"
          : err instanceof Error
            ? err.message
            : "Something went wrong.";
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = { role: "assistant", content };
        return next;
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto p-6">
        {messages.length === 0 && (
          <p className="text-sm text-foreground/40">
            Upload a document, then ask a question about it.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <div
              className={
                "max-w-[75%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm " +
                (m.role === "user"
                  ? "bg-foreground text-background"
                  : "bg-foreground/5 text-foreground")
              }
            >
              {m.content || "…"}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={send} className="flex gap-2 border-t border-foreground/10 p-4">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask something about your documents…"
          className="flex-1 rounded-lg border border-foreground/15 bg-transparent px-3 py-2 text-sm outline-none focus:border-foreground/40"
          disabled={busy}
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="rounded-lg bg-foreground px-4 py-2 text-sm font-medium text-background disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </div>
  );
}
