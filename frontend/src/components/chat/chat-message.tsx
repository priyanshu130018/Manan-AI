import { Sparkle, User } from "lucide-react";
import { Markdown } from "./markdown";
import { CitationCard } from "./citation-card";
import { cn } from "@/lib/utils";
import type { ChatMessage as ChatMessageType } from "@/types";

export function ChatMessage({ message }: { message: ChatMessageType }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end gap-3">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap text-primary-foreground shadow-soft">
          {message.content}
        </div>
        <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-secondary text-secondary-foreground">
          <User className="h-4 w-4" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-accent/15 text-accent">
        <Sparkle className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1 space-y-3">
        <div
          className={cn(
            "rounded-2xl rounded-tl-md border border-border bg-card px-4 py-3 shadow-soft",
            message.error && "border-destructive/40 bg-destructive/5 text-destructive",
          )}
        >
          <Markdown content={message.content} />
        </div>

        {message.citations && message.citations.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
              Sources
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              {message.citations.map((citation, i) => (
                <CitationCard
                  key={`${citation.filename}-${citation.chunk}-${i}`}
                  citation={citation}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
