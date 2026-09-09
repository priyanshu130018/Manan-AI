import { api } from "./axios";
import type { ChatResponse, Citation, ApiResponse } from "@/types";

type RawCitation = {
  filename?: string;
  file_name?: string;
  source?: string;
  chunk?: number;
  chunk_index?: number;
  chunk_id?: number;
  text?: string;
  content?: string;
  score?: number;
  document_id?: string;
};

function normalizeCitation(raw: RawCitation, index: number): Citation {
  return {
    filename: raw.filename ?? raw.file_name ?? raw.source ?? "Unknown document",
    chunk: raw.chunk ?? raw.chunk_index ?? raw.chunk_id ?? index + 1,
    text: raw.text ?? raw.content,
    score: raw.score,
    document_id: raw.document_id,
  };
}


export async function sendChatMessage(
  sessionId: string,
  message: string,
): Promise<ChatResponse> {
  const { data } = await api.post<ApiResponse<ChatResponse>>(
    "/chat",
    {
      session_id: sessionId,
      message,
    },
  );

  return data.data;
}