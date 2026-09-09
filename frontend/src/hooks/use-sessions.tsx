import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { ChatMessage, ChatSession } from "@/types";

const KEY = "manan.sessions";

function createSession(): ChatSession {
  const now = Date.now();
  return {
    id: (globalThis.crypto?.randomUUID?.() ?? String(now)) as string,
    title: "New chat",
    messages: [],
    createdAt: now,
    updatedAt: now,
  };
}

interface SessionsContextValue {
  sessions: ChatSession[];
  activeId: string | null;
  activeSession: ChatSession | null;
  hydrated: boolean;
  newChat: () => string;
  selectSession: (id: string) => void;
  deleteSession: (id: string) => void;
  appendMessage: (sessionId: string, message: ChatMessage) => void;
  renameSession: (sessionId: string, title: string) => void;
}

const SessionsContext = createContext<SessionsContextValue | null>(null);

export function SessionsProvider({ children }: { children: ReactNode }) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    let initial: ChatSession[] = [];
    try {
      initial = JSON.parse(window.localStorage.getItem(KEY) ?? "[]") as ChatSession[];
    } catch {
      initial = [];
    }
    if (!Array.isArray(initial) || initial.length === 0) initial = [createSession()];
    setSessions(initial);
    setActiveId(initial[0].id);
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    window.localStorage.setItem(KEY, JSON.stringify(sessions));
  }, [sessions, hydrated]);

  const newChat = useCallback(() => {
    const session = createSession();
    setSessions((prev) => [session, ...prev]);
    setActiveId(session.id);
    return session.id;
  }, []);

  const deleteSession = useCallback((id: string) => {
    setSessions((prev) => {
      const next = prev.filter((s) => s.id !== id);
      const list = next.length ? next : [createSession()];
      setActiveId((current) => (current === id ? list[0].id : current));
      return list;
    });
  }, []);

  const appendMessage = useCallback((sessionId: string, message: ChatMessage) => {
    setSessions((prev) =>
      prev.map((session) => {
        if (session.id !== sessionId) return session;
        const isFirstUser = message.role === "user" && session.messages.length === 0;
        return {
          ...session,
          title: isFirstUser ? message.content.slice(0, 48) : session.title,
          messages: [...session.messages, message],
          updatedAt: Date.now(),
        };
      }),
    );
  }, []);

  const renameSession = useCallback((sessionId: string, title: string) => {
    setSessions((prev) => prev.map((s) => (s.id === sessionId ? { ...s, title } : s)));
  }, []);

  const value = useMemo<SessionsContextValue>(
    () => ({
      sessions,
      activeId,
      activeSession: sessions.find((s) => s.id === activeId) ?? null,
      hydrated,
      newChat,
      selectSession: setActiveId,
      deleteSession,
      appendMessage,
      renameSession,
    }),
    [sessions, activeId, hydrated, newChat, deleteSession, appendMessage, renameSession],
  );

  return <SessionsContext.Provider value={value}>{children}</SessionsContext.Provider>;
}

export function useSessions() {
  const ctx = useContext(SessionsContext);
  if (!ctx) throw new Error("useSessions must be used inside SessionsProvider");
  return ctx;
}
