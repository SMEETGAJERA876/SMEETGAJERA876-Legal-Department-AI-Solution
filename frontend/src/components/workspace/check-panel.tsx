"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  CircleAlert,
  CircleCheck,
  Download,
  ExternalLink,
  LoaderCircle,
  ShieldAlert,
  Wand2,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { DownloadButton } from "@/components/system/download-button";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  documentDownloadPath,
  fetchIssues,
  repairDocument,
  type Issue,
  type RepairResult,
} from "@/lib/api";
import type { ShowSource } from "./source-quote";

type Props = {
  documentId: string;
  onShowSource: ShowSource;
  /** Demo documents are shared: the mistakes are listed, but nothing may be changed. */
  readOnly?: boolean;
};

export function CheckPanel({ documentId, onShowSource, readOnly = false }: Props) {
  const queryClient = useQueryClient();
  const { data, error, isPending } = useQuery({
    queryKey: ["issues", documentId],
    queryFn: () => fetchIssues(documentId),
  });
  // Fixes the user has unticked; everything fixable is selected by default.
  const [excluded, setExcluded] = useState<Set<string>>(new Set());
  const [confirming, setConfirming] = useState(false);

  const repair = useMutation({
    mutationFn: (ids: string[]) => repairDocument(documentId, ids),
    onSuccess: () => {
      setConfirming(false);
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  if (isPending) {
    return (
      <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
        <LoaderCircle className="size-4 animate-spin" aria-hidden />
        Checking the document for mistakes…
      </p>
    );
  }
  if (error) {
    return (
      <p className="text-sm text-danger" role="alert">
        {error.message}
      </p>
    );
  }

  const fixable = data.issues.filter((issue) => issue.fixable);
  const review = data.issues.filter((issue) => !issue.fixable);
  const selected = fixable.filter((issue) => !excluded.has(issue.id));
  const show = (issue: Issue) => onShowSource(issue.page_number, issue.context, issue.original);
  const toggle = (id: string) =>
    setExcluded((previous) => {
      const next = new Set(previous);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  if (repair.data) return <RepairDone result={repair.data} onShowSource={onShowSource} />;

  return (
    <section aria-labelledby="check-title" className="space-y-4">
      <div className="space-y-1">
        <h2 id="check-title" className="text-sm font-semibold">
          Check document
        </h2>
        <p className="text-xs text-muted-foreground">
          {data.issues.length === 0
            ? "No mistakes were found."
            : `${data.fixable_count} can be fixed automatically · ${data.review_count} need your review`}
        </p>
      </div>

      {data.issues.length === 0 && (
        <p className="flex items-start gap-2 rounded-lg border bg-card p-3 text-sm">
          <CircleCheck className="mt-0.5 size-4 shrink-0 text-success" aria-hidden />
          No spelling mistakes, repeated words, number mismatches, missing clauses, broken
          references, unclosed brackets or empty blanks were found.
        </p>
      )}

      {fixable.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Can be fixed automatically
          </h3>
          <ul className="space-y-2">
            {fixable.map((issue) => (
              <li key={issue.id} className="flex gap-2.5 rounded-lg border bg-card p-3">
                {!readOnly && (
                  <input
                    type="checkbox"
                    className="mt-1 size-4 accent-[var(--primary)]"
                    checked={!excluded.has(issue.id)}
                    onChange={() => toggle(issue.id)}
                    aria-label={`Fix “${issue.original}” on page ${issue.page_number}`}
                  />
                )}
                <IssueBody issue={issue} onShow={() => show(issue)} />
              </li>
            ))}
          </ul>
          {readOnly ? (
            <p className="rounded-lg border border-dashed bg-muted/40 p-3 text-xs text-muted-foreground">
              On your own document you could tick these and click <strong>Auto-repair</strong> to
              download a corrected PDF. The demo document is shared, so it is never changed.
            </p>
          ) : (
            <Button
              className="w-full"
              disabled={selected.length === 0}
              onClick={() => setConfirming(true)}
            >
              <Wand2 aria-hidden />
              Auto-repair {selected.length} {selected.length === 1 ? "mistake" : "mistakes"}
            </Button>
          )}
        </div>
      )}

      {review.length > 0 && (
        <div className="space-y-2">
          <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <ShieldAlert className="size-3.5" aria-hidden />
            Needs your review
          </h3>
          <p className="text-xs text-muted-foreground">
            These may change what the document means, so they are never changed
            automatically. Check them yourself or with the person who issued the document.
          </p>
          <ul className="space-y-2">
            {review.map((issue) => (
              <li key={issue.id} className="rounded-lg border border-warning/30 bg-amber-50/60 p-3">
                <IssueBody issue={issue} onShow={() => show(issue)} />
              </li>
            ))}
          </ul>
        </div>
      )}

      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        issues={selected}
        pending={repair.isPending}
        error={repair.error?.message ?? null}
        onConfirm={() => repair.mutate(selected.map((issue) => issue.id))}
      />
    </section>
  );
}

function IssueBody({ issue, onShow }: { issue: Issue; onShow: () => void }) {
  return (
    <div className="min-w-0 flex-1 space-y-1.5">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium">{issue.label}</p>
        <Badge variant="outline" className="shrink-0 bg-card">
          Page {issue.page_number}
        </Badge>
      </div>
      {issue.suggestion !== null ? (
        <p className="flex flex-wrap items-center gap-1.5 text-sm">
          <span className="rounded bg-red-50 px-1 text-danger line-through decoration-danger/60">
            {issue.original}
          </span>
          <ArrowRight className="size-3.5 text-muted-foreground" aria-label="change to" />
          <span className="rounded bg-green-50 px-1 font-medium text-success">
            {issue.suggestion}
          </span>
        </p>
      ) : (
        <p className="text-sm">
          <span className="rounded bg-amber-100/70 px-1 font-medium">{issue.original}</span>
        </p>
      )}
      <p className="text-xs text-muted-foreground">{issue.message}</p>
      <button
        type="button"
        onClick={onShow}
        className="text-xs font-medium text-primary underline-offset-2 hover:underline"
      >
        Show on page {issue.page_number}
      </button>
    </div>
  );
}

function ConfirmDialog({
  open,
  onOpenChange,
  issues,
  pending,
  error,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  issues: Issue[];
  pending: boolean;
  error: string | null;
  onConfirm: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={(next) => !pending && onOpenChange(next)}>
      <DialogContent className="max-h-[85dvh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            Do you really want to make {issues.length === 1 ? "this change" : `these ${issues.length} changes`}?
          </DialogTitle>
          <DialogDescription>
            A new corrected PDF will be created. Your original document will not be changed.
          </DialogDescription>
        </DialogHeader>
        <ul className="space-y-1.5 rounded-lg border bg-muted/40 p-3 text-sm">
          {issues.map((issue) => (
            <li key={issue.id} className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs font-medium text-muted-foreground">Page {issue.page_number}:</span>
              <span className="line-through decoration-danger/60">{issue.original}</span>
              <ArrowRight className="size-3.5 text-muted-foreground" aria-label="becomes" />
              <span className="font-medium text-success">{issue.suggestion}</span>
            </li>
          ))}
        </ul>
        <p className="flex gap-2 rounded-lg border border-warning/30 bg-amber-50 p-3 text-xs text-foreground/80">
          <CircleAlert className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden />
          If this document is signed, stamped or officially issued, a corrected copy is not a
          replacement for it. Ask the issuer, or a qualified legal professional, before using it.
        </p>
        {error && (
          <p className="text-sm text-danger" role="alert">
            {error}
          </p>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>
            Cancel
          </Button>
          <Button onClick={onConfirm} disabled={pending}>
            {pending ? <LoaderCircle className="animate-spin" /> : <Wand2 />}
            Yes, make the changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RepairDone({
  result,
  onShowSource,
}: {
  result: RepairResult;
  onShowSource: ShowSource;
}) {
  const failedFixes = result.not_applied.filter((item) => item.issue.fixable);
  const reviewLeft = result.not_applied.length - failedFixes.length;
  return (
    <section className="space-y-3" aria-live="polite">
      <div className="space-y-2 rounded-lg border border-success/30 bg-green-50 p-3">
        <p className="flex items-center gap-2 text-sm font-semibold text-success">
          <CircleCheck className="size-4" aria-hidden />
          Corrected PDF created
        </p>
        <p className="text-sm">
          {result.applied.length} {result.applied.length === 1 ? "change was" : "changes were"}{" "}
          made in <span className="font-medium">{result.document.original_filename}</span>. Your
          original document is unchanged.
        </p>
        <ul className="space-y-1 text-sm">
          {result.applied.map((issue) => (
            <li key={issue.id}>
              <button
                type="button"
                className="text-left hover:underline"
                onClick={() => onShowSource(issue.page_number, issue.context, issue.original)}
              >
                Page {issue.page_number}: <span className="line-through">{issue.original}</span>{" "}
                → <span className="font-medium">{issue.suggestion}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
      {failedFixes.length > 0 && (
        <div className="rounded-lg border border-warning/30 bg-amber-50 p-3 text-sm" role="alert">
          <p className="font-medium">Not changed:</p>
          <ul className="list-disc pl-5">
            {failedFixes.map((item) => (
              <li key={item.issue.id}>
                “{item.issue.original}” (page {item.issue.page_number}) — {item.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
      {reviewLeft > 0 && (
        <p className="text-xs text-muted-foreground">
          {reviewLeft} {reviewLeft === 1 ? "item still needs" : "items still need"} your review
          and {reviewLeft === 1 ? "was" : "were"} not changed.
        </p>
      )}
      <div className="flex flex-col gap-2">
        <DownloadButton
          path={documentDownloadPath(result.document.id)}
          fallbackName={result.document.original_filename}
        >
          <Download aria-hidden />
          Download corrected PDF
        </DownloadButton>
        <Button
          variant="outline"
          nativeButton={false}
          render={<Link href={`/documents/${result.document.id}`} />}
        >
          <ExternalLink aria-hidden />
          Open corrected copy
        </Button>
      </div>
    </section>
  );
}
