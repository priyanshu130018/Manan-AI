import { api } from "./axios";
import type { UploadResult, ApiResponse } from "@/types";

export async function uploadDocument(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);

  const { data } = await api.post<ApiResponse<UploadResult>>(
    "/documents/upload",
    form,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress: (event) => {
        if (!event.total || !onProgress) {
          return;
        }

        onProgress(
          Math.round((event.loaded / event.total) * 100),
        );
      },
    },
  );

  return data.data;
}