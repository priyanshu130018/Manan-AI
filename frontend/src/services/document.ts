import { api, API_BASE_URL } from "./axios";
import type { DocumentItem, ApiResponse, StorageUsage } from "@/types";

export async function listDocuments(): Promise<DocumentItem[]> {
  const { data } = await api.get<ApiResponse<DocumentItem[]>>("/doc");
  return data.data;
}

export async function getDocument(documentId: string): Promise<DocumentItem> {
  const { data } = await api.get<ApiResponse<DocumentItem>>(`/doc/${documentId}`);
  return data.data;
}

export async function deleteDocument(documentId: string): Promise<void> {
  await api.delete(`/doc/${documentId}`);
}

export async function getStorageUsage(): Promise<StorageUsage> {
  const { data } = await api.get<ApiResponse<StorageUsage>>("/doc/storage");
  return data.data;
}

export function getDocumentFileUrl(documentId: string): string {
  const base = API_BASE_URL.replace(/\/+$/, "");
  return `${base}/doc/${documentId}/file`;
}
