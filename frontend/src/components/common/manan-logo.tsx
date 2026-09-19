import { forwardRef } from "react";
import { Link } from "@tanstack/react-router";
import { Sparkle } from "lucide-react";
import { cn } from "@/lib/utils";

export interface MananLogoProps {
  /** Size variant for the logo icon box */
  size?: "sm" | "default" | "lg" | "xl";
  /** Whether to only show the icon and omit the wordmark */
  iconOnly?: boolean;
  /** Explicitly toggle wordmark visibility (defaults to !iconOnly) */
  showWordmark?: boolean;
  /** Custom wordmark title text (defaults to "Manan AI") */
  wordmarkText?: string;
  /** Optional subtitle text below the wordmark */
  subtitle?: string;
  /** Additional classes for the root container / link */
  className?: string;
  /** Additional classes for the wordmark text */
  wordmarkClassName?: string;
  /** Additional classes for the icon container */
  iconClassName?: string;
  /** Additional classes for the Sparkle icon itself */
  sparkleClassName?: string;
  /** Accessible label for screen readers and link semantics */
  ariaLabel?: string;
  /** Whether to render as a clickable Home link (default: true) */
  asLink?: boolean;
  /** Click callback (e.g. for closing drawers or resetting state) */
  onClick?: () => void;
  /** Layout orientation: "horizontal" (default) or "vertical" */
  layout?: "horizontal" | "vertical";
}

const SIZE_CONFIG = {
  sm: {
    container: "h-7 w-7 rounded-lg",
    icon: "h-3.5 w-3.5",
  },
  default: {
    container: "h-8 w-8 rounded-xl",
    icon: "h-4 w-4",
  },
  lg: {
    container: "h-10 w-10 rounded-xl",
    icon: "h-5 w-5",
  },
  xl: {
    container: "h-12 w-12 rounded-2xl",
    icon: "h-6 w-6",
  },
} as const;

export const MananLogo = forwardRef<HTMLAnchorElement & HTMLDivElement, MananLogoProps>(
  (
    {
      size = "default",
      iconOnly = false,
      showWordmark,
      wordmarkText = "Manan AI",
      subtitle,
      className,
      wordmarkClassName,
      iconClassName,
      sparkleClassName,
      ariaLabel = "Manan AI home",
      asLink = true,
      onClick,
      layout = "horizontal",
    },
    ref,
  ) => {
    const shouldShowWordmark = showWordmark !== undefined ? showWordmark : !iconOnly;
    const sizeConfig = SIZE_CONFIG[size] || SIZE_CONFIG.default;

    const content = (
      <>
        <div
          className={cn(
            "grid place-items-center shrink-0 bg-primary text-primary-foreground shadow-sm select-none",
            sizeConfig.container,
            iconClassName,
          )}
          aria-hidden="true"
        >
          <Sparkle className={cn(sizeConfig.icon, sparkleClassName)} />
        </div>

        {shouldShowWordmark && (
          <div className={cn("min-w-0 text-left", layout === "vertical" && "text-center")}>
            <p
              className={cn(
                "truncate text-sm font-semibold tracking-tight text-foreground select-none",
                wordmarkClassName,
              )}
            >
              {wordmarkText}
            </p>
            {subtitle && (
              <p className="truncate text-xs text-muted-foreground select-none">{subtitle}</p>
            )}
          </div>
        )}
      </>
    );

    const baseClasses = cn(
      "group inline-flex items-center gap-2.5 transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-xl",
      layout === "vertical" && "flex-col gap-2 text-center",
      asLink && "cursor-pointer hover:opacity-85 active:scale-[0.98]",
      className,
    );

    if (asLink) {
      return (
        <Link
          to="/"
          ref={ref as React.ForwardedRef<HTMLAnchorElement>}
          aria-label={ariaLabel}
          onClick={onClick}
          className={baseClasses}
        >
          {content}
        </Link>
      );
    }

    return (
      <div ref={ref as React.ForwardedRef<HTMLDivElement>} className={baseClasses}>
        {content}
      </div>
    );
  },
);

MananLogo.displayName = "MananLogo";
