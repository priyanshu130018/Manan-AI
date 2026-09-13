import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/hooks/use-theme";

export function ThemeToggle({ withLabel = false }: { withLabel?: boolean }) {
  const { theme, toggleTheme } = useTheme();

  return (
    <Button
      variant="ghost"
      onClick={toggleTheme}
      aria-label="Toggle color theme"
      className="w-full justify-start gap-3 rounded-xl text-sidebar-foreground hover:bg-sidebar-accent"
    >
      {theme === "dark" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
      {withLabel && (
        <span className="text-sm">{theme === "dark" ? "Dark mode" : "Light mode"}</span>
      )}
    </Button>
  );
}
