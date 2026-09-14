import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { ChatMessage, ChatSession, SessionItem } from "@/types";
import {
  listSessions,
  createSession as createSessionApi,
  getSession as getSessionApi,
  getSessionByChatNumber as getSessionByChatNumberApi,
  updateSession as updateSessionApi,
  deleteSession as deleteSessionApi,
  type SessionDetail,
} from "@/services/session";
import { getSharedChat } from "@/services/chat";
import { useAuth } from "@/hooks/use-auth";

function createDraftSession(isTemporary = false): ChatSession {
  const now = Date.now();
  return {
    id: isTemporary
      ? "temp-" + Math.random().toString(36).substring(2, 10)
      : "draft-" + Math.random().toString(36).substring(2, 10),
    title: isTemporary ? "Temporary chat" : "New chat",
    isTemporary,
    messages: [],
    createdAt: now,
    updatedAt: now,
  };
}

interface SessionsContextValue {
  sessions: SessionItem[];
  activeId: string | null;
  activeSession: ChatSession | null;
  isTemporary: boolean;
  hydrated: boolean;
  deletingId: string | null;
  newChat: (isTemporary?: boolean) => void;
  toggleTemporaryMode: () => void;
  selectSession: (id: string) => Promise<void>;
  loadChatByNumber: (chatNumber: string) => Promise<ChatSession | null>;
  deleteSession: (id: string) => Promise<void>;
  appendMessage: (sessionId: string, message: ChatMessage) => void;
  renameSession: (sessionId: string, title: string) => Promise<void>;
  refreshActiveSession: () => Promise<void>;
  createPersistentSessionFromDraft: (
    firstPrompt: string,
    selectedDocIds?: string[],
  ) => Promise<SessionItem | null>;
  clearLocalState: () => void;
}

const SessionsContext = createContext<SessionsContextValue | null>(null);

