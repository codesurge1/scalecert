import { Toaster as SonnerToaster } from "sonner";
import { useTheme } from "@/hooks/useTheme";

// Simplified from shadcn's sonner.tsx: no next-themes here (not a Next app),
// so it follows this app's own theme store (hooks/useTheme.js) instead.
function Toaster(props) {
  const { resolved } = useTheme();
  return (
    <SonnerToaster
      theme={resolved}
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-card group-[.toaster]:text-card-foreground group-[.toaster]:border-border group-[.toaster]:shadow-lg",
          description: "group-[.toast]:text-muted-foreground",
          actionButton: "group-[.toast]:bg-primary group-[.toast]:text-primary-foreground",
          cancelButton: "group-[.toast]:bg-muted group-[.toast]:text-muted-foreground",
        },
      }}
      {...props}
    />
  );
}

export { Toaster };
