"use client";

import { Menu } from "@base-ui/react/menu";
import { useQuery } from "@tanstack/react-query";
import { Check, ChevronDown, FileText, LoaderCircle, Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { fetchDemo, fetchDocuments } from "@/lib/api";

type Props = {
  documentId: string;
  /** Name to show before the list has loaded, and while it is loading. */
  current: string;
  /** In the public demo the list is the shared documents, not the reader's own. */
  demo: boolean;
};

type Entry = { id: string; name: string; kind: string | null; pages: number | null; note?: string };

/**
 * The open document's name, and a menu to move straight to another one. Without it, changing
 * document means going back to the list and starting again, which is the common case: people
 * compare an agreement with the Act it is written under.
 */
export function DocumentSwitcher({ documentId, current, demo }: Props) {
  const [open, setOpen] = useState(false);

  // Only ask for the list once the reader opens the menu.
  const documents = useQuery({
    queryKey: ["switcher", demo ? "demo" : "mine"],
    enabled: open,
    queryFn: async (): Promise<Entry[]> => {
      if (demo) {
        const { documents: list } = await fetchDemo();
        return list.map((d) => ({
          id: d.id,
          name: d.original_filename,
          kind: d.document_type,
          pages: d.page_count,
        }));
      }
      return (await fetchDocuments()).map((d) => ({
        id: d.id,
        name: d.original_filename,
        kind: d.document_type,
        pages: d.page_count,
        note: d.status === "ready" ? undefined : d.status === "failed" ? "Failed" : "Processing…",
      }));
    },
  });

  const others = (documents.data ?? []).filter((entry) => entry.id !== documentId);

  return (
    <Menu.Root open={open} onOpenChange={setOpen}>
      <Menu.Trigger
        aria-label={`Open document: ${current}. Switch to another document`}
        className="flex min-w-0 items-center gap-1.5 rounded-md px-1.5 py-1 text-left transition-colors outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 data-[popup-open]:bg-muted"
      >
        <span className="truncate text-sm font-medium">{current}</span>
        <ChevronDown className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
      </Menu.Trigger>

      <Menu.Portal>
        <Menu.Positioner side="bottom" align="start" sideOffset={8} className="z-50">
          <Menu.Popup className="max-h-[70dvh] w-80 origin-(--transform-origin) overflow-y-auto rounded-xl border bg-popover p-1.5 text-popover-foreground shadow-lg outline-none transition-[opacity,scale] data-[ending-style]:scale-95 data-[ending-style]:opacity-0 data-[starting-style]:scale-95 data-[starting-style]:opacity-0">
            <p className="px-2.5 pt-1.5 pb-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              {demo ? "Demo documents" : "Your documents"}
            </p>

            {documents.isPending && (
              <p className="flex items-center gap-2 px-2.5 py-3 text-sm text-muted-foreground">
                <LoaderCircle className="size-4 animate-spin" aria-hidden />
                Loading…
              </p>
            )}
            {documents.error && (
              <p className="px-2.5 py-3 text-sm text-danger" role="alert">
                {documents.error.message}
              </p>
            )}
            {documents.data && others.length === 0 && (
              <p className="px-2.5 py-3 text-sm text-muted-foreground">
                {demo
                  ? "This is the only demo document."
                  : "This is your only document so far."}
              </p>
            )}

            {others.map((entry) => (
              <Menu.Item
                key={entry.id}
                className="flex cursor-pointer items-start gap-2.5 rounded-lg px-2.5 py-2 text-sm outline-none select-none data-[highlighted]:bg-muted"
                render={<Link href={demo ? `/demo/${entry.id}` : `/documents/${entry.id}`} />}
              >
                <FileText className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
                <span className="min-w-0">
                  <span className="block truncate font-medium">{entry.name}</span>
                  <span className="block truncate text-xs text-muted-foreground">
                    {[entry.kind, entry.pages ? `${entry.pages} pages` : null, entry.note]
                      .filter(Boolean)
                      .join(" · ")}
                  </span>
                </span>
              </Menu.Item>
            ))}

            <Menu.Separator className="my-1 h-px bg-border" />
            <Menu.Item
              className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium text-primary outline-none select-none data-[highlighted]:bg-muted"
              render={<Link href={demo ? "/demo" : "/"} />}
            >
              {demo ? (
                <Check className="size-4 shrink-0" aria-hidden />
              ) : (
                <Plus className="size-4 shrink-0" aria-hidden />
              )}
              {demo ? "All demo documents" : "Upload another document"}
            </Menu.Item>
          </Menu.Popup>
        </Menu.Positioner>
      </Menu.Portal>
    </Menu.Root>
  );
}
