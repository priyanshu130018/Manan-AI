import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Moon, Sun, Sparkle, Brain, Cpu } from "lucide-react";
import { toast } from "sonner";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useTheme } from "@/hooks/use-theme";
import { getHealthInfo } from "@/services/chat";
import { readSettings, writeSettings, MODEL_OPTIONS, type AppSettings } from "@/services/axios";
import { MananLogo } from "@/components/common/manan-logo";
import type { SystemHealth } from "@/types";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings — Manan AI" },
      {
        name: "description",
        content: "Configure Manan AI theme and system preferences.",
      },
    ],
  }),
  component: SettingsPage,
});

const VERSION = "2.0.0";

function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [settings, setSettings] = useState<AppSettings>(readSettings);

  useEffect(() => {
    let active = true;
    getHealthInfo()
      .then((data) => {
        if (active) setHealth(data);
      })
      .catch(() => {
        if (active) setHealth(null);
      });

    return () => {
      active = false;
    };
  }, []);

  const handleModelChange = (model: string) => {
    const opt = MODEL_OPTIONS.find((m) => m.value === model);
    const provider = opt?.provider || settings.provider;
    const updated = { ...settings, model, provider };
    setSettings(updated);
    writeSettings(updated);
    toast.success(`Model switched to ${opt?.label || model}`);
  };

  const handleToggleMemory = (enabled: boolean) => {
    const updated = { ...settings, memoryEnabled: enabled };
    setSettings(updated);
    writeSettings(updated);
    toast.success(enabled ? "Long-term memory enabled." : "Long-term memory disabled.");
  };

  return (
    <div className="h-full overflow-y-auto scroll-fade px-4 py-8 sm:px-8">
      <div className="mx-auto w-full max-w-2xl space-y-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-semibold">Settings</h1>
          <p className="text-sm text-muted-foreground">
            Configure how Manan AI looks and your AI model preferences.
          </p>
        </header>

        {/* Model Selection Section */}
        <section className="rounded-2xl border border-border bg-card p-5 shadow-soft space-y-4">
          <div className="flex items-center gap-2 text-foreground font-medium">
            <Cpu className="h-4 w-4 text-primary" />
            AI Model Preference
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="model-select" className="text-xs text-muted-foreground">
              Select LLM Provider & Model
            </Label>
            <Select value={settings.model} onValueChange={handleModelChange}>
              <SelectTrigger id="model-select" className="w-full">
                <SelectValue placeholder="Select model" />
              </SelectTrigger>
              <SelectContent>
                {MODEL_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-[11px] text-muted-foreground pt-1">
              Gemini models connect via Google Gemini API. Ollama models connect to Ollama Cloud API
              (https://ollama.com/v1).
            </p>
          </div>
        </section>

        {/* Memory Toggle Section */}
        <section className="rounded-2xl border border-border bg-card p-5 shadow-soft">
          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4">
            <div className="min-w-0 space-y-0.5">
              <div className="flex items-center gap-2">
                <Brain className="h-4 w-4 text-primary" />
                <Label className="text-sm font-medium">Long-Term Memory</Label>
              </div>
              <p className="text-xs text-muted-foreground">
                Automatically retain facts, preferences, and context across sessions.
              </p>
            </div>
            <div className="flex shrink-0 items-center">
              <Switch
                checked={settings.memoryEnabled}
                onCheckedChange={handleToggleMemory}
                aria-label="Toggle long-term memory"
              />
            </div>
          </div>
        </section>

        {/* Appearance Section */}
        <section className="rounded-2xl border border-border bg-card p-5 shadow-soft">
          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4">
            <div className="min-w-0 space-y-0.5">
              <Label className="text-sm font-medium">Dark mode</Label>
              <p className="text-xs text-muted-foreground">
                Switch between light and dark appearance.
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <Sun className="h-4 w-4 text-muted-foreground" />
              <Switch
                checked={theme === "dark"}
                onCheckedChange={(checked) => setTheme(checked ? "dark" : "light")}
                aria-label="Toggle dark mode"
              />
              <Moon className="h-4 w-4 text-muted-foreground" />
            </div>
          </div>
        </section>

        {/* System Details */}
        <section className="rounded-2xl border border-border bg-card p-5 shadow-soft">
          <MananLogo
            size="lg"
            showWordmark
            subtitle="Intelligent RAG Assistant"
            ariaLabel="Manan AI home"
            className="transition-opacity hover:opacity-80"
          />
          <Separator className="my-4" />
          <dl className="grid gap-2.5 text-sm">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Version</dt>
              <dd className="font-mono">{VERSION}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Backend Status</dt>
              <dd className="flex items-center gap-1.5 font-mono">
                <span
                  className={`inline-block h-2 w-2 rounded-full ${
                    health?.status === "healthy" ? "bg-emerald-500" : "bg-amber-500"
                  }`}
                />
                {health?.status ? "Connected" : "Not connected"}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Database</dt>
              <dd className="font-mono">PostgreSQL</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Vector Store</dt>
              <dd className="font-mono">PostgreSQL pgvector (HNSW)</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Active Model</dt>
              <dd className="truncate pl-4 font-mono">{settings.model}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Embedding Model</dt>
              <dd className="truncate pl-4 font-mono">
                {health?.embedding_model || "all-MiniLM-L6-v2"}
              </dd>
            </div>
          </dl>
        </section>
      </div>
    </div>
  );
}
