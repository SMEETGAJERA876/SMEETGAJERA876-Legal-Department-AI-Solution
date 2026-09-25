"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleAlert, FileText, LoaderCircle, Trash2 } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
  const remove = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
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
              aria-label={`Delete ${document.original_filename}`}
              disabled={remove.isPending}
              onClick={() => remove.mutate(document.id)}
            >
              <Trash2 />
            </Button>
          </li>
        ))}
      </ul>
    </section>
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
