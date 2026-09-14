import { useEffect, useState } from "react";
import { Link, useRouterState, useNavigate } from "@tanstack/react-router";
import {
  FileText,
  Settings,

  Plus,
  Trash2,
  Sparkle,
  Loader2,
  MoreVertical,
  Pencil,
  HardDrive,
  PanelLeftClose,
  PanelLeft,
  User as UserIcon,
  LogIn,
  UserPlus,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Progress } from "@/components/ui/progress";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useAuth } from "@/hooks/use-auth";
import { useSessions } from "@/hooks/use-sessions";
import { getStorageUsage } from "@/services/document";
import { cn } from "@/lib/utils";
import type { StorageUsage } from "@/types";

export interface SidebarContentProps {
  onNavigate?: () => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function SidebarContentPanel({
  onNavigate,
  collapsed = false,
  onToggleCollapse,
}: SidebarContentProps) {
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { user } = useAuth();
  const {
    sessions,
    activeId,
    selectSession,
    newChat,
    deleteSession,
    renameSession,
    deletingId,
  } = useSessions();

  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null);
  const [renameTarget, setRenameTarget] = useState<{ id: string; title: string } | null>(null);
  const [renameTitle, setRenameTitle] = useState("");
  const [storage, setStorage] = useState<StorageUsage | null>(null);

  const loadStorage = () => {
    if (!user) {
      setStorage(null);
      return;
    }
    getStorageUsage()
      .then(setStorage)
      .catch(() => setStorage(null));
  };

  useEffect(() => {
    if (user) {
      loadStorage();
      const interval = setInterval(loadStorage, 15000);
      return () => clearInterval(interval);
    } else {
      setStorage(null);
    }
  }, [user]);

  const handleConfirmDelete = async () => {
    if (!deleteTarget || !user) return;
    try {
      await deleteSession(deleteTarget.id);
      toast.success("Chat deleted");
      newChat();
      navigate({ to: "/" });
    } catch {
      toast.error("Could not delete chat");
    } finally {
      setDeleteTarget(null);
    }
  };

  const handleConfirmRename = () => {
    if (!renameTarget || !renameTitle.trim() || !user) return;
    renameSession(renameTarget.id, renameTitle.trim());
    toast.success("Chat renamed");
    setRenameTarget(null);
  };

  const handleBrandClick = () => {
    newChat();
    navigate({ to: "/" });
    onNavigate?.();
  };

  const handleNewChatClick = () => {
    newChat();
    navigate({ to: "/" });
    onNavigate?.();
  };


