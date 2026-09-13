import { api } from "./axios";

export interface MemoryItem {
  id: string;
  user_id?: string | null;
  content: string;
  source_session_id?: string | null;
  created_at: number;
  updated_at: number;
}

export async function listMemories(limit: number = 50): Promise<MemoryItem[]> {
  const res = await api.get<MemoryItem[]>("/memories", { params: { limit } });
  return res.data;
}

export async function deleteMemory(memoryId: string): Promise<void> {
  await api.delete(`/memories/${memoryId}`);
}

export async function clearAllMemories(): Promise<void> {
  await api.delete("/memories");
}
