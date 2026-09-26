"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleAlert, FileText, LoaderCircle, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { deleteDocument, fetchDocuments, type DocumentInfo } from "@/lib/api";
import { formatBytes, formatDate } from "@/lib/format";

const PROCESSING_POLL_MS = 2000;

export function RecentDocuments() {
  const queryClient = useQueryClient();
  const { data, error, isPending } = useQuery({
    queryKey: ["documents"],
    queryFn: fetchDocuments,
    refetchInterval: (query) =>
      query.state.data?.some((d) => d.status === "uploaded" || d.status === "processing")
        ? PROCESSING_POLL_MS
        : false,
  });
  // Deleting removes the file and everything extracted from it, and cannot be undone, so it
  // is never one click on an icon: the document is named back before anything happens.
  const [confirming, setConfirming] = useState<DocumentInfo | null>(null);
  const remove = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      setConfirming(null);
      return queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  if (isPending) return null;
  if (error) {
    return (
      <p className="text-sm text-danger" role="alert">
        {error.message}
      </p>
    );
  }
  if (data.length === 0) return null;

  return (
    <section aria-labelledby="recent-title" className="w-full space-y-3 text-left">
      <h2 id="recent-title" className="text-sm font-semibold">
        Your documents
      </h2>
      {remove.error && (
        <p className="text-sm text-danger" role="alert">
          {remove.error.message}
        </p>
      )}
      <ul className="divide-y rounded-xl border bg-card">
        {data.map((document) => (
          <li key={document.id} className="flex items-center gap-3 px-4 py-3">
            <FileText className="size-5 shrink-0 text-primary" aria-hidden />
            <Link
              href={`/documents/${document.id}`}
              className="min-w-0 flex-1 rounded-sm focus-visible:outline-2 focus-visible:outline-ring"
            >
              <span className="block truncate text-sm font-medium hover:underline">
                {document.original_filename}
              </span>
              <span className="block text-xs text-muted-foreground">
                {[
                  document.document_type,
                  document.page_count ? `${document.page_count} pages` : null,
                  formatBytes(document.file_size),
                  formatDate(document.created_at),
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            </Link>
            <StatusBadge document={document} />
            <Button
              variant="ghost"
              size="icon-sm"
              className="text-muted-foreground hover:bg-red-50 hover:text-danger"
              aria-label={`Delete ${document.original_filename}`}
              onClick={() => {
                remove.reset();
                setConfirming(document);
              }}
            >
              <Trash2 />
            </Button>
          </li>
        ))}
      </ul>

      <ConfirmDelete
        document={confirming}
        pending={remove.isPending}
        error={remove.error?.message ?? null}
        onCancel={() => setConfirming(null)}
        onConfirm={(id) => remove.mutate(id)}
      />
    </section>
  );
}

function ConfirmDelete({
  document,
  pending,
  error,
  onCancel,
  onConfirm,
}: {
  document: DocumentInfo | null;
  pending: boolean;
  error: string | null;
  onCancel: () => void;
  onConfirm: (id: string) => void;
}) {
  // The dialog fades out rather than vanishing, so it is still on screen after the choice is
  // made. Keep the last document to name during that moment, or the title reads Delete “”?
  const [shown, setShown] = useState(document);
  if (document !== null && document !== shown) setShown(document);

  return (
    <Dialog open={document !== null} onOpenChange={(next) => !next && !pending && onCancel()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Delete “{shown?.original_filename}”?</DialogTitle>
          <DialogDescription>
            The file and everything read from it — pages, clauses, key facts and your questions
            about it — are removed. This cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <p className="flex gap-2 rounded-lg border border-warning/30 bg-amber-50 p-3 text-xs text-foreground/80">
          <CircleAlert className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden />
          Deleting the copy here does not affect the original document you were given, and is
          not a substitute for telling whoever issued it.
        </p>
        {error && (
          <p className="text-sm text-danger" role="alert">
            {error}
          </p>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={onCancel} disabled={pending}>
            Keep it
          </Button>
          <Button
            className="bg-danger text-white hover:bg-danger/90"
            disabled={pending || !document}
            onClick={() => document && onConfirm(document.id)}
          >
            {pending ? <LoaderCircle className="animate-spin" aria-hidden /> : <Trash2 aria-hidden />}
            Delete permanently
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function StatusBadge({ document }: { document: DocumentInfo }) {
  switch (document.status) {
    case "ready":
      return <Badge variant="outline" className="border-success/40 text-success">Ready</Badge>;
    case "failed":
      return (
        <Badge variant="outline" className="border-danger/40 text-danger">
          <CircleAlert aria-hidden />
          Failed
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className="text-muted-foreground">
          <LoaderCircle className="animate-spin" aria-hidden />
          Processing
        </Badge>
      );
  }
}
