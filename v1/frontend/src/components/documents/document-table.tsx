import { useMemo, useState } from "react";
import { ArrowUpDown, FileText, Search, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/empty-state";
import type { DocumentItem } from "@/types";

type SortKey = "filename" | "chunks";

export function DocumentTable({
  documents,
  loading,
  onSelect,
  onDelete,
  emptyAction,
}: {
  documents: DocumentItem[];
  loading: boolean;
  onSelect?: (doc: DocumentItem) => void;
  onDelete: (doc: DocumentItem) => void;
  emptyAction?: React.ReactNode;
}) {
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("filename");
  const [asc, setAsc] = useState(true);

  const formatSize = (bytes: number) => {
    if (!bytes) return "0 B";
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const rows = useMemo(() => {
    const filtered = documents.filter((doc) => {
      const name = doc.original_filename || doc.filename || "";
      return name.toLowerCase().includes(query.trim().toLowerCase());
    });
    return [...filtered].sort((a, b) => {
      const nameA = a.original_filename || a.filename || "";
      const nameB = b.original_filename || b.filename || "";
      const chunksA = a.chunk_count ?? a.chunks ?? 0;
      const chunksB = b.chunk_count ?? b.chunks ?? 0;
      const result =
        sortKey === "chunks" ? chunksA - chunksB : nameA.localeCompare(nameB);
      return asc ? result : -result;
    });
  }, [documents, query, sortKey, asc]);

  const toggleSort = (key: SortKey) => {
    if (key === sortKey) setAsc((v) => !v);
    else {
      setSortKey(key);
      setAsc(true);
    }
  };

  if (loading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-10 w-full max-w-sm rounded-xl" />
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-14 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="relative max-w-sm">
        <Search className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search documents…"
          aria-label="Search documents"
          className="rounded-xl pl-9"
        />
      </div>

      {documents.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No documents yet"
          description="Upload a document (PDF, OCR scan, CSV, JSON, SQL, DOCX, PPTX, TXT) and Manan will index it for Chat & Study."
          action={emptyAction}
        />
      ) : rows.length === 0 ? (
        <EmptyState
          icon={Search}
          title="No matches"
          description={`Nothing matched "${query}". Try a different filename.`}
        />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-soft">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>
                  <button
                    className="flex items-center gap-1.5 font-medium"
                    onClick={() => toggleSort("filename")}
                  >
                    Document <ArrowUpDown className="h-3.5 w-3.5" />
                  </button>
                </TableHead>
                <TableHead>Format</TableHead>
                <TableHead>Size</TableHead>
                <TableHead>Pages</TableHead>
                <TableHead>
                  <button
                    className="flex items-center gap-1.5 font-medium"
                    onClick={() => toggleSort("chunks")}
                  >
                    Chunks <ArrowUpDown className="h-3.5 w-3.5" />
                  </button>
                </TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((doc) => {
                const name = doc.original_filename || doc.filename || "Untitled";
                const chunks = doc.chunk_count ?? doc.chunks ?? 0;
                return (
                  <TableRow
                    key={doc.document_id}
                    className="cursor-pointer transition-colors hover:bg-muted/40"
                    onClick={() => onSelect?.(doc)}
                  >
                    <TableCell className="max-w-[260px]">
                      <div className="flex min-w-0 items-center gap-2">
                        <FileText className="h-4 w-4 shrink-0 text-primary" />
                        <span className="truncate font-medium hover:underline">{name}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="rounded-md uppercase text-[10px]">
                        {doc.source_type || "pdf"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatSize(doc.size_bytes)}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {doc.page_count ?? 0}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="rounded-lg text-xs">
                        {chunks}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="inline-flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                        {doc.status || "ready"}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="icon"
                        variant="ghost"
                        aria-label={`Delete ${name}`}
                        className="rounded-lg text-muted-foreground hover:text-destructive"
                        onClick={(e) => {
                          e.stopPropagation();
                          onDelete(doc);
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
