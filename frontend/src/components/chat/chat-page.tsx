import { useEffect, useRef, useState } from "react";
import { useNavigate, Link } from "@tanstack/react-router";
import {
  Copy,
  Check,
  FileText,
  X,
  Clock,
  Loader2,
  MessageSquare,
  AlertCircle,
  Settings2,
  Sparkle,
  LogIn,
  UserPlus,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { ChatInput } from "@/components/chat/chat-input";
import { ChatMessage } from "@/components/chat/chat-message";
import { TypingIndicator } from "@/components/chat/typing-indicator";
import { DocumentSelector } from "@/components/chat/document-selector";
import { useAuth } from "@/hooks/use-auth";
import { useSessions } from "@/hooks/use-sessions";
import { sendChatMessage, editChatMessage, regenerateChatMessage } from "@/services/chat";
import { listDocuments } from "@/services/document";
import { uploadDocument } from "@/services/upload";
import { toFriendlyError } from "@/services/axios";
import { cn } from "@/lib/utils";
import type { ChatMessage as ChatMessageType, DocumentItem } from "@/types";

export function ChatPage({ chatNumberParam }: { chatNumberParam?: string }) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const {
    activeSession,
    activeId,
    isTemporary,
    toggleTemporaryMode,
    appendMessage,
    loadChatByNumber,
    newChat,
    createPersistentSessionFromDraft,
    refreshActiveSession,
    hydrated,
  } = useSessions();

  const [loading, setLoading] = useState(false);
  const [loadingSession, setLoadingSession] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [copiedId, setCopiedId] = useState(false);
  const [availableDocs, setAvailableDocs] = useState<DocumentItem[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [rateLimitCountdown, setRateLimitCountdown] = useState<number | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const messages = activeSession?.messages ?? [];
  const chatNumber = activeSession?.chat_number;

  // Rate limit countdown interval
  useEffect(() => {
    if (rateLimitCountdown === null || rateLimitCountdown <= 0) return;
    const timer = setInterval(() => {
      setRateLimitCountdown((prev) => {
        if (prev === null || prev <= 1) return null;
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [rateLimitCountdown]);

  // Load chat by chatNumberParam when accessing /chat/:chatNumber directly (supports shared chats)
  useEffect(() => {
    if (!chatNumberParam) {
      setNotFound(false);
      setLoadingSession(false);
      return;
    }

    if (!/^\d{10}$/.test(chatNumberParam)) {
      setNotFound(true);
      setLoadingSession(false);
      return;
    }

    if (activeSession?.chat_number === chatNumberParam && !activeSession?.isTemporary) {
      setNotFound(false);
      setLoadingSession(false);
      return;
    }

    let active = true;
    setLoadingSession(true);
    setNotFound(false);

    loadChatByNumber(chatNumberParam)
      .then((sess) => {
        if (!active) return;
        if (!sess) {
          setNotFound(true);
        } else {
          setNotFound(false);
        }
      })
      .catch(() => {
        if (active) setNotFound(true);
      })
      .finally(() => {
        if (active) setLoadingSession(false);
      });

    return () => {
      active = false;
    };
  }, [chatNumberParam, loadChatByNumber, activeSession?.chat_number, activeSession?.isTemporary]);

  const refreshDocuments = () => {
    if (!user) {
      setAvailableDocs([]);
      return;
    }
    listDocuments()
      .then((docs) => setAvailableDocs(docs || []))
      .catch(() => setAvailableDocs([]));
  };

  useEffect(() => {
    if (user) {
      refreshDocuments();
    } else {
      setAvailableDocs([]);
    }
  }, [user]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, loading]);

  const toggleDocSelection = (docId: string) => {
    if (!user) {
      navigate({ to: "/login", search: { redirect: "/chat" } });
      return;
    }
    setSelectedDocIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId],
    );
  };

  const handleSelectAllDocs = () => {
    if (!user) {
      navigate({ to: "/login", search: { redirect: "/chat" } });
      return;
    }
    setSelectedDocIds(availableDocs.map((d) => d.document_id));
  };

  const handleClearAllDocs = () => {
    setSelectedDocIds([]);
  };

  const handleCopyShareLink = () => {
    if (!chatNumber) return;
    const origin = typeof window !== "undefined" ? window.location.origin : "";
    const shareUrl = `${origin}/chat/${chatNumber}`;
    void navigator.clipboard.writeText(shareUrl);
    setCopiedId(true);
    toast.success("Chat link copied to clipboard");
    setTimeout(() => setCopiedId(false), 2000);
  };

  const handleToggleTemporary = () => {
    if (!user) {
      toast.info("Please log in to use Temporary Chat.");
      navigate({ to: "/login", search: { redirect: "/chat" } });
      return;
    }
    toggleTemporaryMode();
    if (chatNumberParam) {
      navigate({ to: "/chat" });
    }
  };

  const handleUploadFile = async (file: File) => {
    if (!user) {
      toast.info("Please log in to upload documents.");
      navigate({ to: "/login", search: { redirect: "/chat" } });
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      toast.error("File size exceeds 50 MB limit");
      return;
    }
    setUploading(true);
    try {
      await uploadDocument(file);
      toast.success(`Uploaded and indexed: ${file.name}`);
      refreshDocuments();
    } catch (err) {
      toast.error("Upload failed", { description: toFriendlyError(err) });
    } finally {
      setUploading(false);
    }
  };

  const handleSend = async (text: string) => {
    if (!user) {
      toast.info("Please sign in to start chatting.");
      navigate({ to: "/login", search: { redirect: "/" } });
      return;
    }

    const isDraft = !activeSession?.chat_number && !isTemporary;

    if (isDraft) {
      const userMessage: ChatMessageType = {
        id: crypto.randomUUID(),
        role: "user",
        content: text,
        createdAt: Date.now(),
      };
      appendMessage(activeSession?.id || "draft", userMessage);
      setLoading(true);

      try {
        const response = await sendChatMessage(
          null,
          text,
          selectedDocIds.length > 0 ? selectedDocIds : undefined,
        );

        const resChatNum = response?.chat_number || response?.chat_id;

        appendMessage(activeSession?.id || "draft", {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response?.response || "_No answer returned by the backend._",
          citations: response?.citations || [],
          createdAt: Date.now(),
        });


        if (resChatNum) {
          await loadChatByNumber(resChatNum);
          void navigate({
            to: "/chat/$chatNumber",
            params: { chatNumber: resChatNum },
            replace: true,
          });
        }
      } catch (error: any) {
        const message = toFriendlyError(error);
        if (error?.response?.status === 429 || error?.retryAfter) {
          const sec = error.retryAfter ? Math.round(error.retryAfter) : 30;
          setRateLimitCountdown(sec);
        }
        toast.error("AI service error", { description: message });
        appendMessage(activeSession?.id || "draft", {
          id: crypto.randomUUID(),
          role: "assistant",
          content: message,
          createdAt: Date.now(),
          error: true,
        });
      } finally {
        setLoading(false);
      }
      return;
    }

    const sessionId = activeId || activeSession?.id;
    if (!sessionId) return;

    const userMessage: ChatMessageType = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      createdAt: Date.now(),
    };
    appendMessage(sessionId, userMessage);
    setLoading(true);

    try {
      const response = await sendChatMessage(
        sessionId,
        text,
        selectedDocIds.length > 0 ? selectedDocIds : undefined,
      );
      appendMessage(sessionId, {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response?.response || "_No answer returned by the backend._",
        citations: response?.citations || [],
        createdAt: Date.now(),
      });

    } catch (error: any) {
      const message = toFriendlyError(error);
      if (error?.response?.status === 429 || error?.retryAfter) {
        const sec = error.retryAfter ? Math.round(error.retryAfter) : 30;
        setRateLimitCountdown(sec);
      }
      toast.error("AI service error", { description: message });
      appendMessage(sessionId, {
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

  const handleEditMessage = async (messageId: string, newContent: string) => {
    if (!user) return;
    setLoading(true);
    try {
      await editChatMessage(messageId, newContent);
      await refreshActiveSession();
      toast.success("Message updated.");
    } catch (err: any) {
      toast.error("Failed to edit message", { description: toFriendlyError(err) });
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerateMessage = async (messageId: string) => {
    if (!user) return;
    setLoading(true);
    try {
      await regenerateChatMessage(messageId);
      await refreshActiveSession();
      toast.success("Response regenerated.");
    } catch (err: any) {
      toast.error("Failed to regenerate response", { description: toFriendlyError(err) });
    } finally {
      setLoading(false);
    }
  };

  // If loading a shared session directly
  if (loadingSession) {
    return (
      <div className="flex h-full flex-col items-center justify-center bg-background p-6">
        <Loader2 className="mb-3 h-8 w-8 animate-spin text-primary" />
        <p className="font-mono text-sm text-muted-foreground">Loading conversation…</p>
      </div>
    );
  }

  // If chat not found (invalid or non-existent 10-digit number)
  if (notFound) {
    return (
      <div className="flex h-full flex-col items-center justify-center bg-background px-4 text-center">
        <div className="mb-4 grid h-12 w-12 place-items-center rounded-2xl bg-muted text-muted-foreground">
          <MessageSquare className="h-6 w-6" />
        </div>
        <h2 className="text-xl font-semibold text-foreground">Chat not found</h2>
        <p className="mt-2 max-w-sm text-sm text-muted-foreground">
          This conversation does not exist, may have expired, or access is unauthorized.
        </p>
        <Button
          className="mt-6 rounded-xl font-medium"
          onClick={() => {
            newChat(false);
            navigate({ to: "/chat" });
          }}
        >
          Start a new chat
        </Button>
      </div>
    );
  }

  return (
    <TooltipProvider delayDuration={150}>
      <div className="flex h-full flex-col bg-background">
        {/* Top Header */}
        <header className="flex shrink-0 items-center justify-between border-b border-border/70 px-4 py-2.5 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="truncate text-sm font-semibold text-foreground">
                  {user ? (activeSession?.title || "New conversation") : "Manan AI"}
                </h1>

                {/* Authenticated user: 10-Digit ID / Temporary Badge */}
                {user && !isTemporary && chatNumber ? (
                  <div className="flex items-center gap-1">
                    <span className="rounded-md bg-muted px-2 py-0.5 font-mono text-[11px] font-medium text-muted-foreground">
                      ID: {chatNumber}
                    </span>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={handleCopyShareLink}
                          className="h-6 w-6 text-muted-foreground hover:text-foreground"
                          aria-label="Copy chat share link"
                        >
                          {copiedId ? (
                            <Check className="h-3 w-3 text-emerald-500" />
                          ) : (
                            <Copy className="h-3 w-3" />
                          )}
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent side="bottom">Copy chat link</TooltipContent>
                    </Tooltip>
                  </div>
                ) : user && isTemporary ? (
                  <Badge
                    variant="secondary"
                    className="flex items-center gap-1 py-0.5 text-[11px] font-normal text-muted-foreground"
                  >
                    <Clock className="h-3 w-3" />
                    Temporary chat
                  </Badge>
                ) : null}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Unauthenticated: Top-Right Login / Sign Up Actions */}
            {!user ? (
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  className="rounded-xl text-xs font-medium"
                  asChild
                >
                  <Link to="/login" search={{ redirect: "/" }}>
                    <LogIn className="mr-1.5 h-3.5 w-3.5" /> Log in
                  </Link>
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  className="rounded-xl text-xs font-medium shadow-sm"
                  asChild
                >
                  <Link to="/signup" search={{ redirect: "/" }}>
                    <UserPlus className="mr-1.5 h-3.5 w-3.5" /> Sign up
                  </Link>
                </Button>
              </div>
            ) : (
              <>
                {/* Authenticated Controls */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      size="icon"
                      variant={isTemporary ? "secondary" : "ghost"}
                      onClick={handleToggleTemporary}
                      className={cn(
                        "h-8 w-8 rounded-xl transition-colors",
                        isTemporary
                          ? "bg-muted text-foreground ring-1 ring-border"
                          : "text-muted-foreground hover:text-foreground",
                      )}
                      aria-label={isTemporary ? "Disable temporary chat" : "Temporary chat"}
                    >
                      <Clock className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="bottom">
                    {isTemporary ? "Temporary chat is ON (unsaved)" : "Temporary chat"}
                  </TooltipContent>
                </Tooltip>

                <DocumentSelector
                  documents={availableDocs}
                  selectedDocIds={selectedDocIds}
                  onToggleDoc={toggleDocSelection}
                  onSelectAll={handleSelectAllDocs}
                  onClearAll={handleClearAllDocs}
                />
              </>
            )}
          </div>
        </header>

        {/* Selected documents pill banner (Document Reference mode) */}
        {user && selectedDocIds.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 border-b border-border/50 bg-muted/20 px-4 py-1.5 text-xs sm:px-6">
            <span className="text-[11px] font-medium text-muted-foreground">Using:</span>
            {selectedDocIds.map((id) => {
              const doc = availableDocs.find((d) => d.document_id === id);
              return (
                <Badge
                  key={id}
                  variant="secondary"
                  className="flex items-center gap-1 rounded-md py-0.5 text-[11px] font-normal"
                >
                  <FileText className="h-3 w-3 text-muted-foreground" />
                  <span className="max-w-[180px] truncate">
                    {doc?.original_filename || doc?.filename || id}
                  </span>
                  <button
                    type="button"
                    onClick={() => toggleDocSelection(id)}
                    className="text-muted-foreground hover:text-foreground"
                    aria-label="Remove document reference"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              );
            })}
            <button
              type="button"
              onClick={handleClearAllDocs}
              className="ml-auto text-[11px] text-muted-foreground hover:underline"
            >
              Clear (general chat)
            </button>
          </div>
        )}

        {/* 429 Active Rate Limit Countdown Banner */}
        {rateLimitCountdown !== null && rateLimitCountdown > 0 && (
          <div className="flex items-center justify-between border-b border-amber-500/30 bg-amber-500/10 px-4 py-2 text-xs text-amber-900 dark:text-amber-200 sm:px-6">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
              <span>
                AI rate limit reached. Retrying available in <strong>{rateLimitCountdown}s</strong>.
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="h-7 text-xs border-amber-500/40 hover:bg-amber-500/20"
                asChild
              >
                <Link to="/settings">
                  <Settings2 className="mr-1 h-3.5 w-3.5" /> Switch Model
                </Link>
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-amber-900 dark:text-amber-200 hover:bg-amber-500/20"
                onClick={() => setRateLimitCountdown(null)}
                aria-label="Dismiss alert"
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        )}

        {/* Center Chat Content */}
        <div className="min-h-0 flex-1 overflow-y-auto scroll-fade px-4 py-6 sm:px-6">
          <div className="mx-auto w-full max-w-3xl space-y-6">
            {/* Welcome Landing when conversation is empty */}
            {hydrated && messages.length === 0 && !loading && (
              <div className="flex min-h-[50vh] flex-col items-center justify-center text-center">
                <div className="mb-4 grid h-14 w-14 place-items-center rounded-3xl bg-primary/10 text-primary">
                  <Sparkle className="h-7 w-7" />
                </div>
                <h2 className="text-2xl font-semibold tracking-tight text-foreground/90 sm:text-3xl">
                  Ask anything you want to learn.
                </h2>
                {!user && (
                  <p className="mt-2 max-w-md text-sm text-muted-foreground">
                    Sign in to chat with AI, upload and study your documents with page citations, and preserve your learning history.
                  </p>
                )}
              </div>
            )}

            {/* Messages */}
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                onEdit={handleEditMessage}
                onRegenerate={handleRegenerateMessage}
                isReadOnly={!user || isTemporary}
                isLoading={loading}
              />
            ))}

            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Fixed Bottom Chat Input */}
        <div className="border-t border-border/70 bg-background/95 pb-2 pt-1">
          <div className="mx-auto w-full max-w-3xl">
            <ChatInput
              onSend={handleSend}
              loading={loading}
              uploading={uploading}
              onUploadFile={handleUploadFile}
              disabled={!user}
              onDisabledClick={() => {
                toast.info("Please sign in to start chatting.");
                navigate({ to: "/login", search: { redirect: "/" } });
              }}
              placeholder={
                !user
                  ? "Sign in to start chatting"
                  : selectedDocIds.length > 0
                  ? "Ask anything about selected notes..."
                  : "Ask anything…"
              }
            />
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
}
