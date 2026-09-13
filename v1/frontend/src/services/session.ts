import { api } from "./axios";
import type { SessionItem, ChatMessage, ApiResponse, AppMode } from "@/types";

export interface SessionDetail {
  id: string;
  title: string;
  mode: AppMode;
  selected_document_ids: string[];
  chat_number?: string;
  created_at: number;
  updated_at: number;
  messages: {
    id: string;
    session_id?: string;
    role: "user" | "assistant";
    content: string;
    citations: any[];
    created_at: number;
  }[];
  summary: string | null;
}

export async function listSessions(): Promise<SessionItem[]> {
  const { data } = await api.get<ApiResponse<SessionItem[]>>("/sessions");
  return data.data;
}

export async function createSession(options?: {
  id?: string;
  title?: string;
  mode?: AppMode;
  selectedDocumentIds?: string[];
  chatNumber?: string;
  messages?: ChatMessage[];
}): Promise<SessionItem> {
  const { data } = await api.post<ApiResponse<SessionItem>>("/sessions", {
    id: options?.id,
    title: options?.title || "New Chat",
    mode: options?.mode || "chat",
    selected_document_ids: options?.selectedDocumentIds || [],
    chat_number: options?.chatNumber,
    messages: options?.messages || [],
  });
  return data.data;
}

export async function getSession(sessionId: string): Promise<SessionDetail> {
  const { data } = await api.get<ApiResponse<SessionDetail>>(`/sessions/${sessionId}`);
  return data.data;
}

export async function getSessionByChatNumber(chatNumber: string): Promise<SessionDetail> {
  const { data } = await api.get<ApiResponse<SessionDetail>>(`/sessions/by-number/${chatNumber}`);
  return data.data;
}

export async function updateSession(
  sessionId: string,
  updates: {
    title?: string;
    mode?: AppMode;
    selected_document_ids?: string[];
  },
): Promise<SessionItem> {
  const { data } = await api.patch<ApiResponse<SessionItem>>(`/sessions/${sessionId}`, updates);
  return data.data;
}

export async function deleteSession(sessionId: string): Promise<void> {
  await api.delete(`/sessions/${sessionId}`);
}
