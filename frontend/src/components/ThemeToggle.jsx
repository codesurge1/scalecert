import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import { nextPreference } from "@/lib/theme";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const ICONS = { light: Sun, dark: Moon, system: Monitor };
const LABELS = { light: "Light", dark: "Dark", system: "System" };

/**
 * One button, cycling light → dark → system. The icon shows the CURRENT
 * preference (a monitor for "system", not whichever of sun/moon it happens
 * to resolve to), so the user can always tell an explicit choice from
 * "following the OS". `showLabel` adds the word beside the icon, for the
 * roomier sidebar footer; everywhere else it's icon-only with an
 * aria-label/title that also names the next step.
 */
export function ThemeToggle({ className, showLabel = false }) {
  const { preference, setPreference } = useTheme();
  const next = nextPreference(preference);
  const Icon = ICONS[preference];
  const label = `Theme: ${LABELS[preference]} (switch to ${LABELS[next]})`;

  return (
    <Button
      type="button"
      variant="ghost"
      size={showLabel ? "sm" : "icon"}
      className={cn(showLabel && "justify-start", className)}
      onClick={() => setPreference(next)}
      aria-label={label}
      title={label}
    >
      <Icon />
      {showLabel ? <span>Theme: {LABELS[preference]}</span> : null}
    </Button>
  );
}
