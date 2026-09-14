export type AppMode = "chat";

export interface Citation {
  id?: string;
  chunk_id?: string;
  document_id?: string;
  filename: string;
  page_number?: number;
  page?: number;
  chunk_index?: number;
  chunk?: number;
  text?: string;
  snippet?: string;
  score?: number;
  source_type?: string;
  row_range?: string;
  table_context?: string;
  retrieval_method?: string;
  heading?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  createdAt: number;
  error?: boolean;
}

export interface SessionItem {
  id: string;
  title: string;
  mode: AppMode;
  selected_document_ids: string[];
  chat_number?: string;
  created_at: number;
  updated_at: number;
}

export interface ChatSession {
  id: string;
  title: string;
  mode?: AppMode;
  selected_document_ids?: string[];
  chat_number?: string;
  isTemporary?: boolean;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}

export interface ChatResponse {
  response: string;
  citations: Citation[];
  session_id?: string;
  chat_number?: string;
  chat_id?: string;
  mode?: string;
  intent?: string;
}

export interface DocumentItem {
  document_id: string;
  original_filename: string;
  filename?: string;
  mime_type: string;
  size_bytes: number;
  status: "pending" | "processing" | "ready" | "failed";
  page_count: number;
  chunk_count: number;
  chunks?: number;
  source_type: string;
  processing_error?: string;
  created_at: number;
  uploaded_at?: string;
}

export interface UploadResult {
  document_id: string;
  filename: string;
  chunks: number;
  page_count?: number;
  source_type?: string;
}

export interface AppSettings {
  model: string;
  memoryEnabled: boolean;
}

export interface MemoryItem {
  id: string;
  content: string;
  source_session_id?: string | null;
  created_at: number;
  updated_at: number;
}

export interface StorageUsage {
  used_bytes: number;
  limit_bytes: number;
  used_mb: number;
  limit_mb: number;
  usage_percent: number;
}

export interface SystemHealth {
  status: string;
  app_name?: string;
  gemini_model?: string;
  embedding_model?: string;
}

export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