export function SessionsProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [activeSession, setActiveSession] = useState<ChatSession | null>(() => createDraftSession(false));
  const [activeId, setActiveId] = useState<string | null>(activeSession?.id ?? null);
  const [hydrated, setHydrated] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const clearLocalState = useCallback(() => {
    const draft = createDraftSession(false);
    setSessions([]);
    setActiveSession(draft);
    setActiveId(draft.id);
  }, []);

  // Load persisted sessions from backend only when user is authenticated
  const refreshSessions = useCallback(async () => {
    if (!user) {
      setSessions([]);
      setHydrated(true);
      return;
    }
    try {
      const remote = await listSessions();
      setSessions(remote || []);
    } catch {
      setSessions([]);
    } finally {
      setHydrated(true);
    }
  }, [user]);

  useEffect(() => {
    if (user) {
      void refreshSessions();
    } else {
      clearLocalState();
      setHydrated(true);
    }
  }, [user, refreshSessions, clearLocalState]);

  const newChat = useCallback((isTemporary = false) => {
    const draft = createDraftSession(isTemporary);
    setActiveSession(draft);
    setActiveId(draft.id);
  }, []);

  const toggleTemporaryMode = useCallback(() => {
    setActiveSession((current) => {
      const nextIsTemporary = !current?.isTemporary;
      const draft = createDraftSession(nextIsTemporary);
      setActiveId(draft.id);
      return draft;
    });
  }, []);

  const selectSession = useCallback(async (id: string) => {
    if (!user) return;
    try {
      const detail = await getSessionApi(id);
      const chatSess: ChatSession = {
        id: detail.id,
        title: detail.title,
        mode: detail.mode,
        selected_document_ids: detail.selected_document_ids,
        chat_number: detail.chat_number,
        isTemporary: false,
        messages: (detail.messages || []).map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          citations: m.citations,
          createdAt: m.created_at,
        })),
        createdAt: detail.created_at,
        updatedAt: detail.updated_at,
      };
      setActiveSession(chatSess);
      setActiveId(id);
    } catch {
      setActiveId(id);
    }
  }, [user]);

  const loadChatByNumber = useCallback(async (chatNumber: string): Promise<ChatSession | null> => {
    try {
      let detail: SessionDetail;
      if (user) {
        try {
          detail = await getSessionByChatNumberApi(chatNumber);
        } catch {
          detail = await getSharedChat(chatNumber);
        }
      } else {
        detail = await getSharedChat(chatNumber);
      }
      const chatSess: ChatSession = {
        id: detail.id,
        title: detail.title,
        mode: detail.mode,
        selected_document_ids: detail.selected_document_ids,
        chat_number: detail.chat_number,
        isTemporary: false,
        messages: (detail.messages || []).map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          citations: m.citations,
          createdAt: m.created_at,
        })),
        createdAt: detail.created_at,
        updatedAt: detail.updated_at,
      };
      setActiveSession(chatSess);
      setActiveId(detail.id);

      if (user) {
        setSessions((prev) => {
          if (prev.some((s) => s.id === detail.id)) return prev;
          return [
            {
              id: detail.id,
              title: detail.title,
              mode: detail.mode,
              selected_document_ids: detail.selected_document_ids,
              chat_number: detail.chat_number,
              created_at: detail.created_at,
              updated_at: detail.updated_at,
            },
            ...prev,
          ];
        });
      }

      return chatSess;
    } catch (err) {
      console.error("Failed to load chat by number:", err);
      return null;
    }
  }, [user]);

  const refreshActiveSession = useCallback(async () => {
    if (!activeId || !user) return;
    try {
      await selectSession(activeId);
    } catch (err) {
      console.error("Failed to refresh active session:", err);
    }
  }, [activeId, user, selectSession]);

  const deleteSession = useCallback(
    async (id: string) => {
      if (!user) return;
      setDeletingId(id);
      try {
        await deleteSessionApi(id);
      } catch {
        // Ignored
      } finally {
        setSessions((prev) => prev.filter((s) => s.id !== id));
        if (activeId === id) {
          newChat(false);
        }
        setDeletingId(null);
      }
    },
    [user, activeId, newChat],
  );

  const appendMessage = useCallback((sessionId: string, message: ChatMessage) => {
    setActiveSession((current) => {
      if (!current) return current;
      const isFirstUser = message.role === "user" && current.messages.length === 0;
      const newTitle = isFirstUser ? message.content.slice(0, 48) : current.title;
      return {
        ...current,
        title: newTitle,
        messages: [...current.messages, message],
        updatedAt: Date.now(),
      };
    });
  }, []);

  const createPersistentSessionFromDraft = useCallback(
    async (firstPrompt: string, selectedDocIds: string[] = []): Promise<SessionItem | null> => {
      if (!user) return null;
      try {
        const title = firstPrompt.slice(0, 48).trim() || "New chat";
        const saved = await createSessionApi({
          title,
          mode: "chat",
          selectedDocumentIds: selectedDocIds,
        });

        setActiveSession((current) => {
          if (!current) return current;
          return {
            ...current,
            id: saved.id,
            chat_number: saved.chat_number,
            isTemporary: false,
            title: saved.title,
          };
        });
        setActiveId(saved.id);
        setSessions((prev) => [saved, ...prev.filter((s) => s.id !== saved.id)]);
        return saved;
      } catch (err) {
        console.error("Failed to create persistent session from draft:", err);
        return null;
      }
    },
    [user],
  );

  const renameSession = useCallback(async (sessionId: string, title: string) => {
    if (!user) return;
    try {
      await updateSessionApi(sessionId, { title });
    } catch {
      // Ignore
    }
    setSessions((prev) => prev.map((s) => (s.id === sessionId ? { ...s, title } : s)));
    setActiveSession((cur) => (cur?.id === sessionId ? { ...cur, title } : cur));
  }, [user]);

  const value = useMemo<SessionsContextValue>(
    () => ({
      sessions,
      activeId,
      activeSession,
      isTemporary: Boolean(activeSession?.isTemporary),
      hydrated,
      deletingId,
      newChat,
      toggleTemporaryMode,
      selectSession,
      loadChatByNumber,
      deleteSession,
      appendMessage,
      renameSession,
      refreshActiveSession,
      createPersistentSessionFromDraft,
      clearLocalState,
    }),
    [
      sessions,
      activeId,
      activeSession,
      hydrated,
      deletingId,
      newChat,
      toggleTemporaryMode,
      selectSession,
      loadChatByNumber,
      deleteSession,
      appendMessage,
      renameSession,
      refreshActiveSession,
      createPersistentSessionFromDraft,
      clearLocalState,
    ],
  );

  return <SessionsContext.Provider value={value}>{children}</SessionsContext.Provider>;
}

export function useSessions() {
  const ctx = useContext(SessionsContext);
  if (!ctx) throw new Error("useSessions must be used inside SessionsProvider");
  return ctx;
}
