import { Info } from "lucide-react";
import { cn } from "@/lib/utils";

export function Disclaimer({ className }: { className?: string }) {
  return (
    <p className={cn("flex items-center gap-1.5 text-xs text-muted-foreground", className)}>
      <Info className="size-3.5 shrink-0" aria-hidden />
      ClauseLens gives information about your document, not legal advice. For decisions, consult a
      qualified legal professional.
    </p>
  );
}
