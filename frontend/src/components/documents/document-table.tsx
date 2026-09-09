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
  onDelete,
  emptyAction,
}: {
  documents: DocumentItem[];
  loading: boolean;
  onDelete: (doc: DocumentItem) => void;
  emptyAction?: React.ReactNode;
}) {
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("filename");
  const [asc, setAsc] = useState(true);

  const rows = useMemo(() => {
    const filtered = documents.filter((doc) =>
      doc.filename.toLowerCase().includes(query.trim().toLowerCase()),
    );
    return [...filtered].sort((a, b) => {
      const result =
        sortKey === "chunks" ? a.chunks - b.chunks : a.filename.localeCompare(b.filename);
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
          description="Upload a PDF and Manan will chunk, embed, and index it so you can chat with it."
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
                    Filename <ArrowUpDown className="h-3.5 w-3.5" />
                  </button>
                </TableHead>
                <TableHead>
                  <button
                    className="flex items-center gap-1.5 font-medium"
                    onClick={() => toggleSort("chunks")}
                  >
                    Chunks <ArrowUpDown className="h-3.5 w-3.5" />
                  </button>
                </TableHead>
                <TableHead className="hidden md:table-cell">Document ID</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((doc) => (
                <TableRow key={doc.document_id} className="transition-colors">
                  <TableCell className="max-w-[240px]">
                    <div className="flex min-w-0 items-center gap-2">
                      <FileText className="h-4 w-4 shrink-0 text-primary" />
                      <span className="truncate font-medium">{doc.filename}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="rounded-lg">
                      {doc.chunks}
                    </Badge>
                  </TableCell>
                  <TableCell className="hidden font-mono text-xs text-muted-foreground md:table-cell">
                    {doc.document_id}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="icon"
                      variant="ghost"
                      aria-label={`Delete ${doc.filename}`}
                      className="rounded-lg text-muted-foreground hover:text-destructive"
                      onClick={() => onDelete(doc)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
