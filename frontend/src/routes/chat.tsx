import { useEffect, useRef, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { MessagesSquare, Plus, Sparkle } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ChatInput } from "@/components/chat/chat-input";
import { ChatMessage } from "@/components/chat/chat-message";
import { TypingIndicator } from "@/components/chat/typing-indicator";
import { EmptyState } from "@/components/common/empty-state";
import { useSessions } from "@/hooks/use-sessions";
import { sendChatMessage } from "@/services/chat";
import { toFriendlyError } from "@/services/axios";
import type { ChatMessage as ChatMessageType } from "@/types";

export const Route = createFileRoute("/chat")({
  head: () => ({
    meta: [
      { title: "Chat — Manan AI Assistant" },
      {
        name: "description",
        content:
          "Chat with Manan, a retrieval-augmented AI assistant that answers from your own PDF knowledge base with cited sources.",
      },
      { property: "og:title", content: "Chat — Manan AI Assistant" },
      {
        property: "og:description",
        content: "Ask questions and get cited answers from your indexed documents.",
      },
    ],
  }),
  component: ChatPage,
});

const SUGGESTIONS = [
  "Summarize the key points of my latest document",
  "What does the document say about error handling?",
  "Give me a table comparing the main concepts",
];

function ChatPage() {
  const { activeSession, activeId, appendMessage, newChat, hydrated } = useSessions();
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const messages = activeSession?.messages ?? [];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, loading]);

  const handleSend = async (text: string) => {
    if (!activeId) return;
    const userMessage: ChatMessageType = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      createdAt: Date.now(),
    };
    appendMessage(activeId, userMessage);
    setLoading(true);

    try {
      const response = await sendChatMessage(activeId,text,);
      appendMessage(activeId, {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.response  || "_No answer returned by the backend._",
        citations: response.citations,
        createdAt: Date.now(),
      });
    } catch (error) {
      const message = toFriendlyError(error);
      toast.error("Manan couldn't answer", { description: message });
      appendMessage(activeId, {
        id: crypto.randomUUID(),
        role: "assistant",
        content: message,
        createdAt: Date.now(),
        error: true,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <header className="grid shrink-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-4 border-b border-border px-4 py-3 sm:px-6">
        <div className="min-w-0">
          <h1 className="truncate text-base font-semibold">{activeSession?.title || "New chat"}</h1>
          <p className="truncate text-xs text-muted-foreground">
            {messages.length} message{messages.length === 1 ? "" : "s"} · grounded in your documents
          </p>
        </div>
        <Button variant="outline" className="rounded-xl" onClick={() => newChat()}>
          <Plus className="mr-2 h-4 w-4" /> New chat
        </Button>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto scroll-fade px-4 py-6 sm:px-6">
        <div className="mx-auto w-full max-w-3xl space-y-6">
          {hydrated && messages.length === 0 && !loading && (
            <div className="space-y-4 pt-8">
              <EmptyState
                icon={Sparkle}
                title="Ask Manan anything"
                description="Manan searches your uploaded PDFs, then answers with citations back to the exact chunks."
              />
              <div className="grid gap-2 sm:grid-cols-3">
                {SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => handleSend(suggestion)}
                    className="rounded-xl border border-border bg-card px-3 py-3 text-left text-sm text-muted-foreground transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:text-foreground hover:shadow-soft"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {!hydrated && (
            <div className="flex justify-center pt-16 text-muted-foreground">
              <MessagesSquare className="h-5 w-5 animate-pulse" />
            </div>
          )}

          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}
          {loading && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>
      </div>

      <ChatInput onSend={handleSend} loading={loading} />
    </div>
  );
}
