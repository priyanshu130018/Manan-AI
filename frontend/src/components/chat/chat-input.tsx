import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { ArrowUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { LoadingSpinner } from "@/components/common/loading-spinner";

export function ChatInput({
  onSend,
  loading,
}: {
  onSend: (value: string) => void;
  loading: boolean;
}) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!loading) ref.current?.focus();
  }, [loading]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value]);

  const submit = () => {
    const text = value.trim();
    if (!text || loading) return;
    onSend(text);
    setValue("");
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <div className="border-t border-border bg-background/80 px-4 py-4 backdrop-blur">
      <div className="mx-auto w-full max-w-3xl">
        <div className="flex items-end gap-2 rounded-2xl border border-border bg-card p-2 shadow-soft transition-shadow focus-within:border-primary/50 focus-within:shadow-lift">
          <Textarea
            ref={ref}
            rows={1}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask Manan anything about your documents…"
            aria-label="Message Manan"
            className="max-h-[200px] min-h-[44px] resize-none border-0 bg-transparent px-2 py-2.5 text-sm shadow-none focus-visible:ring-0 dark:bg-transparent"
          />
          <Button
            size="icon"
            onClick={submit}
            disabled={loading || !value.trim()}
            aria-label="Send message"
            className="h-9 w-9 shrink-0 rounded-xl"
          >
            {loading ? (
              <LoadingSpinner className="text-primary-foreground" />
            ) : (
              <ArrowUp className="h-4 w-4" />
            )}
          </Button>
        </div>
        <p className="mt-2 text-center text-xs text-muted-foreground">
          Enter to send · Shift + Enter for a new line
        </p>
      </div>
    </div>
  );
}
