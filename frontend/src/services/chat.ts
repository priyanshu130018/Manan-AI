import { api, readSettings } from "./axios";
import type { ChatResponse, ApiResponse, SystemHealth } from "@/types";
import type { SessionDetail } from "./session";

export async function sendChatMessage(
  sessionId?: string | null,
  message?: string,
  documentIds?: string[],
  modelOverride?: string,
  memoryEnabledOverride?: boolean,
  providerOverride?: string,
): Promise<ChatResponse> {
  const currentSettings = readSettings();
  const payload: {
    session_id?: string | null;
    message: string;
    document_ids?: string[];
    provider?: string;
    model?: string;
    memory_enabled?: boolean;
  } = {
    message: message || "",
    provider: providerOverride || currentSettings.provider,
    model: modelOverride || currentSettings.model,
    memory_enabled: memoryEnabledOverride !== undefined ? memoryEnabledOverride : currentSettings.memoryEnabled,
  };

  if (sessionId && !sessionId.startsWith("draft-") && !sessionId.startsWith("temp-")) {
    payload.session_id = sessionId;
  }

  if (documentIds && documentIds.length > 0) {
    payload.document_ids = documentIds;
  }

  const { data } = await api.post<ApiResponse<ChatResponse> | ChatResponse>("/chat", payload);
  const raw = data as any;
  if (raw && raw.data && typeof raw.data === "object" && "response" in raw.data) {
    return raw.data as ChatResponse;
  }
  return raw as ChatResponse;
}

export async function editChatMessage(
  messageId: string,
  content: string,
  model?: string,
  provider?: string,
): Promise<ChatResponse> {
  const { data } = await api.patch<ApiResponse<ChatResponse>>(`/messages/${messageId}`, {
    content,
    model,
    provider,
  });
  return data.data;
}

export async function regenerateChatMessage(
  messageId: string,
  model?: string,
  provider?: string,
): Promise<ChatResponse> {
  const { data } = await api.post<ApiResponse<ChatResponse>>(`/messages/${messageId}/regenerate`, {
    model,
    provider,
  });
  return data.data;
}

export async function getSharedChat(chatNumber: string): Promise<SessionDetail> {
  const { data } = await api.get<ApiResponse<SessionDetail>>(`/chat/${chatNumber}`);
  return data.data;
}

export async function getHealthInfo(): Promise<SystemHealth> {
  const { data } = await api.get<SystemHealth>("/health");
  return data;
}