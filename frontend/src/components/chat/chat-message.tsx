import { useState, useEffect } from "react";
import { Sparkle, User, Pencil, Copy, Check, RefreshCw, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Markdown } from "./markdown";
import { CompactSourcesDisplay } from "./citation-card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { ChatMessage as ChatMessageType } from "@/types";

interface ChatMessageProps {
  message: ChatMessageType;
  onEdit?: (messageId: string, newContent: string) => Promise<void> | void;
  onRegenerate?: (messageId: string) => Promise<void> | void;
  isReadOnly?: boolean;
  isLoading?: boolean;
}

export function ChatMessage({
  message,
  onEdit,
  onRegenerate,
  isReadOnly = false,
  isLoading = false,
}: ChatMessageProps) {
  const isUser = message.role === "user";
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  const [submittingEdit, setSubmittingEdit] = useState(false);
  const [copied, setCopied] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  useEffect(() => {
    if (!isEditing) {
      setEditContent(message.content);
    }
  }, [message.content, isEditing]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      toast.success("Copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy");
    }
  };

  const handleSaveEdit = async () => {
    if (!editContent.trim() || editContent.trim() === message.content) {
      setIsEditing(false);
      return;
    }
    if (!onEdit) return;

    setSubmittingEdit(true);
    try {
      await onEdit(message.id, editContent.trim());
      setIsEditing(false);
    } catch {
      // Error handled in parent
    } finally {
      setSubmittingEdit(false);
    }
  };

  const handleRegenerate = async () => {
    if (!onRegenerate || isLoading || regenerating) return;
    setRegenerating(true);
    try {
      await onRegenerate(message.id);
    } catch {
      // Error handled in parent
    } finally {
      setRegenerating(false);
    }
  };

  if (isUser) {
    return (
      <div className="group flex justify-end gap-3">
        <div className="flex max-w-[85%] flex-col items-end gap-1.5">
          {isEditing ? (
            <div className="w-full min-w-[280px] sm:min-w-[400px] space-y-2 rounded-2xl rounded-br-md border border-border bg-card p-3 shadow-soft">
              <Textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSaveEdit();
                  } else if (e.key === "Escape") {
                    setIsEditing(false);
                    setEditContent(message.content);
                  }
                }}
                rows={3}
                className="resize-none text-sm"
                placeholder="Edit your message..."
                autoFocus
              />
              <div className="flex items-center justify-end gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={submittingEdit}
                  onClick={() => {
                    setIsEditing(false);
                    setEditContent(message.content);
                  }}
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  disabled={submittingEdit || !editContent.trim()}
                  onClick={handleSaveEdit}
                  className="flex items-center gap-1.5"
                >
                  {submittingEdit && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Save & Submit
                </Button>
              </div>
            </div>
          ) : (
            <>
              <div className="rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap text-primary-foreground shadow-soft">
                {message.content}
              </div>
              {!isReadOnly && onEdit && (
                <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-6 w-6 text-muted-foreground hover:text-foreground"
                    onClick={() => {
                      setEditContent(message.content);
                      setIsEditing(true);
                    }}
                    title="Edit message"
                  >
                    <Pencil className="h-3 w-3" />
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-6 w-6 text-muted-foreground hover:text-foreground"
                    onClick={handleCopy}
                    title="Copy message"
                  >
                    {copied ? (
                      <Check className="h-3 w-3 text-emerald-500" />
                    ) : (
                      <Copy className="h-3 w-3" />
                    )}
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
        <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-secondary text-secondary-foreground">
          <User className="h-4 w-4" />
        </div>
      </div>
    );
  }

  return (
    <div className="group flex gap-3">
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
          <div className="pt-1">
            <CompactSourcesDisplay citations={message.citations} />
          </div>
        )}

        <div className="flex items-center gap-1.5 pt-0.5">
          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
            onClick={handleCopy}
          >
            {copied ? (
              <>
                <Check className="mr-1 h-3.5 w-3.5 text-emerald-500" />
                Copied
              </>
            ) : (
              <>
                <Copy className="mr-1 h-3.5 w-3.5" />
                Copy
              </>
            )}
          </Button>

          {!isReadOnly && onRegenerate && (
            <Button
              size="sm"
              variant="ghost"
              disabled={isLoading || regenerating}
              className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
              onClick={handleRegenerate}
            >
              {regenerating ? (
                <>
                  <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                  Regenerating...
                </>
              ) : (
                <>
                  <RefreshCw className="mr-1 h-3.5 w-3.5" />
                  Regenerate
                </>
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
