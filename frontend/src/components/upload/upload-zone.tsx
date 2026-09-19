import { useCallback, useRef, useState, type DragEvent } from "react";
import { UploadCloud, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function UploadZone({
  onFiles,
  disabled,
}: {
  onFiles: (files: File[]) => void;
  disabled?: boolean;
}) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setDragging(false);
      if (disabled) return;
      onFiles(Array.from(event.dataTransfer.files));
    },
    [onFiles, disabled],
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={cn(
        "flex flex-col items-center justify-center gap-4 rounded-3xl border-2 border-dashed px-6 py-8 text-center transition-all",
        dragging
          ? "border-primary bg-primary/5 scale-[1.01]"
          : "border-border bg-card/60 hover:border-primary/40",
        disabled && "pointer-events-none opacity-60",
      )}
    >
      <div className="grid h-16 w-16 place-items-center rounded-2xl bg-primary/10 text-primary">
        <UploadCloud className="h-7 w-7" />
      </div>
      <div className="space-y-1">
        <h2 className="text-base font-semibold">Drop your study materials here</h2>
        <p className="text-sm text-muted-foreground">
          Supports PDF (with OCR), CSV, JSON, SQL, DOCX, PPTX, TXT, and Images. Up to 50 MB per file.
        </p>
      </div>
      <Button variant="outline" className="rounded-xl" onClick={() => inputRef.current?.click()}>
        <FileText className="mr-2 h-4 w-4" /> Browse files
      </Button>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.pptx,.txt,.md,.csv,.json,.sql,.png,.jpg,.jpeg,.webp"
        multiple
        hidden
        onChange={(e) => {
          onFiles(Array.from(e.target.files ?? []));
          e.target.value = "";
        }}
      />
    </div>
  );
}
