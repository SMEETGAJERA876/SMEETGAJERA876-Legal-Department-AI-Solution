"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  CircleAlert,
  Download,
  FileDown,
  FileSearch,
  FileText,
  LoaderCircle,
  LogIn,
  MessageSquareText,
  Scale,
  Search,
  Sparkles,
  SpellCheck,
} from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Disclaimer } from "@/components/system/disclaimer";
import { DownloadButton } from "@/components/system/download-button";
import { UserMenu } from "@/components/system/user-menu";
import {
  documentDownloadPath,
  documentSummaryPath,
  fetchConcepts,
  fetchDocument,
  fetchDocumentFile,
  type DocumentInfo,
} from "@/lib/api";
import { AskPanel } from "./ask-panel";
import { CheckPanel } from "./check-panel";
import { AuthenticityPanel } from "./authenticity-panel";
import { FormatPanel } from "./format-panel";
import { OverviewPanel } from "./overview-panel";
import type { ViewerTarget } from "./pdf-viewer";
import { SearchPanel } from "./search-panel";

const PdfViewer = dynamic(() => import("./pdf-viewer"), {
  ssr: false,
  loading: () => (
    <p className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
      <LoaderCircle className="size-4 animate-spin" aria-hidden />
      Loading viewer…
    </p>
  ),
});

const STATUS_POLL_MS = 1500;

type MobileTab = "document" | "search" | "ask";
type SideTab = "search" | "check" | "format";

const SIDE_TABS: { value: SideTab; label: string; icon: typeof FileText }[] = [
  { value: "search", label: "Search", icon: Search },
  { value: "check", label: "Mistakes", icon: SpellCheck },
  { value: "format", label: "Verify", icon: Scale },
];

const MOBILE_TABS: { value: MobileTab; label: string; icon: typeof FileText }[] = [
  { value: "document", label: "Document", icon: FileText },
  { value: "search", label: "Search & check", icon: Search },
  { value: "ask", label: "Ask", icon: MessageSquareText },
];

export function DocumentWorkspace({
  documentId,
  demo = false,
}: {
  documentId: string;
  /** Opened from /demo: shared, read-only, and usable without signing in. */
  demo?: boolean;
}) {
  const { data: document, error } = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => fetchDocument(documentId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "ready" || status === "failed" ? false : STATUS_POLL_MS;
    },
  });

  const home = demo ? "/demo" : "/";

  return (
    <div className="flex h-dvh flex-col">
      <header className="flex items-center gap-3 border-b bg-card px-4 py-2.5">
        <Button
          variant="ghost"
          size="icon-sm"
          nativeButton={false}
          render={<Link href={home} aria-label={demo ? "All demo documents" : "All documents"} />}
        >
          <ArrowLeft />
        </Button>
        <Link href={home} className="flex items-center gap-1.5 text-sm font-semibold text-primary">
          <FileSearch className="size-4" aria-hidden />
          <span className="hidden sm:inline">ClauseLens AI</span>
        </Link>
        <span className="text-muted-foreground" aria-hidden>
          /
        </span>
        <h1 className="truncate text-sm font-medium">
          {document?.original_filename ?? "Document"}
        </h1>
        {document?.source_document_id && (
          <Link
            href={`/documents/${document.source_document_id}`}
            className="shrink-0 rounded-full border border-success/40 px-2 py-0.5 text-xs font-medium text-success hover:bg-green-50"
          >
            Corrected copy · view original
          </Link>
        )}
        {document?.status === "ready" && (
          <DownloadButton
            size="sm"
            className="ml-auto shrink-0"
            path={documentSummaryPath(documentId)}
            fallbackName="summary.pdf"
          >
            <FileDown aria-hidden />
            <span className="hidden sm:inline">Summary PDF</span>
          </DownloadButton>
        )}
        {document?.status === "ready" && (
          <DownloadButton
            variant="outline"
            size="sm"
            className="shrink-0"
            path={documentDownloadPath(documentId)}
            fallbackName={document.original_filename}
          >
            <Download aria-hidden />
            <span className="hidden sm:inline">Download PDF</span>
          </DownloadButton>
        )}
        <div className={document?.status === "ready" ? "shrink-0" : "ml-auto shrink-0"}>
          {demo ? (
            <Button size="sm" nativeButton={false} render={<Link href="/" />}>
              <LogIn aria-hidden />
              <span className="hidden sm:inline">Sign in to use your own</span>
              <span className="sm:hidden">Sign in</span>
            </Button>
          ) : (
            <UserMenu compact />
          )}
        </div>
      </header>

      {error ? (
        <CenteredMessage tone="error" title="Unable to open this document" text={error.message} />
      ) : !document ? (
        <CenteredMessage tone="loading" title="Opening document…" />
      ) : document.status === "failed" ? (
        <CenteredMessage
          tone="error"
          title="We couldn't process this document"
          text={document.error_message ?? "Please try uploading it again."}
          action
        />
      ) : document.status !== "ready" ? (
        <ProcessingView document={document} />
      ) : (
        <>
          {demo && <DemoBanner />}
          {document.authenticity_verdict === "concerns" && <AuthenticityBanner />}
          <ReadyWorkspace documentId={documentId} demo={demo} />
        </>
      )}
    </div>
  );
}

