import { Check, FileText, Layers, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { DocumentItem } from "@/types";

interface DocumentSelectorProps {
  documents: DocumentItem[];
  selectedDocIds: string[];
  onToggleDoc: (id: string) => void;
  onClearAll: () => void;
  onSelectAll: () => void;
}

export function DocumentSelector({
  documents,
  selectedDocIds,
  onToggleDoc,
  onClearAll,
  onSelectAll,
}: DocumentSelectorProps) {
  if (!documents || documents.length === 0) {
    return null;
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant={selectedDocIds.length > 0 ? "secondary" : "outline"}
          size="sm"
          className="rounded-xl"
        >
          <Layers className="mr-1.5 h-3.5 w-3.5" />
          {selectedDocIds.length > 0
            ? `${selectedDocIds.length} of ${documents.length} doc${documents.length === 1 ? "" : "s"}`
            : "Documents"}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel className="flex items-center justify-between text-xs">
          <span>Select documents</span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onSelectAll}
              className="text-xs text-primary hover:underline"
            >
              Select All
            </button>
            {selectedDocIds.length > 0 && (
              <button
                type="button"
                onClick={onClearAll}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                Clear
              </button>
            )}
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <div className="max-h-64 overflow-y-auto">
          {documents.map((doc) => {
            const isSelected = selectedDocIds.includes(doc.document_id);
            const name = doc.original_filename || doc.filename || "Untitled document";
            return (
              <DropdownMenuCheckboxItem
                key={doc.document_id}
                checked={isSelected}
                onCheckedChange={() => onToggleDoc(doc.document_id)}
                className="flex items-center justify-between py-2 text-xs"
              >
                <div className="flex min-w-0 flex-1 flex-col pr-2">
                  <span className="truncate font-medium">{name}</span>
                  <span className="text-[10px] text-muted-foreground">
                    {doc.source_type?.toUpperCase() || "PDF"} · {doc.page_count ?? 0} pages · {doc.chunk_count ?? doc.chunks ?? 0} chunks
                  </span>
                </div>
              </DropdownMenuCheckboxItem>
            );
          })}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
