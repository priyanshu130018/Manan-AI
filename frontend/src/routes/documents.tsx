import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { RefreshCw, Upload } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { DocumentTable } from "@/components/documents/document-table";
import { DeleteDialog } from "@/components/documents/delete-dialog";
import { deleteDocument, listDocuments } from "@/services/document";
import { toFriendlyError } from "@/services/axios";
import type { DocumentItem } from "@/types";

export const Route = createFileRoute("/documents")({
  head: () => ({
    meta: [
      { title: "Documents — Manan AI" },
      {
        name: "description",
        content:
          "Browse, search, sort and delete the PDFs indexed in Manan's retrieval knowledge base.",
      },
      { property: "og:title", content: "Documents — Manan AI" },
      {
        property: "og:description",
        content: "Manage every document powering Manan's answers.",
      },
    ],
  }),
  component: DocumentsPage,
});

function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [target, setTarget] = useState<DocumentItem | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      setDocuments(await listDocuments());
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

  const confirmDelete = async () => {
    if (!target) return;
    const doc = target;
    setTarget(null);
    try {
      await deleteDocument(doc.document_id);
      setDocuments((prev) => prev.filter((d) => d.document_id !== doc.document_id));
      toast.success(`${doc.filename} deleted`);
    } catch (error) {
      toast.error("Delete failed", { description: toFriendlyError(error) });
    }
  };

  return (
    <div className="h-full overflow-y-auto scroll-fade px-4 py-8 sm:px-8">
      <div className="mx-auto w-full max-w-5xl space-y-6">
        <header className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4">
          <div className="min-w-0">
            <h1 className="text-2xl font-semibold">Documents</h1>
            <p className="text-sm text-muted-foreground">
              {documents.length} indexed document{documents.length === 1 ? "" : "s"}
            </p>
          </div>
          <Button variant="outline" className="rounded-xl" onClick={() => void load()}>
            <RefreshCw className="mr-2 h-4 w-4" /> Refresh
          </Button>
        </header>

        <DocumentTable
          documents={documents}
          loading={loading}
          onDelete={setTarget}
          emptyAction={
            <Button asChild className="rounded-xl">
              <Link to="/upload">
                <Upload className="mr-2 h-4 w-4" /> Upload a PDF
              </Link>
            </Button>
          }
        />
      </div>

      <DeleteDialog
        open={Boolean(target)}
        filename={target?.filename}
        onOpenChange={(open) => !open && setTarget(null)}
        onConfirm={() => void confirmDelete()}
      />
    </div>
  );
}
