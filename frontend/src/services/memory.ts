import { api } from "./axios";
import type { ApiResponse } from "@/types";

export interface MemoryItem {
  id: string;
  user_id?: string | null;
  content: string;
  source_session_id?: string | null;
  created_at: string | number;
  updated_at: string | number;
}

export async function listMemories(limit: number = 50): Promise<MemoryItem[]> {
  const { data } = await api.get<ApiResponse<MemoryItem[]>>("/memories", { params: { limit } });
  return data.data;
}

export async function createMemory(
  content: string,
  sourceSessionId?: string | null,
): Promise<MemoryItem> {
  const { data } = await api.post<ApiResponse<MemoryItem>>("/memories", {
    content,
    source_session_id: sourceSessionId,
  });
  return data.data;
}

export async function updateMemory(memoryId: string, content: string): Promise<MemoryItem> {
  const { data } = await api.patch<ApiResponse<MemoryItem>>(`/memories/${memoryId}`, {
    content,
  });
  return data.data;
}

export async function deleteMemory(memoryId: string): Promise<void> {
  await api.delete(`/memories/${memoryId}`);
}

export async function clearAllMemories(): Promise<void> {
  await api.delete("/memories");
}
