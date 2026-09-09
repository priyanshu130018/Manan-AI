import { Link, useRouterState } from "@tanstack/react-router";
import { MessageSquare, Upload, FileText, Settings, Plus, Trash2, Sparkle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ThemeToggle } from "@/components/common/theme-toggle";
import { useSessions } from "@/hooks/use-sessions";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/chat", label: "Chat", icon: MessageSquare },
  { to: "/upload", label: "Upload", icon: Upload },
  { to: "/documents", label: "Documents", icon: FileText },
  { to: "/settings", label: "Settings", icon: Settings },
] as const;

export function SidebarContentPanel({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { sessions, activeId, selectSession, newChat, deleteSession } = useSessions();

  return (
    <div className="flex h-full flex-col gap-4 bg-sidebar p-3 text-sidebar-foreground">
      <div className="flex items-center gap-3 px-2 pt-2">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-primary text-primary-foreground shadow-soft">
          <Sparkle className="h-4 w-4" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">Manan AI</p>
          <p className="truncate text-xs text-muted-foreground">RAG assistant</p>
        </div>
      </div>

      <nav className="space-y-1">
        {NAV.map(({ to, label, icon: Icon }) => {
          const active = pathname.startsWith(to);
          return (
            <Link
              key={to}
              to={to}
              onClick={onNavigate}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="flex min-h-0 flex-1 flex-col gap-2 border-t border-sidebar-border pt-3">
        <div className="flex items-center justify-between px-2">
          <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
            Conversations
          </span>
          <Button
            size="icon"
            variant="ghost"
            className="h-7 w-7 rounded-lg"
            aria-label="New chat"
            onClick={() => {
              newChat();
              onNavigate?.();
            }}
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        <ScrollArea className="min-h-0 flex-1">
          <div className="space-y-1 pr-2">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={cn(
                  "group flex items-center gap-1 rounded-xl px-2 py-1.5 transition-colors",
                  session.id === activeId
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "hover:bg-sidebar-accent/60",
                )}
              >
                <Link
                  to="/chat"
                  onClick={() => {
                    selectSession(session.id);
                    onNavigate?.();
                  }}
                  className="min-w-0 flex-1 truncate text-left text-sm"
                >
                  {session.title || "New chat"}
                </Link>
                <Button
                  size="icon"
                  variant="ghost"
                  aria-label={`Delete ${session.title}`}
                  className="h-6 w-6 shrink-0 rounded-md opacity-0 transition-opacity group-hover:opacity-100"
                  onClick={() => deleteSession(session.id)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </div>
        </ScrollArea>
      </div>

      <div className="border-t border-sidebar-border pt-2">
        <ThemeToggle withLabel />
      </div>
    </div>
  );
}