  return (
    <TooltipProvider delayDuration={150}>
      <div
        className={cn(
          "flex h-full flex-col bg-sidebar text-sidebar-foreground transition-all duration-200",
          collapsed ? "items-center px-2 py-3 gap-3" : "p-3 gap-3",
        )}
      >
        {/* Brand Header */}
        {collapsed ? (
          <div className="flex flex-col items-center gap-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={handleBrandClick}
                  className="grid h-10 w-10 place-items-center rounded-xl bg-primary text-primary-foreground shadow-sm transition-transform hover:scale-105"
                  aria-label="Manan AI — Start new chat"
                >
                  <Sparkle className="h-5 w-5" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">Manan AI</TooltipContent>
            </Tooltip>

            {onToggleCollapse && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={onToggleCollapse}
                    className="h-8 w-8 text-muted-foreground hover:text-foreground"
                    aria-label="Expand sidebar"
                  >
                    <PanelLeft className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">Expand sidebar</TooltipContent>
              </Tooltip>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-between px-2 pt-1">
            <button
              type="button"
              onClick={handleBrandClick}
              className="flex items-center gap-2.5 text-left transition-opacity hover:opacity-80 focus:outline-none"
              aria-label="Manan AI — Start new chat"
            >
              <div className="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-primary text-primary-foreground shadow-sm">
                <Sparkle className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold tracking-tight text-foreground">
                  Manan AI
                </p>
              </div>
            </button>

            {onToggleCollapse && (
              <Button
                size="icon"
                variant="ghost"
                onClick={onToggleCollapse}
                className="h-8 w-8 text-muted-foreground hover:text-foreground"
                aria-label="Collapse sidebar"
              >
                <PanelLeftClose className="h-4 w-4" />
              </Button>
            )}
          </div>
        )}

        {/* New Chat Button */}
        {collapsed ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                size="icon"
                variant="outline"
                className="h-9 w-9 rounded-xl border-sidebar-border bg-sidebar-accent/40 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                onClick={handleNewChatClick}
                aria-label="New chat"
              >
                <Plus className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">New Chat</TooltipContent>
          </Tooltip>
        ) : (
          <Button
            variant="outline"
            className="w-full justify-start gap-2 rounded-xl border-sidebar-border bg-sidebar-accent/40 font-medium hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            onClick={handleNewChatClick}
          >
            <Plus className="h-4 w-4" />
            New Chat
          </Button>
        )}

        {/* Primary Navigation */}
        <nav className={cn("space-y-1 w-full", collapsed && "flex flex-col items-center")}>
          {collapsed ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <Link
                  to="/doc"
                  onClick={onNavigate}
                  className={cn(
                    "grid h-9 w-9 place-items-center rounded-xl transition-colors",
                    pathname.startsWith("/doc")
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
                  )}
                  aria-label="Documents"
                >
                  <FileText className="h-4 w-4" />
                </Link>
              </TooltipTrigger>
              <TooltipContent side="right">Documents</TooltipContent>
            </Tooltip>
          ) : (
            <Link
              to="/doc"
              onClick={onNavigate}
              className={cn(
                "flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
                pathname.startsWith("/doc")
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
              )}
            >
              <FileText className="h-4 w-4 shrink-0" />
              Documents
            </Link>
          )}
        </nav>


