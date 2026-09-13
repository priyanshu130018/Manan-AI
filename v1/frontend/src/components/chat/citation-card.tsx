import { FileText } from "lucide-react";
import type { Citation } from "@/types";

export function CitationCard({ citation, onClick }: { citation: Citation; onClick?: () => void }) {
  const chunkNumber = citation.chunk_index ?? citation.chunk;
  const sourceDetail = [
    typeof citation.page === "number" ? `Page ${citation.page}` : null,
    typeof chunkNumber === "number" ? `Chunk ${chunkNumber}` : null,
    citation.source_type ? `${citation.source_type.toUpperCase()}` : null,
    typeof citation.score === "number" ? `${(citation.score * 100).toFixed(0)}% match` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex w-full items-start gap-3 rounded-xl border border-border bg-card px-3 py-2.5 text-left transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-soft"
    >
      <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
        <FileText className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{citation.filename}</p>
        <p className="text-xs text-muted-foreground">{sourceDetail || "Source chunk"}</p>
        {citation.text && (
          <p className="mt-1 line-clamp-2 text-xs text-muted-foreground/80">{citation.text}</p>
        )}
      </div>
    </button>
  );
}

