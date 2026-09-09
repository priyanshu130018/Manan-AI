import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Check, Moon, Sun, Sparkle } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { useSettings } from "@/hooks/use-settings";
import { useTheme } from "@/hooks/use-theme";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings — Manan AI" },
      {
        name: "description",
        content:
          "Configure Manan's theme, backend API URL and model name, and review application details.",
      },
      { property: "og:title", content: "Settings — Manan AI" },
      {
        property: "og:description",
        content: "Theme, backend URL and model configuration for Manan AI.",
      },
    ],
  }),
  component: SettingsPage,
});

const VERSION = "1.0.0";

function SettingsPage() {
  const { settings, save } = useSettings();
  const { theme, setTheme } = useTheme();
  const [backendUrl, setBackendUrl] = useState(settings.backendUrl);
  const [modelName, setModelName] = useState(settings.modelName);

  useEffect(() => {
    setBackendUrl(settings.backendUrl);
    setModelName(settings.modelName);
  }, [settings]);

  const onSave = () => {
    save({ backendUrl: backendUrl.trim(), modelName: modelName.trim() });
    toast.success("Settings saved");
  };

  return (
    <div className="h-full overflow-y-auto scroll-fade px-4 py-8 sm:px-8">
      <div className="mx-auto w-full max-w-2xl space-y-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-semibold">Settings</h1>
          <p className="text-sm text-muted-foreground">
            Configure how Manan connects and how it looks.
          </p>
        </header>

        <section className="rounded-2xl border border-border bg-card p-5 shadow-soft">
          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4">
            <div className="min-w-0 space-y-0.5">
              <Label className="text-sm font-medium">Dark mode</Label>
              <p className="text-xs text-muted-foreground">
                Switch between the light and dark appearance.
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

        <section className="space-y-5 rounded-2xl border border-border bg-card p-5 shadow-soft">
          <div className="space-y-2">
            <Label htmlFor="backend-url">Backend URL</Label>
            <Input
              id="backend-url"
              value={backendUrl}
              onChange={(e) => setBackendUrl(e.target.value)}
              placeholder="http://localhost:8000"
              className="rounded-xl font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              Base URL for the RAG API (<code>/chat</code>, <code>/upload</code>,{" "}
              <code>/documents</code>).
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="model-name">Model name</Label>
            <Input
              id="model-name"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              placeholder="gpt-4o-mini"
              className="rounded-xl font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              Sent to the backend as the <code>X-Model-Name</code> header.
            </p>
          </div>

          <Button onClick={onSave} className="rounded-xl">
            <Check className="mr-2 h-4 w-4" /> Save changes
          </Button>
        </section>

        <section className="rounded-2xl border border-border bg-card p-5 shadow-soft">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary text-primary-foreground">
              <Sparkle className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold">Manan AI</p>
              <p className="text-xs text-muted-foreground">
                Retrieval-augmented document assistant
              </p>
            </div>
          </div>
          <Separator className="my-4" />
          <dl className="grid gap-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Version</dt>
              <dd className="font-mono">{VERSION}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Model</dt>
              <dd className="truncate pl-4 font-mono">{settings.modelName}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Backend</dt>
              <dd className="truncate pl-4 font-mono">{settings.backendUrl}</dd>
            </div>
          </dl>
        </section>
      </div>
    </div>
  );
}
