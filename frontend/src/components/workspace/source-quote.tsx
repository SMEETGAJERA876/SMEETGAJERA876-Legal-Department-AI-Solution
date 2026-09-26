"use client";

import { useMutation } from "@tanstack/react-query";
import { ArrowUpRight, FileText, LoaderCircle, Languages } from "lucide-react";
import { Button } from "@/components/ui/button";
import { simplifyText, type Source } from "@/lib/api";
import { formatSource } from "@/lib/format";

export type ShowSource = (page: number, quote: string | null, focus?: string | null) => void;

type Props = {
  source: Source;
  onShowSource: ShowSource;
  label?: string;
  /** Document id: when given, the reader can ask for this wording in everyday words. */
  simplifyFor?: string;
};

/** Original wording from the document plus a button that jumps to it in the viewer. */
export function SourceQuote({ source, onShowSource, label = "View in document", simplifyFor }: Props) {
  const simplify = useMutation({
    mutationFn: () => simplifyText(simplifyFor as string, source.quote),
  });
  const plain = simplify.data;

  return (
    <figure className="rounded-lg border bg-muted/40 p-3">
      <blockquote className="border-l-2 border-primary/40 pl-3 text-sm leading-relaxed text-foreground/90">
        “{source.quote}”
      </blockquote>

      {plain && (
        <div className="mt-2 space-y-1 rounded-md border border-primary/20 bg-accent p-2.5">
          <p className="flex items-center gap-1.5 text-xs font-semibold tracking-wide text-primary uppercase">
            <Languages className="size-3.5" aria-hidden />
            In simple words
          </p>
          {plain.worth_showing ? (
            <p className="text-sm leading-relaxed">{plain.simple}</p>
          ) : (
            <p className="text-sm text-muted-foreground">
              This passage is already in everyday words.
            </p>
          )}
          {plain.terms.length > 0 && (
            <dl className="space-y-0.5 pt-1">
              {plain.terms.map(({ legal, plain: meaning }) => (
                <div key={legal} className="flex flex-wrap gap-x-1.5 text-xs">
                  <dt className="font-medium">“{legal}”</dt>
                  <dd className="text-muted-foreground">means {meaning}</dd>
                </div>
              ))}
            </dl>
          )}
          <p className="pt-1 text-xs text-muted-foreground">
            A simplified version. The original wording above is what counts.
          </p>
        </div>
      )}
      {simplify.error && (
        <p className="mt-2 text-xs text-danger" role="alert">
          {simplify.error.message}
        </p>
      )}

      <figcaption className="mt-2 flex flex-wrap items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
          <FileText className="size-3.5" aria-hidden />
          {formatSource(source.page_number, source.clause_ref)}
          {source.heading ? ` · ${source.heading}` : ""}
        </span>
        <span className="flex flex-wrap items-center gap-2">
          {simplifyFor && !plain && (
            <Button
              variant="outline"
              size="xs"
              disabled={simplify.isPending}
              onClick={() => simplify.mutate()}
            >
              {simplify.isPending ? (
                <LoaderCircle className="animate-spin" aria-hidden />
              ) : (
                <Languages aria-hidden />
              )}
              Simple words
            </Button>
          )}
          <Button
            variant="outline"
            size="xs"
            onClick={() => onShowSource(source.page_number, source.quote)}
          >
            {label}
            <ArrowUpRight data-icon="inline-end" aria-hidden />
          </Button>
        </span>
      </figcaption>
    </figure>
  );
}