/** Strong evidence that the file is not an issued document — said before anything is read. */
function AuthenticityBanner() {
  return (
    <p
      className="flex flex-wrap items-center justify-center gap-x-2 gap-y-1 border-b border-danger/30 bg-red-50 px-4 py-1.5 text-center text-xs text-foreground"
      role="alert"
    >
      <CircleAlert className="size-3.5 shrink-0 text-danger" aria-hidden />
      <span>
        <strong className="font-semibold">Check this document before relying on it.</strong>{" "}
        Something about how this file was made does not match an issued document — see{" "}
        <em>Verify</em>.
      </span>
    </p>
  );
}

/** Says plainly what this document is, so nobody mistakes a shared sample for their own file. */
function DemoBanner() {
  return (
    <p className="flex flex-wrap items-center justify-center gap-x-2 gap-y-1 border-b border-primary/20 bg-accent px-4 py-1.5 text-center text-xs text-foreground">
      <Sparkles className="size-3.5 shrink-0 text-primary" aria-hidden />
      <span>
        <strong className="font-semibold">Live demo.</strong> This document is shared and
        read-only — search it, ask it anything, and click a source to see the page.
      </span>
      <Link href="/" className="font-medium text-primary underline underline-offset-2">
        Sign in to upload your own
      </Link>
    </p>
  );
}

function ReadyWorkspace({ documentId, demo }: { documentId: string; demo: boolean }) {
  const [target, setTarget] = useState<ViewerTarget | null>(null);
  const [mobileTab, setMobileTab] = useState<MobileTab>("document");
  const [sideTab, setSideTab] = useState<SideTab>("search");
  const { data: concepts } = useQuery({ queryKey: ["concepts"], queryFn: fetchConcepts, staleTime: Infinity });

  const conceptLabel = useCallback(
    (key: string) => concepts?.find((c) => c.key === key)?.label ?? key.replace(/_/g, " "),
    [concepts],
  );

  const showSource = useCallback((page: number, quote: string | null, focus?: string | null) => {
    setTarget((previous) => ({ page, quote, focus, requestId: (previous?.requestId ?? 0) + 1 }));
    setMobileTab("document");
  }, []);

  const fileUrl = useDocumentFileUrl(documentId);
  const panelClass = (tab: MobileTab) => (mobileTab === tab ? "flex" : "hidden lg:flex");

  return (
    <>
      <nav className="flex border-b bg-card lg:hidden" aria-label="Workspace sections">
        {MOBILE_TABS.map(({ value, label, icon: Icon }) => (
          <button
            key={value}
            type="button"
            onClick={() => setMobileTab(value)}
            aria-current={mobileTab === value ? "page" : undefined}
            className="flex flex-1 items-center justify-center gap-1.5 border-b-2 border-transparent py-2.5 text-sm font-medium text-muted-foreground aria-[current=page]:border-primary aria-[current=page]:text-primary"
          >
            <Icon className="size-4" aria-hidden />
            {label}
          </button>
        ))}
      </nav>

      <div className="grid min-h-0 flex-1 lg:grid-cols-[300px_minmax(0,1fr)_380px] xl:grid-cols-[340px_minmax(0,1fr)_420px]">
        <aside
          className={`${panelClass("search")} min-h-0 flex-col gap-6 overflow-y-auto border-r bg-background p-4`}
          aria-label="Overview and search"
        >
          <div role="tablist" aria-label="Left panel" className="flex rounded-lg bg-muted p-1">
            {SIDE_TABS.map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                type="button"
                role="tab"
                aria-selected={sideTab === value}
                onClick={() => setSideTab(value)}
                className="flex flex-1 items-center justify-center gap-1.5 rounded-md py-1.5 text-xs font-medium text-muted-foreground aria-selected:bg-card aria-selected:text-foreground aria-selected:shadow-sm focus-visible:outline-2 focus-visible:outline-ring"
              >
                <Icon className="size-3.5" aria-hidden />
                {label}
              </button>
            ))}
          </div>
          {sideTab === "search" ? (
            <>
              <SearchPanel documentId={documentId} onShowSource={showSource} conceptLabel={conceptLabel} />
              <OverviewPanel documentId={documentId} onShowSource={showSource} />
            </>
          ) : sideTab === "check" ? (
            <CheckPanel documentId={documentId} onShowSource={showSource} readOnly={demo} />
          ) : (
            <>
              <AuthenticityPanel documentId={documentId} onShowSource={showSource} />
              <FormatPanel documentId={documentId} onShowSource={showSource} />
            </>
          )}
        </aside>

        <main className={`${panelClass("document")} min-h-0 flex-col`} aria-label="Document viewer">
          {"url" in fileUrl ? (
            <PdfViewer fileUrl={fileUrl.url} target={target} />
          ) : (
            <CenteredMessage
              tone={fileUrl.error ? "error" : "loading"}
              title={fileUrl.error ? "Unable to open the PDF" : "Opening document…"}
              text={fileUrl.error ?? undefined}
            />
          )}
        </main>

        <aside className={`${panelClass("ask")} min-h-0 flex-col border-l bg-card`} aria-label="Ask about your document">
          <AskPanel documentId={documentId} onShowSource={showSource} conceptLabel={conceptLabel} />
        </aside>
      </div>
      <Disclaimer className="border-t bg-card px-4 py-1.5" />
    </>
  );
}