        {/* Chat History List (Only for Authenticated Users in Expanded mode) */}
        {!collapsed && user && (
          <div className="flex min-h-0 flex-1 flex-col gap-1.5 border-t border-sidebar-border pt-2.5">
            <div className="flex items-center justify-between px-2">
              <span className="text-[11px] font-medium tracking-wider text-muted-foreground uppercase">
                Chat History
              </span>
            </div>

            <ScrollArea className="min-h-0 flex-1">
              <div className="space-y-0.5 pr-2">
                {sessions.map((session) => {
                  const isActive = session.id === activeId;
                  return (
                    <div
                      key={session.id}
                      className={cn(
                        "group flex items-center justify-between rounded-xl px-2 py-1.5 transition-colors",
                        isActive
                          ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                          : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground",
                      )}
                    >
                      {session.chat_number ? (
                        <Link
                          to="/chat/$chatNumber"
                          params={{ chatNumber: session.chat_number }}
                          onClick={() => {
                            selectSession(session.id);
                            onNavigate?.();
                          }}
                          className="min-w-0 flex-1 truncate text-left text-xs"
                        >
                          {session.title || "New conversation"}
                        </Link>
                      ) : (
                        <Link
                          to="/chat"
                          onClick={() => {
                            selectSession(session.id);
                            onNavigate?.();
                          }}
                          className="min-w-0 flex-1 truncate text-left text-xs"
                        >
                          {session.title || "New conversation"}
                        </Link>
                      )}

                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            size="icon"
                            variant="ghost"
                            className={cn(
                              "h-6 w-6 shrink-0 rounded-md opacity-0 transition-opacity group-hover:opacity-100",
                              isActive && "opacity-100",
                            )}
                            aria-label="Session options"
                          >
                            {deletingId === session.id ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <MoreVertical className="h-3.5 w-3.5" />
                            )}
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-36">
                          <DropdownMenuItem
                            onClick={() => {
                              setRenameTarget({ id: session.id, title: session.title || "New conversation" });
                              setRenameTitle(session.title || "");
                            }}
                          >
                            <Pencil className="mr-2 h-3.5 w-3.5" />
                            Rename
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={() =>
                              setDeleteTarget({ id: session.id, title: session.title || "New conversation" })
                            }
                          >
                            <Trash2 className="mr-2 h-3.5 w-3.5" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          </div>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Storage Capacity Indicator (Authenticated + Expanded mode only) */}
        {!collapsed && user && storage && (
          <div className="rounded-xl border border-sidebar-border bg-sidebar-accent/30 p-2.5 text-xs">
            <div className="mb-1.5 flex items-center justify-between text-[11px] text-muted-foreground">
              <span className="flex items-center gap-1.5 font-medium">
                <HardDrive className="h-3.5 w-3.5" /> Storage
              </span>
              <span>
                {storage.used_mb} MB / {storage.limit_mb} MB
              </span>
            </div>
            <Progress value={storage.usage_percent} className="h-1.5" />
          </div>
        )}

        {/* Footer Navigation (Profile + Settings) */}
        <div className={cn("w-full border-t border-sidebar-border pt-2 space-y-1", collapsed && "flex flex-col items-center")}>
          {/* Profile (Only for Authenticated Users) */}
          {user && (
            <>
              {collapsed ? (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Link
                      to="/profile"
                      onClick={onNavigate}
                      className={cn(
                        "grid h-9 w-9 place-items-center rounded-xl transition-colors",
                        pathname.startsWith("/profile")
                          ? "bg-sidebar-accent text-sidebar-accent-foreground"
                          : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
                      )}
                      aria-label="Profile"
                    >
                      <UserIcon className="h-4 w-4" />
                    </Link>
                  </TooltipTrigger>
                  <TooltipContent side="right">Profile</TooltipContent>
                </Tooltip>
              ) : (
                <Link
                  to="/profile"
                  onClick={onNavigate}
                  className={cn(
                    "flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
                    pathname.startsWith("/profile")
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
                  )}
                >
                  <UserIcon className="h-4 w-4 shrink-0" />
                  Profile
                </Link>
              )}
            </>
          )}

          {/* Settings (Accessible to all) */}
          {collapsed ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <Link
                  to="/settings"
                  onClick={onNavigate}
                  className={cn(
                    "grid h-9 w-9 place-items-center rounded-xl transition-colors",
                    pathname.startsWith("/settings")
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
                  )}
                  aria-label="Settings"
                >
                  <Settings className="h-4 w-4" />
                </Link>
              </TooltipTrigger>
              <TooltipContent side="right">Settings</TooltipContent>
            </Tooltip>
          ) : (
            <Link
              to="/settings"
              onClick={onNavigate}
              className={cn(
                "flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
                pathname.startsWith("/settings")
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
              )}
            >
              <Settings className="h-4 w-4 shrink-0" />
              Settings
            </Link>
          )}
        </div>

        {/* Rename Dialog */}
        <Dialog open={Boolean(renameTarget)} onOpenChange={(open) => !open && setRenameTarget(null)}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle>Rename Chat</DialogTitle>
              <DialogDescription>Enter a new title for this conversation.</DialogDescription>
            </DialogHeader>
            <div className="py-2">
              <Input
                value={renameTitle}
                onChange={(e) => setRenameTitle(e.target.value)}
                placeholder="Chat title..."
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleConfirmRename();
                }}
                autoFocus
              />
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setRenameTarget(null)}>
                Cancel
              </Button>
              <Button onClick={handleConfirmRename}>Save</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Alert Dialog */}
        <AlertDialog open={Boolean(deleteTarget)} onOpenChange={(o) => !o && setDeleteTarget(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete chat?</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to delete{" "}
                <strong>&ldquo;{deleteTarget?.title}&rdquo;</strong>? This will remove this
                conversation history.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                onClick={handleConfirmDelete}
              >
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </TooltipProvider>
  );
}
