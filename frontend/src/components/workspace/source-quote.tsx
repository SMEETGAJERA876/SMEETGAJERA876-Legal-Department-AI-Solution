import { ArrowUpRight, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { formatSource } from "@/lib/format";
import type { Source } from "@/lib/api";

export type ShowSource = (page: number, quote: string | null, focus?: string | null) => void;

type Props = {
  source: Source;
  onShowSource: ShowSource;
  label?: string;
};

/** Original wording from the document plus a button that jumps to it in the viewer. */
export function SourceQuote({ source, onShowSource, label = "View in document" }: Props) {
  return (
    <figure className="rounded-lg border bg-muted/40 p-3">
      <blockquote className="border-l-2 border-primary/40 pl-3 text-sm leading-relaxed text-foreground/90">
        “{source.quote}”
      </blockquote>
      <figcaption className="mt-2 flex flex-wrap items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
          <FileText className="size-3.5" aria-hidden />
          {formatSource(source.page_number, source.clause_ref)}
          {source.heading ? ` · ${source.heading}` : ""}
        </span>
        <Button
          variant="outline"
          size="xs"
          onClick={() => onShowSource(source.page_number, source.quote)}
        >
          {label}
          <ArrowUpRight data-icon="inline-end" aria-hidden />
        </Button>
      </figcaption>
    </figure>
  );
}
