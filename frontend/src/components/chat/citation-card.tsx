import { useState } from "react";
import { FileText, Table, Database, Image } from "lucide-react";
import { HoverCard, HoverCardTrigger, HoverCardContent } from "@/components/ui/hover-card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Citation } from "@/types";

function getSourceIcon(sourceType?: string) {
  const type = (sourceType || "").toLowerCase();
  if (type.includes("csv") || type.includes("excel") || type.includes("table")) {
    return Table;
  }
  if (type.includes("sql") || type.includes("db") || type.includes("database")) {
    return Database;
  }
  if (type.includes("png") || type.includes("jpg") || type.includes("image") || type.includes("jpeg") || type.includes("webp")) {
    return Image;
  }
  return FileText;
}

function getLocationTag(citation: Citation): string {
  const page = citation.page_number ?? citation.page;
  if (typeof page === "number" && page > 0) {
    return `Page ${page}`;
  }
  if (citation.row_range) {
    return citation.row_range;
  }
  if (citation.table_context) {
    return citation.table_context;
  }
  const chunk = citation.chunk_index ?? citation.chunk;
  if (typeof chunk === "number" && chunk > 0) {
    return `Chunk ${chunk}`;
  }
  return "Source";
}

export function CitationCard({ citation }: { citation: Citation }) {
  const [isOpen, setIsOpen] = useState(false);
  const Icon = getSourceIcon(citation.source_type);
  const locationTag = getLocationTag(citation);
  const sourceTypeLabel = (citation.source_type || "document").toUpperCase();
  const snippetText = citation.snippet || citation.text || "";
  const matchScore = typeof citation.score === "number" ? `${Math.round(citation.score * 100)}% match` : null;
  const retrievalMethod = citation.retrieval_method || "Hybrid Search";

  return (
    <HoverCard open={isOpen} onOpenChange={setIsOpen} openDelay={100} closeDelay={150}>
      <HoverCardTrigger asChild>
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          className={cn(
            "group inline-flex items-center gap-2 rounded-xl border border-border/80 bg-muted/40 px-3 py-1.5 text-xs text-foreground transition-all hover:bg-muted/80 hover:border-primary/40 hover:shadow-soft active:scale-[0.98] cursor-pointer",
            isOpen && "border-primary/50 bg-primary/10 text-primary"
          )}
        >
          <Icon className="h-3.5 w-3.5 shrink-0 text-primary/80 group-hover:text-primary" />
          <span className="max-w-[140px] sm:max-w-[200px] truncate font-medium">
            {citation.filename}
          </span>
          <span className="rounded-md bg-background/80 px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground border border-border/40">
            {locationTag}
          </span>
        </button>
      </HoverCardTrigger>

      <HoverCardContent align="start" side="top" className="w-80 space-y-3 rounded-2xl p-4 shadow-xl border-border bg-popover text-popover-foreground">
        {/* Header */}
        <div className="flex items-start justify-between gap-2 border-b border-border/50 pb-2.5">
          <div className="flex items-center gap-2 min-w-0">
            <div className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
              <Icon className="h-3.5 w-3.5" />
            </div>
            <p className="truncate text-xs font-semibold text-foreground">
              {citation.filename}
            </p>
          </div>
          <Badge variant="outline" className="shrink-0 text-[10px] font-mono tracking-wider uppercase">
            {sourceTypeLabel}
          </Badge>
        </div>

        {/* Metadata Details */}
        <div className="grid grid-cols-2 gap-2 text-[11px]">
          <div className="rounded-lg bg-muted/50 p-2">
            <span className="text-muted-foreground block text-[10px]">Location</span>
            <span className="font-mono font-medium text-foreground">{locationTag}</span>
          </div>
          <div className="rounded-lg bg-muted/50 p-2">
            <span className="text-muted-foreground block text-[10px]">Method</span>
            <span className="font-mono font-medium text-foreground">{retrievalMethod}</span>
          </div>
          {matchScore && (
            <div className="col-span-2 rounded-lg bg-emerald-500/10 p-2 border border-emerald-500/20">
              <span className="text-emerald-700 dark:text-emerald-300 block text-[10px] font-medium">Relevance</span>
              <span className="font-mono font-semibold text-emerald-600 dark:text-emerald-400">{matchScore}</span>
            </div>
          )}
        </div>

        {/* Snippet Preview */}
        {snippetText && (
          <div className="space-y-1">
            <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
              Context Extract
            </span>
            <p className="rounded-lg border border-border/40 bg-muted/30 p-2.5 text-xs text-muted-foreground leading-relaxed line-clamp-4 font-sans">
              "{snippetText.trim()}"
            </p>
          </div>
        )}
      </HoverCardContent>
    </HoverCard>
  );
}
