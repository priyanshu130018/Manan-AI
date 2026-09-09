export interface Citation {
  filename: string;
  chunk: number;
  text?: string;
  score?: number;
  document_id?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  createdAt: number;
  error?: boolean;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}

export interface ChatResponse {
  response: string;
  citations: Citation[];
  session_id?: string;
}

export interface DocumentItem {
  document_id: string;
  filename: string;
  chunks: number;
  uploaded_at?: string;
}

export interface UploadResult {
  document_id: string;
  filename: string;
  chunks: number;
}

export interface AppSettings {
  backendUrl: string;
  modelName: string;
}

export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
}
