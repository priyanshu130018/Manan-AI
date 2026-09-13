import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import {
  CheckCircle2,
  FileText,
  XCircle,
  HardDrive,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import { UploadZone } from "@/components/upload/upload-zone";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { toFriendlyError } from "@/services/axios";
import { uploadDocument } from "@/services/upload";
import { getStorageUsage } from "@/services/document";
import type { UploadResult, StorageUsage } from "@/types";

export const Route = createFileRoute("/upload")({
  head: () => ({
    meta: [
      { title: "Upload Documents — Manan AI" },
      {
        name: "description",
        content:
          "Upload study materials (PDF, CSV, JSON, SQL, DOCX, PPTX, TXT, Images) with real-time staged indexing progress.",
      },
    ],
  }),
  component: UploadPage,
});

type UploadStage =
  | "uploading"
  | "extracting"
  | "chunking"
  | "indexing"
  | "success"
  | "error";

interface UploadRow extends UploadResult {
  status: UploadStage;
  progress: number;
  stageText: string;
  sizeBytes: number;
  message?: string;
}

const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024; // 50 MB

function UploadPage() {
  const [rows, setRows] = useState<UploadRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [storage, setStorage] = useState<StorageUsage | null>(null);

  const loadStorage = () => {
    getStorageUsage()
      .then(setStorage)
      .catch(() => setStorage(null));
  };

  useEffect(() => {
    loadStorage();
  }, []);

  const handleFiles = async (files: File[]) => {
    const validExtensions = [
      ".pdf",
      ".docx",
      ".doc",
      ".pptx",
      ".ppt",
      ".txt",
      ".md",
      ".csv",
      ".json",
      ".sql",
      ".png",
      ".jpg",
      ".jpeg",
      ".webp",
    ];

    const validFiles: File[] = [];

    for (const file of files) {
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      if (!validExtensions.includes(ext)) {
        toast.error(`Unsupported format: ${file.name}`, {
          description: "Supported formats: PDF (with OCR), CSV, JSON, SQL, DOCX, PPTX, TXT, Images.",
        });
        continue;
      }

      if (file.size > MAX_FILE_SIZE_BYTES) {
        toast.error(`File too large: ${file.name}`, {
          description: `Maximum allowed file size is 50 MB. This file is ${(file.size / (1024 * 1024)).toFixed(1)} MB.`,
        });
        continue;
      }

      validFiles.push(file);
    }

    if (!validFiles.length) return;

    setBusy(true);
    for (const file of validFiles) {
      const key = crypto.randomUUID();
      setRows((prev) => [
        {
          document_id: key,
          filename: file.name,
          chunks: 0,
          sizeBytes: file.size,
          status: "uploading",
          progress: 10,
          stageText: "Uploading file to server...",
        },
        ...prev,
      ]);

      try {
        const result = await uploadDocument(file, (uploadPercent) => {
          setRows((prev) =>
            prev.map((row) => {
              if (row.document_id !== key) return row;
              if (uploadPercent < 100) {
                return {
                  ...row,
                  progress: Math.max(10, Math.round(uploadPercent * 0.4)),
                  stageText: `Uploading… ${uploadPercent}%`,
                };
              }
              return {
                ...row,
                progress: 60,
                status: "extracting",
                stageText: "Extracting text & running OCR (if needed)...",
              };
            }),
          );
        });

        // Pipeline completed
        setRows((prev) =>
          prev.map((row) =>
            row.document_id === key
              ? {
                  ...row,
                  ...result,
                  status: "success",
                  progress: 100,
                  stageText: "✓ Successfully uploaded and indexed",
                }
              : row,
          ),
        );

        toast.success(`'${result.filename}' indexed successfully`, {
          description: `${result.chunks} chunks stored in ChromaDB & PostgreSQL.`,
        });
        loadStorage();
      } catch (error) {
        const message = toFriendlyError(error);
        setRows((prev) =>
          prev.map((row) =>
            row.document_id === key
              ? {
                  ...row,
                  status: "error",
                  progress: 100,
                  stageText: "✕ Upload failed",
                  message,
                }
              : row,
          ),
        );
        toast.error(`Processing failed: ${file.name}`, { description: message });
      }
    }
    setBusy(false);
  };

  const formatSize = (bytes: number) => {
    if (!bytes) return "0 B";
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="h-full overflow-y-auto scroll-fade px-4 py-8 sm:px-8">
      <div className="mx-auto w-full max-w-3xl space-y-8">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">Upload Documents</h1>
            <p className="text-sm text-muted-foreground">
              Add study materials for RAG retrieval. Files are chunked and embedded in ChromaDB.
            </p>
          </div>
          <Button asChild variant="outline" className="rounded-xl">
            <Link to="/documents">View All Documents</Link>
          </Button>
        </header>

        {/* Storage Capacity Overview */}
        {storage && (
          <div className="rounded-2xl border border-border bg-card p-4 shadow-soft">
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 font-medium text-foreground">
                <HardDrive className="h-4 w-4 text-primary" /> Storage Usage
              </span>
              <span className="font-mono text-muted-foreground">
                {storage.used_mb} MB / {storage.limit_mb} MB ({storage.usage_percent}%)
              </span>
            </div>
            <Progress value={storage.usage_percent} className="mt-2.5 h-2" />
          </div>
        )}

        {/* Upload Drop Zone */}
        <UploadZone onFiles={handleFiles} disabled={busy} />

        {/* Upload Progress Rows */}
        {rows.length > 0 && (
          <section className="space-y-3">
            <h2 className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
              Upload Activity & Pipeline Status
            </h2>
            <div className="space-y-2.5">
              {rows.map((row) => (
                <div
                  key={row.document_id}
                  className="rounded-2xl border border-border bg-card p-4 shadow-soft transition-all"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
                      {row.status === "uploading" ||
                      row.status === "extracting" ||
                      row.status === "chunking" ||
                      row.status === "indexing" ? (
                        <Loader2 className="h-5 w-5 animate-spin" />
                      ) : (
                        <FileText className="h-5 w-5" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <p className="truncate text-sm font-medium">{row.filename}</p>
                        <span className="shrink-0 text-xs text-muted-foreground font-mono">
                          {formatSize(row.sizeBytes)}
                        </span>
                      </div>
                      <p className="mt-0.5 truncate text-xs text-muted-foreground">
                        {row.status === "success" && (
                          <span className="text-emerald-600 dark:text-emerald-400">
                            {row.stageText} · {row.chunks} chunks
                          </span>
                        )}
                        {row.status === "error" && (
                          <span className="text-destructive font-medium">
                            {row.stageText}: {row.message}
                          </span>
                        )}
                        {row.status !== "success" &&
                          row.status !== "error" &&
                          row.stageText}
                      </p>
                    </div>
                    {row.status === "success" && (
                      <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500" />
                    )}
                    {row.status === "error" && (
                      <XCircle className="h-5 w-5 shrink-0 text-destructive" />
                    )}
                  </div>
                  {row.status !== "success" && row.status !== "error" && (
                    <Progress value={row.progress} className="mt-3 h-1.5" />
                  )}
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
