import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  RefreshCw,
  Upload,
  FileText,
  HardDrive,
  ExternalLink,
  CheckCircle2,
  XCircle,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { DocumentTable } from "@/components/documents/document-table";
import { DeleteDialog } from "@/components/documents/delete-dialog";
import { UploadZone } from "@/components/upload/upload-zone";
import {
  deleteDocument,
  listDocuments,
  getStorageUsage,
  getDocumentFileUrl,
} from "@/services/document";
import { uploadDocument } from "@/services/upload";
import { toFriendlyError } from "@/services/axios";
import type { DocumentItem, StorageUsage, UploadResult } from "@/types";

export const Route = createFileRoute("/documents")({
  head: () => ({
    meta: [
      { title: "Documents — Manan AI" },
      {
        name: "description",
        content:
          "Browse, inspect, and manage documents indexed in Manan's RAG knowledge base.",
      },
    ],
  }),
  component: DocumentsPage,
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

function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [target, setTarget] = useState<DocumentItem | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null);
  const [storage, setStorage] = useState<StorageUsage | null>(null);

  // In-page upload modal state
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [uploadRows, setUploadRows] = useState<UploadRow[]>([]);
  const [uploadBusy, setUploadBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [docs, storageData] = await Promise.all([
        listDocuments(),
        getStorageUsage().catch(() => null),
      ]);
      setDocuments(docs || []);
      setStorage(storageData);
    } catch (error) {
      setDocuments([]);
      toast.error("Couldn't load documents", { description: toFriendlyError(error) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const handleUploadFiles = async (files: File[]) => {
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

    setUploadBusy(true);
    for (const file of validFiles) {
      const key = crypto.randomUUID();
      setUploadRows((prev) => [
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
          setUploadRows((prev) =>
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
        setUploadRows((prev) =>
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
        void load();
      } catch (error) {
        const message = toFriendlyError(error);
        setUploadRows((prev) =>
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
    setUploadBusy(false);
  };

  const confirmDelete = async () => {
    if (!target) return;
    const doc = target;
    setTarget(null);
    try {
      await deleteDocument(doc.document_id);
      setDocuments((prev) => prev.filter((d) => d.document_id !== doc.document_id));
      toast.success(`${doc.original_filename || doc.filename} deleted`);
      void getStorageUsage().then(setStorage).catch(() => {});
    } catch (error) {
      toast.error("Delete failed", { description: toFriendlyError(error) });
    }
  };

  const formatSize = (bytes: number) => {
    if (!bytes) return "0 B";
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (timestamp: number) => {
    if (!timestamp) return "Unknown";
    return new Date(timestamp * 1000).toLocaleString();
  };

  return (
    <div className="h-full overflow-y-auto scroll-fade px-4 py-8 sm:px-8">
      <div className="mx-auto w-full max-w-5xl space-y-6">
        {/* Header with Title and Upload button */}
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-2xl font-semibold tracking-tight">Documents</h1>
            <p className="text-sm text-muted-foreground">
              {documents.length} indexed document{documents.length === 1 ? "" : "s"} in knowledge
              base
            </p>
          </div>
          <div className="flex items-center gap-2.5">
            <Button variant="outline" className="rounded-xl" onClick={() => void load()}>
              <RefreshCw className="mr-2 h-4 w-4" /> Refresh
            </Button>
            <Button className="rounded-xl" onClick={() => setIsUploadOpen(true)}>
              <Upload className="mr-2 h-4 w-4" /> + Upload Document
            </Button>
          </div>
        </header>

        {/* Storage Capacity Bar */}
        {storage && (
          <div className="rounded-2xl border border-border bg-card p-4 shadow-soft">
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 font-medium text-foreground">
                <HardDrive className="h-4 w-4 text-primary" /> Total Storage Capacity
              </span>
              <span className="font-mono text-muted-foreground">
                {storage.used_mb} MB / {storage.limit_mb} MB ({storage.usage_percent}%)
              </span>
            </div>
            <Progress value={storage.usage_percent} className="mt-2.5 h-2" />
          </div>
        )}

        {/* Document Table */}
        <DocumentTable
          documents={documents}
          loading={loading}
          onSelect={setSelectedDoc}
          onDelete={setTarget}
          emptyAction={
            <Button className="rounded-xl" onClick={() => setIsUploadOpen(true)}>
              <Upload className="mr-2 h-4 w-4" /> Upload Document
            </Button>
          }
        />
      </div>

      {/* In-Page Upload Modal Dialog */}
      <Dialog open={isUploadOpen} onOpenChange={setIsUploadOpen}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Upload Documents</DialogTitle>
            <DialogDescription>
              Add study materials for RAG retrieval. Files are chunked and embedded in ChromaDB.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <UploadZone onFiles={handleUploadFiles} disabled={uploadBusy} />

            {uploadRows.length > 0 && (
              <div className="space-y-2.5">
                <h4 className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
                  Upload Activity & Pipeline Status
                </h4>
                {uploadRows.map((row) => (
                  <div
                    key={row.document_id}
                    className="rounded-2xl border border-border bg-card p-3.5 shadow-soft transition-all"
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
                        {row.status === "uploading" ||
                        row.status === "extracting" ||
                        row.status === "chunking" ||
                        row.status === "indexing" ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <FileText className="h-4 w-4" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <p className="truncate text-xs font-medium">{row.filename}</p>
                          <span className="shrink-0 text-[11px] text-muted-foreground font-mono">
                            {formatSize(row.sizeBytes)}
                          </span>
                        </div>
                        <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
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
                        <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
                      )}
                      {row.status === "error" && (
                        <XCircle className="h-4 w-4 shrink-0 text-destructive" />
                      )}
                    </div>
                    {row.status !== "success" && row.status !== "error" && (
                      <Progress value={row.progress} className="mt-2.5 h-1.5" />
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setIsUploadOpen(false);
                setUploadRows([]);
              }}
            >
              Done
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Document Detail & Viewer Dialog */}
      <Dialog open={Boolean(selectedDoc)} onOpenChange={(open) => !open && setSelectedDoc(null)}>
        <DialogContent className="max-w-xl">
          {selectedDoc && (
            <>
              <DialogHeader>
                <div className="flex items-center gap-2">
                  <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
                    <FileText className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <DialogTitle className="truncate text-base">
                      {selectedDoc.original_filename || selectedDoc.filename}
                    </DialogTitle>
                    <DialogDescription className="text-xs">
                      Document Details & Metadata
                    </DialogDescription>
                  </div>
                </div>
              </DialogHeader>

              <div className="space-y-4 py-2">
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="rounded-xl border border-border/70 bg-muted/30 p-3">
                    <p className="text-muted-foreground">Format / Type</p>
                    <Badge variant="outline" className="mt-1 uppercase text-[10px]">
                      {selectedDoc.source_type}
                    </Badge>
                  </div>
                  <div className="rounded-xl border border-border/70 bg-muted/30 p-3">
                    <p className="text-muted-foreground">File Size</p>
                    <p className="mt-1 font-mono font-medium text-foreground">
                      {formatSize(selectedDoc.size_bytes)}
                    </p>
                  </div>
                  <div className="rounded-xl border border-border/70 bg-muted/30 p-3">
                    <p className="text-muted-foreground">Indexed Chunks</p>
                    <p className="mt-1 font-mono font-medium text-foreground">
                      {selectedDoc.chunk_count ?? selectedDoc.chunks ?? 0}
                    </p>
                  </div>
                  <div className="rounded-xl border border-border/70 bg-muted/30 p-3">
                    <p className="text-muted-foreground">Page Count</p>
                    <p className="mt-1 font-mono font-medium text-foreground">
                      {selectedDoc.page_count ?? 1}
                    </p>
                  </div>
                </div>

                <div className="space-y-2 rounded-xl border border-border/70 bg-card p-3 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Document ID</span>
                    <span className="font-mono text-[11px] text-foreground">
                      {selectedDoc.document_id}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Status</span>
                    <span className="inline-flex items-center gap-1 font-medium text-emerald-600 dark:text-emerald-400">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      {selectedDoc.status || "Ready"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Uploaded At</span>
                    <span className="font-mono text-[11px] text-foreground">
                      {formatDate(selectedDoc.created_at)}
                    </span>
                  </div>
                </div>
              </div>

              <DialogFooter className="flex-row items-center justify-between sm:justify-between">
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => {
                    const doc = selectedDoc;
                    setSelectedDoc(null);
                    setTarget(doc);
                  }}
                >
                  Delete Document
                </Button>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setSelectedDoc(null)}>
                    Close
                  </Button>
                  <Button size="sm" asChild>
                    <a
                      href={getDocumentFileUrl(selectedDoc.document_id)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <ExternalLink className="mr-1.5 h-3.5 w-3.5" /> Preview File
                    </a>
                  </Button>
                </div>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <DeleteDialog
        open={Boolean(target)}
        filename={target?.original_filename || target?.filename}
        onOpenChange={(open) => !open && setTarget(null)}
        onConfirm={() => void confirmDelete()}
      />
    </div>
  );
}
