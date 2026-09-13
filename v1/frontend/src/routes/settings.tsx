import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  Sparkles,
  Info,
  Layers,
  Server,
  Activity,
  CheckCircle2,
  AlertCircle,
  FileSearch,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ThemeToggle } from "@/components/common/theme-toggle";
import { getHealthInfo } from "@/services/chat";
import type { SystemHealth } from "@/types";

export const Route = createFileRoute("/settings")({
  component: SettingsPage,
});

function SettingsPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);

  useEffect(() => {
    getHealthInfo()
      .then(setHealth)
      .catch(() => setHealth(null))
      .finally(() => setHealthLoading(false));
  }, []);

  return (
    <div className="flex h-full flex-col bg-background">
      <div className="flex-1 overflow-y-auto p-4 md:p-8">
        <div className="mx-auto max-w-3xl space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Settings</h1>
            <p className="text-sm text-muted-foreground">
              Manage your appearance and view system information.
            </p>
          </div>

          {/* Appearance */}
          <Card className="border-border">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Layers className="h-5 w-5 text-primary" />
                <CardTitle className="text-base">Appearance</CardTitle>
              </div>
              <CardDescription>
                Customize how Manan AI looks on your device.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Theme</p>
                  <p className="text-xs text-muted-foreground">
                    Switch between light, dark, or system default mode.
                  </p>
                </div>
                <ThemeToggle />
              </div>
            </CardContent>
          </Card>

          {/* AI Model Configuration (Environment Driven) */}
          <Card className="border-border">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                <CardTitle className="text-base">AI Model</CardTitle>
              </div>
              <CardDescription>
                Configured via backend environment for optimal performance.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between rounded-xl bg-muted/40 p-3">
                <div className="flex items-center gap-2.5">
                  <Sparkles className="h-4 w-4 text-primary" />
                  <div>
                    <p className="text-xs font-semibold text-foreground">Google Gemini 3.6 Flash</p>
                    <p className="text-[11px] text-muted-foreground">Primary Generative Model</p>
                  </div>
                </div>
                <Badge variant="secondary" className="text-xs">Active</Badge>
              </div>

              <div className="flex items-center justify-between rounded-xl bg-muted/40 p-3">
                <div className="flex items-center gap-2.5">
                  <FileSearch className="h-4 w-4 text-primary" />
                  <div>
                    <p className="text-xs font-semibold text-foreground">Local / Gemini Embeddings</p>
                    <p className="text-[11px] text-muted-foreground">Vector RAG Retrieval</p>
                  </div>
                </div>
                <Badge variant="outline" className="text-xs">ChromaDB</Badge>
              </div>
            </CardContent>
          </Card>

          {/* System Information */}
          <Card className="border-border">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Server className="h-5 w-5 text-primary" />
                <CardTitle className="text-base">System Status</CardTitle>
              </div>
              <CardDescription>
                Connection and backend health information.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {healthLoading ? (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Activity className="h-3.5 w-3.5 animate-pulse" />
                  Checking backend status...
                </div>
              ) : health ? (
                <div className="space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Backend Status</span>
                    <span className="flex items-center gap-1 font-medium text-green-600 dark:text-green-400">
                      <CheckCircle2 className="h-3.5 w-3.5" /> Healthy
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Version</span>
                    <span className="font-mono text-foreground">{health.data?.version || "1.0.0"}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Mode</span>
                    <span className="font-mono text-foreground">{health.data?.mode || "anonymous-gemini"}</span>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-xs text-yellow-600 dark:text-yellow-400">
                  <AlertCircle className="h-3.5 w-3.5" />
                  Could not connect to backend at http://localhost:8001
                </div>
              )}
            </CardContent>
          </Card>

          {/* About */}
          <Card className="border-border">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Info className="h-5 w-5 text-primary" />
                <CardTitle className="text-base">About Manan AI V1</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-2 text-xs text-muted-foreground">
              <p>
                <strong>Manan AI V1</strong> is a lightweight, anonymous AI chat application powered directly by Google Gemini with optional document intelligence (RAG).
              </p>
              <p>
                Designed for private, instant, and frictionless knowledge retrieval.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
