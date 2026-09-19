import { useState } from "react";
import { FileText, Table, Database, Image, ChevronDown } from "lucide-react";
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

export function CompactSourcesDisplay({ citations }: { citations: Citation[] }) {
  const [isOpen, setIsOpen] = useState(false);
  if (!citations || citations.length === 0) return null;

  return (
    <HoverCard open={isOpen} onOpenChange={setIsOpen} openDelay={150} closeDelay={200}>
      <HoverCardTrigger asChild>
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          className={cn(
            "inline-flex items-center gap-2 rounded-xl border border-border/80 bg-muted/40 px-3 py-1.5 text-xs text-foreground transition-all hover:bg-muted/80 hover:border-primary/40 cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/20",
            isOpen && "border-primary/50 bg-primary/10 text-primary"
          )}
          aria-expanded={isOpen}
          aria-label={`View ${citations.length} sources`}
        >
          <FileText className="h-3.5 w-3.5 text-primary" />
          <span className="font-semibold">Sources ({citations.length})</span>
          <ChevronDown className={cn("h-3 w-3 text-muted-foreground transition-transform duration-200", isOpen && "rotate-180")} />
        </button>
      </HoverCardTrigger>

      <HoverCardContent align="start" side="top" className="w-80 sm:w-96 max-h-80 overflow-y-auto space-y-2.5 rounded-2xl p-4 shadow-xl border-border bg-popover text-popover-foreground">
        <div className="flex items-center justify-between border-b border-border/50 pb-2">
          <span className="text-xs font-bold text-foreground">
            Sources & References ({citations.length})
          </span>
        </div>
        <div className="space-y-2">
          {citations.map((citation, i) => {
            const Icon = getSourceIcon(citation.source_type);
            const location = getLocationTag(citation);
            const filename = citation.filename || "Document";
            const snippet = citation.snippet || citation.text || "";

            return (
              <div
                key={citation.id || `${filename}-${i}`}
                className="rounded-xl border border-border/50 bg-muted/30 p-2.5 text-xs space-y-1 transition-colors hover:bg-muted/50"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <Icon className="h-3.5 w-3.5 text-primary shrink-0" />
                    <span className="font-medium text-foreground truncate">{filename}</span>
                  </div>
                  <Badge variant="outline" className="shrink-0 text-[10px] font-mono px-1.5 py-0">
                    {location}
                  </Badge>
                </div>
                {snippet && (
                  <p className="text-[11px] text-muted-foreground line-clamp-2 leading-relaxed italic pl-5">
                    "{snippet.trim()}"
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </HoverCardContent>
    </HoverCard>
  );
}

export function CitationCard({ citation }: { citation: Citation }) {
  return <CompactSourcesDisplay citations={[citation]} />;
}
