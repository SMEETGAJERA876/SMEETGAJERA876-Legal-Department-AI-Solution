"use client";

import { useQuery } from "@tanstack/react-query";
import {
  CalendarDays,
  FileDown,
  FileText,
  ListChecks,
  LoaderCircle,
  TriangleAlert,
  Wallet,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { downloadFromApi, documentSummaryPath, fetchOverview } from "@/lib/api";
import { formatSource } from "@/lib/format";
import { ClassificationCard } from "./classification-card";
import type { ShowSource } from "./source-quote";

type Props = { documentId: string; onShowSource: ShowSource };

export function OverviewPanel({ documentId, onShowSource }: Props) {
  const { data, error, isPending } = useQuery({
    queryKey: ["overview", documentId],
    queryFn: () => fetchOverview(documentId),
  });

  if (isPending) {
    return (
      <div className="space-y-3" aria-busy="true">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }
  if (error) {
    return (
      <p className="text-sm text-danger" role="alert">
        {error.message}
      </p>
    );
  }

  const { document, counts, concepts } = data;
  return (
    <div className="space-y-5">
      <section aria-labelledby="doc-summary-title" className="space-y-2">
        <h2 id="doc-summary-title" className="sr-only">
          Document summary
        </h2>
        <ClassificationCard document={document} />
        {document.parties.length > 0 && (
          <p className="text-sm text-muted-foreground">
            Between <span className="text-foreground">{document.parties.join(" and ")}</span>
          </p>
        )}
        <ul className="grid grid-cols-2 gap-2 text-sm">
          <Stat icon={<FileText />} label="pages" value={counts.pages} />
          <Stat icon={<ListChecks />} label="clauses" value={counts.clauses} />
          <Stat icon={<CalendarDays />} label="dates" value={counts.dates} />
          <Stat icon={<Wallet />} label="money items" value={counts.payments} />
          {counts.attention > 0 && (
            <Stat
              icon={<TriangleAlert />}
              label="items to review carefully"
              value={counts.attention}
              wide
            />
          )}
        </ul>
      </section>

      <SummaryDownloadCard documentId={documentId} />

      {document.changes.length > 0 && (
        <section
          aria-labelledby="changes-title"
          className="space-y-2 rounded-lg border border-success/30 bg-green-50/60 p-3"
        >
          <h2 id="changes-title" className="text-sm font-semibold">
            Changes in this corrected copy
          </h2>
          <ul className="space-y-1 text-sm">
            {document.changes.map((change, index) => (
              <li key={index}>
                <button
                  type="button"
                  className="text-left hover:underline"
                  onClick={() => onShowSource(change.page_number, null)}
                >
                  Page {change.page_number}:{" "}
                  <span className="line-through decoration-danger/60">{change.original}</span> →{" "}
                  <span className="font-medium">{change.replacement}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section aria-labelledby="important-info-title" className="space-y-3">
        <h2 id="important-info-title" className="text-sm font-semibold">
          Important information
        </h2>
        {concepts.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No notice periods, payments, dates or other key terms were detected automatically. You
            can still search or ask questions about the document.
          </p>
        )}
        {concepts.map((concept) => (
          <div key={concept.concept} className="rounded-lg border bg-card p-3">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {concept.label}
            </h3>
            <ul className="space-y-1.5">
              {concept.facts.map((fact, index) => (
                <li key={`${fact.value}-${index}`}>
                  <button
                    type="button"
                    onClick={() => onShowSource(fact.source.page_number, fact.source.quote)}
                    aria-label={`${fact.value}, ${formatSource(fact.source.page_number, fact.source.clause_ref)}. Show in document`}
                    className="group flex w-full items-start justify-between gap-2 rounded-md px-1.5 py-1 text-left text-sm hover:bg-accent focus-visible:outline-2 focus-visible:outline-ring"
                  >
                    <span className="line-clamp-2">{fact.value}</span>
                    <Badge variant="outline" className="shrink-0 group-hover:border-primary/50">
                      {formatSource(fact.source.page_number, fact.source.clause_ref)}
                    </Badge>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </section>
    </div>
  );
}

function Stat({
  icon,
  label,
  value,
  wide = false,
}: {
  icon: ReactNode;
  label: string;
  value: number | undefined;
  wide?: boolean;
}) {
  return (
    <li
      className={`flex items-center gap-2 rounded-lg border bg-card px-2.5 py-2 [&_svg]:size-4 [&_svg]:text-primary ${wide ? "col-span-2" : ""}`}
    >
      {icon}
      <span>
        <span className="font-semibold tabular-nums">{value ?? 0}</span>{" "}
        <span className="text-muted-foreground">{label}</span>
      </span>
    </li>
  );
}

function SummaryDownloadCard({ documentId }: { documentId: string }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function download() {
    setPending(true);
    setError(null);
    try {
      await downloadFromApi(documentSummaryPath(documentId), "summary.pdf");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The download didn't work.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-1">
      <button
        type="button"
        onClick={() => void download()}
        disabled={pending}
        aria-busy={pending}
        className="flex w-full items-start gap-3 rounded-lg border border-primary/30 bg-accent/50 p-3 text-left hover:border-primary/60 focus-visible:outline-2 focus-visible:outline-ring disabled:opacity-70"
      >
        {pending ? (
          <LoaderCircle className="mt-0.5 size-5 shrink-0 animate-spin text-primary" aria-hidden />
        ) : (
          <FileDown className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden />
        )}
        <span>
          <span className="block text-sm font-semibold">Download summary PDF</span>
          <span className="block text-xs text-muted-foreground">
            Key dates, notice periods, deadlines, amounts, items to review and questions for a
            legal professional — each with its page — in one file.
          </span>
        </span>
      </button>
      {error && (
        <p role="alert" className="text-xs text-danger">
          Download failed: {error}
        </p>
      )}
    </div>
  );
}
