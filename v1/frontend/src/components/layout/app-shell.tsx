import { useState, useEffect, type ReactNode } from "react";
import { useRouterState, useNavigate, Link } from "@tanstack/react-router";
import { Menu, Sparkle, Loader2, LogIn, UserPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet";
import { SidebarContentPanel } from "./app-sidebar";
import { ErrorBoundary } from "@/components/common/error-boundary";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

const SIDEBAR_COLLAPSED_KEY = "manan:sidebar_collapsed";

export function AppShell({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { user, loading } = useAuth();

  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "true";
    } catch {
      return false;
    }
  });

  const isAuthPage = pathname === "/login" || pathname === "/signup";
  // Protected routes that strictly require login:
  const isStrictlyProtectedRoute = pathname.startsWith("/profile") || pathname.startsWith("/documents") || pathname.startsWith("/upload");

  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(collapsed));
    } catch {
      // Ignore storage errors
    }
  }, [collapsed]);

  useEffect(() => {
    if (!loading && !user && isStrictlyProtectedRoute) {
      navigate({
        to: "/login",
        search: { redirect: pathname },
      });
    }
  }, [loading, user, isStrictlyProtectedRoute, pathname, navigate]);

  const toggleCollapsed = () => {
    setCollapsed((prev) => !prev);
  };

  if (loading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3 text-muted-foreground">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-primary text-primary-foreground shadow-sm">
            <Sparkle className="h-6 w-6 animate-pulse" />
          </div>
          <p className="text-sm font-medium">Loading Manan AI...</p>
        </div>
      </div>
    );
  }

  // Auth pages (login, signup) render standalone without sidebar
  if (isAuthPage) {
    return (
      <div className="min-h-screen w-full bg-background">
        <ErrorBoundary>{children}</ErrorBoundary>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      <aside
        className={cn(
          "hidden shrink-0 border-r border-sidebar-border transition-all duration-200 md:block",
          collapsed ? "w-[68px]" : "w-72",
        )}
      >
        <SidebarContentPanel
          collapsed={collapsed}
          onToggleCollapse={toggleCollapsed}
        />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile Header */}
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-border px-3 md:hidden">
          <div className="flex items-center gap-3">
            <Sheet open={open} onOpenChange={setOpen}>
              <SheetTrigger asChild>
                <Button size="icon" variant="ghost" aria-label="Open navigation">
                  <Menu className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-72 p-0">
                <SheetTitle className="sr-only">Navigation</SheetTitle>
                <SidebarContentPanel onNavigate={() => setOpen(false)} />
              </SheetContent>
            </Sheet>
            <div className="flex min-w-0 items-center gap-2">
              <div className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-primary text-primary-foreground">
                <Sparkle className="h-3.5 w-3.5" />
              </div>
              <span className="truncate text-sm font-semibold">Manan AI</span>
            </div>
          </div>

          {!user && (
            <div className="flex items-center gap-1.5">
              <Button variant="ghost" size="sm" className="h-8 px-2 text-xs" asChild>
                <Link to="/login" search={{ redirect: pathname }}>
                  Log in
                </Link>
              </Button>
              <Button size="sm" className="h-8 px-2.5 text-xs" asChild>
                <Link to="/signup" search={{ redirect: pathname }}>
                  Sign up
                </Link>
              </Button>
            </div>
          )}
        </header>

        <main className="min-h-0 flex-1 overflow-hidden">
          <ErrorBoundary>{children}</ErrorBoundary>
        </main>
      </div>
    </div>
  );
}