type FileState = { url: string } | { error: string | null };

/** The PDF, fetched with the user's sign-in and handed to the viewer as a local object URL. */
function useDocumentFileUrl(documentId: string): FileState {
  const [state, setState] = useState<{ id: string; file: FileState } | null>(null);

  useEffect(() => {
    let cancelled = false;
    let url: string | null = null;
    fetchDocumentFile(documentId).then(
      (blob) => {
        if (cancelled) return;
        url = URL.createObjectURL(blob);
        setState({ id: documentId, file: { url } });
      },
      (error: unknown) => {
        if (cancelled) return;
        const message = error instanceof Error ? error.message : "Please try again.";
        setState({ id: documentId, file: { error: message } });
      },
    );
    return () => {
      cancelled = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [documentId]);

  return state?.id === documentId ? state.file : { error: null };
}

const PROCESSING_STEPS = [
  "Uploading",
  "Reading pages",
  "Finding clauses",
  "Understanding the meaning of each part",
  "Extracting important information",
];

function currentStep(document: DocumentInfo): number {
  if (document.status === "uploaded") return 1;
  const detail = document.status_detail?.toLowerCase() ?? "";
  if (detail.startsWith("reading")) return 1;
  if (detail.startsWith("finding")) return 2;
  if (detail.startsWith("understanding")) return 3;
  if (detail.startsWith("extracting")) return 4;
  return 1;
}

function ProcessingView({ document }: { document: DocumentInfo }) {
  const step = currentStep(document);
  return (
    <div className="flex flex-1 items-center justify-center p-6">
      <div className="w-full max-w-md space-y-5 rounded-xl border bg-card p-6 shadow-sm" role="status" aria-live="polite">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold">Processing your document</h2>
          <p className="text-sm text-muted-foreground">
            This usually takes a few seconds. The first document may take a little longer while
            the search model loads.
          </p>
        </div>
        <ol className="space-y-2.5">
          {PROCESSING_STEPS.map((label, index) => {
            const state = index < step ? "done" : index === step ? "active" : "waiting";
            return (
              <li key={label} className="flex items-center gap-2.5 text-sm">
                <span
                  className={`flex size-5 items-center justify-center rounded-full border text-[11px] ${
                    state === "done"
                      ? "border-success bg-success text-white"
                      : state === "active"
                        ? "border-primary text-primary"
                        : "text-muted-foreground"
                  }`}
                  aria-hidden
                >
                  {state === "done" ? "✓" : state === "active" ? <LoaderCircle className="size-3 animate-spin" /> : index + 1}
                </span>
                <span className={state === "waiting" ? "text-muted-foreground" : ""}>
                  {label}
                  <span className="sr-only">
                    {state === "done" ? " (done)" : state === "active" ? " (in progress)" : ""}
                  </span>
                </span>
              </li>
            );
          })}
        </ol>
        {document.page_count && (
          <p className="text-xs text-muted-foreground">{document.page_count} pages found</p>
        )}
      </div>
    </div>
  );
}

function CenteredMessage({
  tone,
  title,
  text,
  action = false,
}: {
  tone: "loading" | "error";
  title: string;
  text?: string;
  action?: boolean;
}) {
  return (
    <div className="flex flex-1 items-center justify-center p-6">
      <div className="max-w-md space-y-3 text-center" role={tone === "error" ? "alert" : "status"}>
        {tone === "loading" ? (
          <LoaderCircle className="mx-auto size-6 animate-spin text-primary" aria-hidden />
        ) : (
          <CircleAlert className="mx-auto size-6 text-danger" aria-hidden />
        )}
        <h2 className="text-lg font-semibold">{title}</h2>
        {text && <p className="text-sm text-muted-foreground">{text}</p>}
        {action && (
          <Button nativeButton={false} render={<Link href="/" />}>
            Upload another document
          </Button>
        )}
      </div>
    </div>
  );
}
