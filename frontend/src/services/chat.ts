import { api, readSettings, MODEL_OPTIONS } from "./axios";
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
  const targetModel = modelOverride || currentSettings.model;
  const modelOpt = MODEL_OPTIONS.find((m) => m.value === targetModel);
  const targetProvider = providerOverride || modelOpt?.provider || currentSettings.provider;

  const payload: {
    session_id?: string | null;
    message: string;
    document_ids?: string[];
    selected_document_ids?: string[];
    provider?: string;
    model?: string;
    memory_enabled?: boolean;
  } = {
    message: message || "",
    provider: targetProvider,
    model: targetModel,
    memory_enabled:
      memoryEnabledOverride !== undefined ? memoryEnabledOverride : currentSettings.memoryEnabled,
  };

  if (sessionId && !sessionId.startsWith("draft-") && !sessionId.startsWith("temp-")) {
    payload.session_id = sessionId;
  }

  if (documentIds && documentIds.length > 0) {
    payload.document_ids = documentIds;
    payload.selected_document_ids = documentIds;
  }

  const { data } = await api.post<ApiResponse<ChatResponse>>("/chat", payload);
  return data.data;
}

export async function editChatMessage(
  messageId: string,
  content: string,
  model?: string,
  provider?: string,
): Promise<ChatResponse> {
  const currentSettings = readSettings();
  const targetModel = model || currentSettings.model;
  const modelOpt = MODEL_OPTIONS.find((m) => m.value === targetModel);
  const prov = provider || modelOpt?.provider || currentSettings.provider;
  const { data } = await api.patch<ApiResponse<ChatResponse>>(`/messages/${messageId}`, {
    content,
    model: targetModel,
    provider: prov,
  });
  return data.data;
}

export async function regenerateChatMessage(
  messageId: string,
  model?: string,
  provider?: string,
): Promise<ChatResponse> {
  const currentSettings = readSettings();
  const targetModel = model || currentSettings.model;
  const modelOpt = MODEL_OPTIONS.find((m) => m.value === targetModel);
  const prov = provider || modelOpt?.provider || currentSettings.provider;
  const { data } = await api.post<ApiResponse<ChatResponse>>(`/messages/${messageId}/regenerate`, {
    model: targetModel,
    provider: prov,
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

export interface AvailableModelItem {
  value: string;
  label: string;
  provider: "gemini" | "ollama";
}

export interface AvailableModelsData {
  gemini: {
    available: boolean;
    message: string;
    models: AvailableModelItem[];
  };
  ollama: {
    available: boolean;
    message: string;
    models: AvailableModelItem[];
  };
  default_model: string;
  default_provider: "gemini" | "ollama";
}

export async function fetchAvailableModels(): Promise<AvailableModelsData> {
  const { data } = await api.get<ApiResponse<AvailableModelsData>>("/llm/models");
  return data.data;
}
