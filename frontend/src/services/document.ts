import { api } from "./axios";
import type { DocumentItem, ApiResponse } from "@/types";

type RawDoc = Record<string, unknown>;

function normalize(raw: RawDoc, index: number): DocumentItem {
  return {
    document_id: String(raw.document_id ?? raw.id ?? raw.doc_id ?? index),
    filename: String(raw.filename ?? raw.file_name ?? raw.name ?? "Untitled.pdf"),
    chunks: Number(raw.chunks ?? raw.chunk_count ?? raw.num_chunks ?? 0),
    uploaded_at: (raw.uploaded_at ?? raw.created_at) as string | undefined,
  };
}

export async function listDocuments(): Promise<DocumentItem[]> {
  const { data } = await api.get<ApiResponse<DocumentItem[]>>(
    "/documents",
  );

  return data.data;
}

export async function deleteDocument(
  documentId: string,
): Promise<void> {
  await api.delete(`/documents/${documentId}`);
}
