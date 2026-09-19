import { useEffect, useState } from "react";
import { ChevronDown, Cpu, Check, Loader2, AlertCircle, RefreshCw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import {
  fetchAvailableModels,
  type AvailableModelsData,
  type AvailableModelItem,
} from "@/services/chat";
import { MODEL_OPTIONS } from "@/services/axios";

interface ModelSelectorProps {
  currentModel: string;
  onModelChange: (modelValue: string, provider: "gemini" | "ollama") => void;
  compact?: boolean;
}

export function ModelSelector({ currentModel, onModelChange }: ModelSelectorProps) {
  const [data, setData] = useState<AvailableModelsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [, setError] = useState<string | null>(null);

  const loadModels = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchAvailableModels();
      setData(res);
    } catch {
      setError("Could not load models from server");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadModels();
  }, []);

  const getModelDisplayLabel = (val: string): string => {
    if (data) {
      const all = [...(data.gemini?.models ?? []), ...(data.ollama?.models ?? [])];
      const match = all.find((m) => m.value === val);
      if (match) return match.label;
    }
    const fallback = MODEL_OPTIONS.find((m) => m.value === val);
    return fallback ? fallback.label : val;
  };

  const handleSelect = (item: AvailableModelItem) => {
    onModelChange(item.value, item.provider);
  };

  const displayLabel = getModelDisplayLabel(currentModel);
  const isOllamaActive =
    currentModel.toLowerCase().includes("gpt") ||
    currentModel.toLowerCase().includes("oss") ||
    currentModel.toLowerCase().includes("gemma") ||
    currentModel.toLowerCase().includes("qwen") ||
    currentModel.toLowerCase().includes("llama") ||
    Boolean(data?.ollama?.models?.some((m) => m.value === currentModel));

  return (
    <TooltipProvider delayDuration={150}>
      <DropdownMenu
        onOpenChange={(open) => {
          if (open && !data) void loadModels();
        }}
      >
        <Tooltip>
          <TooltipTrigger asChild>
            <DropdownMenuTrigger asChild>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className={`h-8 gap-1.5 rounded-xl border-border bg-card/60 px-2.5 text-xs font-medium backdrop-blur transition-all hover:bg-card hover:text-foreground ${
                  isOllamaActive
                    ? "border-emerald-500/30 text-emerald-600 dark:text-emerald-400"
                    : "border-primary/20 text-primary"
                }`}
              >
                {loading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : isOllamaActive ? (
                  <Cpu className="h-3.5 w-3.5" />
                ) : (
                  <Sparkles className="h-3.5 w-3.5" />
                )}
                <span className="max-w-[120px] truncate">{displayLabel}</span>
                <ChevronDown className="h-3 w-3 opacity-60" />
              </Button>
            </DropdownMenuTrigger>
          </TooltipTrigger>
          <TooltipContent side="top">Active model (Click to change)</TooltipContent>
        </Tooltip>

        <DropdownMenuContent align="end" className="w-64 p-2 shadow-lift">
          <div className="flex items-center justify-between px-2 py-1.5 text-xs font-semibold text-muted-foreground">
            <span>Select Model</span>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-5 w-5 rounded-md text-muted-foreground hover:text-foreground"
              onClick={(e) => {
                e.stopPropagation();
                void loadModels();
              }}
              title="Refresh available models"
            >
              <RefreshCw className={`h-3 w-3 ${loading ? "animate-spin" : ""}`} />
            </Button>
          </div>

          <DropdownMenuSeparator />

          {/* Gemini Models Section */}
          <DropdownMenuGroup>
            <DropdownMenuLabel className="flex items-center gap-1.5 px-2 py-1 text-xs font-medium text-foreground">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              <span>Google Gemini</span>
            </DropdownMenuLabel>

            {(
              data?.gemini?.models ?? [
                { value: "gemini-3.6-flash", label: "Gemini 3.6 Flash", provider: "gemini" },
              ]
            ).map((item) => (
              <DropdownMenuItem
                key={item.value}
                onClick={() => handleSelect(item)}
                className="flex items-center justify-between rounded-lg px-2 py-1.5 text-xs cursor-pointer"
              >
                <span className="font-medium text-foreground">{item.label}</span>
                {currentModel === item.value && <Check className="h-3.5 w-3.5 text-primary" />}
              </DropdownMenuItem>
            ))}
          </DropdownMenuGroup>

          <DropdownMenuSeparator />

          {/* Ollama Cloud Models Section */}
          <DropdownMenuGroup>
            <DropdownMenuLabel className="flex items-center gap-1.5 px-2 py-1 text-xs font-medium text-foreground">
              <Cpu className="h-3.5 w-3.5 text-emerald-500" />
              <span>Ollama Cloud</span>
            </DropdownMenuLabel>

            {data?.ollama?.available === false ? (
              <div className="mx-1 my-1 flex items-start gap-2 rounded-lg bg-destructive/10 p-2 text-xs text-destructive">
                <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span className="leading-tight">{data.ollama.message}</span>
              </div>
            ) : (
              (
                data?.ollama?.models ?? [
                  {
                    value: "qwen3-coder:480b-cloud",
                    label: "Qwen 3 Coder 480B (Ollama Cloud)",
                    provider: "ollama",
                  },
                ]
              ).map((item) => (
                <DropdownMenuItem
                  key={item.value}
                  onClick={() => handleSelect(item)}
                  className="flex items-center justify-between rounded-lg px-2 py-1.5 text-xs cursor-pointer"
                >
                  <span className="font-medium text-foreground">{item.label}</span>
                  {currentModel === item.value && (
                    <Check className="h-3.5 w-3.5 text-emerald-500" />
                  )}
                </DropdownMenuItem>
              ))
            )}
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>
    </TooltipProvider>
  );
}
