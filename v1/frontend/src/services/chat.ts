import { api } from "./axios";
import type { ChatResponse, ApiResponse, SystemHealth } from "@/types";

export async function sendChatMessage(
  sessionId: string,
  message: string,
  documentIds?: string[],
  isTemporary?: boolean,
  history?: Array<{ role: string; content: string }>,
  chatNumber?: string,
): Promise<ChatResponse> {
  const payload: {
    session_id: string;
    message: string;
    selected_document_ids?: string[];
    is_temporary?: boolean;
    history?: Array<{ role: string; content: string }>;
    chat_number?: string;
  } = {
    session_id: sessionId,
    message,
    is_temporary: isTemporary,
    history,
    chat_number: chatNumber,
  };

  if (documentIds && documentIds.length > 0) {
    payload.selected_document_ids = documentIds;
  }

  const { data } = await api.post<ApiResponse<ChatResponse>>("/chat", payload);
  return data.data;
}

export async function getHealthInfo(): Promise<SystemHealth> {
  const { data } = await api.get<SystemHealth>("/health");
  return data;
}
