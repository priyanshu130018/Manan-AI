import { useEffect, useRef, useState, type KeyboardEvent, type ChangeEvent } from "react";
import { ArrowUp, Plus, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { LoadingSpinner } from "@/components/common/loading-spinner";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { ModelSelector } from "@/components/chat/model-selector";
import { readSettings, writeSettings } from "@/services/axios";

const ACCEPTED_EXTENSIONS = ".pdf,.docx,.pptx,.txt,.md,.sql,.csv,.json,.png,.jpg,.jpeg,.webp";

export function ChatInput({
  onSend,
  loading,
  placeholder,
  onUploadFile,
  uploading = false,
  disabled = false,
  onDisabledClick,
  currentModel: externalModel,
  onModelChange: externalOnModelChange,
  draftText,
  onDraftTextChange,
}: {
  onSend: (value: string) => void;
  loading: boolean;
  placeholder?: string;
  onUploadFile?: (file: File) => Promise<void> | void;
  uploading?: boolean;
  disabled?: boolean;
  onDisabledClick?: () => void;
  currentModel?: string;
  onModelChange?: (modelValue: string, provider: "gemini" | "ollama") => void;
  draftText?: string;
  onDraftTextChange?: (text: string) => void;
}) {
  const [value, setValue] = useState(draftText || "");
  const [internalModel, setInternalModel] = useState<string>(
    () => externalModel || readSettings().model,
  );
  const ref = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (draftText !== undefined && draftText !== value) {
      setValue(draftText);
    }
  }, [draftText]);

  const activeModel = externalModel || internalModel;

  const handleModelChange = (modelValue: string, provider: "gemini" | "ollama") => {
    setInternalModel(modelValue);
    if (externalOnModelChange) {
      externalOnModelChange(modelValue, provider);
    } else {
      const settings = readSettings();
      writeSettings({ ...settings, model: modelValue, provider });
    }
  };

  useEffect(() => {
    if (!loading && !disabled) ref.current?.focus();
  }, [loading, disabled]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value]);

  const submit = () => {
    if (disabled) {
      onDisabledClick?.();
      return;
    }
    const text = value.trim();
    if (!text || loading) return;
    onSend(text);
    setValue("");
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (disabled) {
      onDisabledClick?.();
      return;
    }
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (disabled) {
      onDisabledClick?.();
      return;
    }
    const file = e.target.files?.[0];
    if (file && onUploadFile) {
      void onUploadFile(file);
    }
    if (e.target) {
      e.target.value = "";
    }
  };

  return (
    <TooltipProvider delayDuration={150}>
      <div className="bg-background/80 px-4 py-2 backdrop-blur">
        <div className="mx-auto w-full max-w-3xl">
          <div
            onClick={() => {
              if (disabled) onDisabledClick?.();
            }}
            className={`flex items-end gap-2 rounded-2xl border border-border bg-card p-2 shadow-soft transition-shadow ${
              disabled
                ? "cursor-pointer opacity-80"
                : "focus-within:border-primary/50 focus-within:shadow-lift"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_EXTENSIONS}
              onChange={handleFileChange}
              className="hidden"
              disabled={disabled}
              aria-label="Upload document"
            />
            {onUploadFile && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    disabled={uploading || loading}
                    onClick={(e) => {
                      if (disabled) {
                        e.stopPropagation();
                        onDisabledClick?.();
                        return;
                      }
                      fileInputRef.current?.click();
                    }}
                    aria-label="Attach document"
                    className="h-9 w-9 shrink-0 rounded-xl text-muted-foreground hover:text-foreground"
                  >
                    {uploading ? (
                      <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    ) : (
                      <Plus className="h-4 w-4" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="top">Attach document (PDF, DOCX, etc.)</TooltipContent>
              </Tooltip>
            )}

            <Textarea
              ref={ref}
              rows={1}
              value={value}
              onChange={(e) => {
                if (disabled) {
                  onDisabledClick?.();
                  return;
                }
                setValue(e.target.value);
              }}
              onKeyDown={onKeyDown}
              readOnly={disabled}
              placeholder={
                disabled ? "Sign in to start chatting" : (placeholder ?? "Ask anything…")
              }
              aria-label="Message Manan"
              className={`max-h-[200px] min-h-[44px] resize-none border-0 bg-transparent px-2 py-2.5 text-sm shadow-none focus-visible:ring-0 dark:bg-transparent ${
                disabled ? "cursor-pointer select-none" : ""
              }`}
            />
            <div className="flex items-center gap-1 shrink-0 pb-1">
              <ModelSelector currentModel={activeModel} onModelChange={handleModelChange} />
              <Button
                size="icon"
                onClick={(e) => {
                  if (disabled) {
                    e.stopPropagation();
                    onDisabledClick?.();
                    return;
                  }
                  submit();
                }}
                disabled={disabled || loading || !value.trim()}
                aria-label="Send message"
                className="h-9 w-9 shrink-0 rounded-xl"
              >
                {loading ? (
                  <LoadingSpinner className="text-primary-foreground" />
                ) : (
                  <ArrowUp className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
          <p className="mt-2 text-center text-xs text-muted-foreground">
            Manan AI can make mistakes. Check important information.
          </p>
        </div>
      </div>
    </TooltipProvider>
  );
}
