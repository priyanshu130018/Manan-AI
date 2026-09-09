import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { CheckCircle2, FileText, XCircle } from "lucide-react";
import { toast } from "sonner";
import { UploadZone } from "@/components/upload/upload-zone";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { toFriendlyError } from "@/services/axios";
import { uploadDocument } from "@/services/upload";
import type { UploadResult } from "@/types";

export const Route = createFileRoute("/upload")({
  head: () => ({
    meta: [
      { title: "Upload documents — Manan AI" },
      {
        name: "description",
        content:
          "Drag and drop PDFs to index them into Manan's retrieval knowledge base and see chunk counts instantly.",
      },
      { property: "og:title", content: "Upload documents — Manan AI" },
      {
        property: "og:description",
        content: "Add PDFs to Manan's knowledge base with live upload progress.",
      },
    ],
  }),
  component: UploadPage,
});

interface UploadRow extends UploadResult {
  status: "uploading" | "success" | "error";
  progress: number;
  message?: string;
}

function UploadPage() {
  const [rows, setRows] = useState<UploadRow[]>([]);
  const [busy, setBusy] = useState(false);

  const handleFiles = async (files: File[]) => {
    const pdfs = files.filter(
      (file) => file.type === "application/pdf" || file.name.endsWith(".pdf"),
    );
    if (pdfs.length !== files.length) toast.error("Only PDF files are supported.");
    if (!pdfs.length) return;

    setBusy(true);
    for (const file of pdfs) {
      const key = crypto.randomUUID();
      setRows((prev) => [
        { document_id: key, filename: file.name, chunks: 0, status: "uploading", progress: 0 },
        ...prev,
      ]);

      try {
        const result = await uploadDocument(file, (progress) =>
          setRows((prev) =>
            prev.map((row) => (row.document_id === key ? { ...row, progress } : row)),
          ),
        );
        setRows((prev) =>
          prev.map((row) =>
            row.document_id === key ? { ...row, ...result, status: "success", progress: 100 } : row,
          ),
        );
        toast.success(`${result.filename} indexed`, {
          description: `${result.chunks} chunks are now searchable.`,
        });
      } catch (error) {
        const message = toFriendlyError(error);
        setRows((prev) =>
          prev.map((row) => (row.document_id === key ? { ...row, status: "error", message } : row)),
        );
        toast.error(`Upload failed: ${file.name}`, { description: message });
      }
    }
    setBusy(false);
  };

  return (
    <div className="h-full overflow-y-auto scroll-fade px-4 py-8 sm:px-8">
      <div className="mx-auto w-full max-w-3xl space-y-8">
        <header className="space-y-1">
          <h1 className="text-2xl font-semibold">Upload documents</h1>
          <p className="text-sm text-muted-foreground">
            PDFs are chunked and embedded so Manan can cite them in answers.
          </p>
        </header>

        <UploadZone onFiles={handleFiles} disabled={busy} />

        {rows.length > 0 && (
          <section className="space-y-3">
            <h2 className="text-sm font-medium tracking-wide text-muted-foreground uppercase">
              Recently uploaded
            </h2>
            <div className="space-y-2">
              {rows.map((row) => (
                <div
                  key={row.document_id}
                  className="rounded-2xl border border-border bg-card p-4 shadow-soft transition-all"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
                      <FileText className="h-4 w-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{row.filename}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {row.status === "uploading" && `Uploading… ${row.progress}%`}
                        {row.status === "success" && `${row.chunks} chunks · ${row.document_id}`}
                        {row.status === "error" && row.message}
                      </p>
                    </div>
                    {row.status === "success" && (
                      <CheckCircle2 className="h-5 w-5 shrink-0 animate-in zoom-in text-primary" />
                    )}
                    {row.status === "error" && (
                      <XCircle className="h-5 w-5 shrink-0 text-destructive" />
                    )}
                  </div>
                  {row.status === "uploading" && (
                    <Progress value={row.progress} className="mt-3 h-1.5" />
                  )}
                </div>
              ))}
            </div>
            <Button asChild variant="outline" className="rounded-xl">
              <Link to="/documents">View all documents</Link>
            </Button>
          </section>
        )}
      </div>
    </div>
  );
}
