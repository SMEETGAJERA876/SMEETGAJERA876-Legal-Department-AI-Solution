"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { History, LoaderCircle, LockKeyhole, ShieldCheck, Trash2 } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { deleteAllMyDocuments, fetchMyActivity } from "@/lib/api";

const PROTECTIONS = [
  "Only your Google account can open, search or download your documents.",
  "Files are encrypted on the server (AES-256).",
  "Your documents are never used to train AI models.",
  "Every view, download and deletion is recorded below.",
];

const TIME_FORMAT = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });

/** "Privacy & activity": what protects the user's documents, their activity log, and erasure. */
export function PrivacyDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState(false);
  const activity = useQuery({ queryKey: ["my-activity"], queryFn: fetchMyActivity, enabled: open });
  const erase = useMutation({
    mutationFn: deleteAllMyDocuments,
    onSuccess: () => {
      setConfirming(false);
      void queryClient.invalidateQueries();
    },
  });

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (erase.isPending) return;
        setConfirming(false);
        onOpenChange(next);
      }}
    >
      <DialogContent className="max-h-[85dvh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShieldCheck className="size-5 text-success" aria-hidden />
            Privacy &amp; activity
          </DialogTitle>
          <DialogDescription>
            How your documents are protected, and what happened to them.
          </DialogDescription>
        </DialogHeader>

        <ul className="space-y-1.5 rounded-lg bg-accent/60 p-3">
          {PROTECTIONS.map((item) => (
            <li key={item} className="flex items-start gap-2 text-xs">
              <LockKeyhole className="mt-px size-3.5 shrink-0 text-success" aria-hidden />
              {item}
            </li>
          ))}
        </ul>

        <section aria-labelledby="activity-title" className="space-y-2">
          <h3 id="activity-title" className="flex items-center gap-1.5 text-sm font-semibold">
            <History className="size-4 text-muted-foreground" aria-hidden />
            Your activity
          </h3>
          {activity.isPending ? (
            <p className="flex items-center gap-2 text-xs text-muted-foreground" role="status">
              <LoaderCircle className="size-3.5 animate-spin" aria-hidden /> Loading…
            </p>
          ) : activity.error ? (
            <p className="text-xs text-danger" role="alert">
              {activity.error.message}
            </p>
          ) : activity.data.length === 0 ? (
            <p className="text-xs text-muted-foreground">Nothing yet.</p>
          ) : (
            <ol className="max-h-56 divide-y overflow-y-auto rounded-lg border">
              {activity.data.map((event, index) => (
                <li
                  key={`${event.at}-${index}`}
                  className="flex items-baseline justify-between gap-3 px-3 py-2"
                >
                  <span className="min-w-0 text-xs">
                    {event.label}
                    {event.document_name && (
                      <span className="block truncate text-muted-foreground">
                        {event.document_name}
                      </span>
                    )}
                  </span>
                  <time dateTime={event.at} className="shrink-0 text-[11px] text-muted-foreground">
                    {TIME_FORMAT.format(new Date(event.at))}
                  </time>
                </li>
              ))}
            </ol>
          )}
        </section>

        <section
          aria-labelledby="erase-title"
          className="space-y-2 rounded-lg border border-danger/30 p-3"
        >
          <h3 id="erase-title" className="text-sm font-semibold text-danger">
            Delete all my documents
          </h3>
          <p className="text-xs text-muted-foreground">
            Permanently deletes every document you uploaded, its corrected copies and everything
            ClauseLens extracted from them. This can&apos;t be undone.
          </p>
          {erase.isSuccess && (
            <p className="text-xs font-medium text-success" role="status">
              Deleted {erase.data.deleted_documents} document
              {erase.data.deleted_documents === 1 ? "" : "s"}.
            </p>
          )}
          {erase.error && (
            <p className="text-xs text-danger" role="alert">
              {erase.error.message}
            </p>
          )}
          {confirming ? (
            <DialogFooter className="gap-2 sm:justify-start">
              <Button
                variant="destructive"
                onClick={() => erase.mutate()}
                disabled={erase.isPending}
              >
                {erase.isPending ? (
                  <LoaderCircle className="animate-spin" aria-hidden />
                ) : (
                  <Trash2 aria-hidden />
                )}
                Yes, delete everything
              </Button>
              <Button
                variant="outline"
                onClick={() => setConfirming(false)}
                disabled={erase.isPending}
              >
                Cancel
              </Button>
            </DialogFooter>
          ) : (
            <Button variant="outline" className="text-danger" onClick={() => setConfirming(true)}>
              <Trash2 aria-hidden />
              Delete all my documents…
            </Button>
          )}
        </section>
      </DialogContent>
    </Dialog>
  );
}
