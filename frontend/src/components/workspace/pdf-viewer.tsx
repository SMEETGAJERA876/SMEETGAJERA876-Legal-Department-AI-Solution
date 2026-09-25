"use client";

import {
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Highlighter,
  LoaderCircle,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState, type ComponentProps } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { locateQuote, renderItem, type HighlightMap } from "@/lib/highlight";

// Must be set in the same module that renders <Document>; the file is copied on install.
pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

export type ViewerTarget = {
  page: number;
  quote: string | null;
  /** Words inside the quote to mark precisely, e.g. the searched term. */
  focus?: string | null;
  requestId: number;
};

type TextContent = Parameters<NonNullable<ComponentProps<typeof Page>["onGetTextSuccess"]>>[0];

type HighlightStatus = "none" | "found" | "not-found";

const ZOOM_STEPS = [0.6, 0.75, 0.9, 1, 1.15, 1.3, 1.5, 1.75, 2];
const DEFAULT_ZOOM_INDEX = 3;
const PAGE_GUTTER_PX = 32;
const MAX_PAGE_WIDTH_PX = 900;

type Props = {
  fileUrl: string;
  target: ViewerTarget | null;
  onPageCountKnown?: (count: number) => void;
};

export default function PdfViewer({ fileUrl, target, onPageCountKnown }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [pageCount, setPageCount] = useState(0);
  const [page, setPage] = useState(1);
  const [zoomIndex, setZoomIndex] = useState(DEFAULT_ZOOM_INDEX);
  const [containerWidth, setContainerWidth] = useState(0);
  const [pageInput, setPageInput] = useState("1");
  const [quote, setQuote] = useState<string | null>(null);
  const [focus, setFocus] = useState<string | null>(null);
  const [highlights, setHighlights] = useState<HighlightMap>(new Map());
  const [highlightStatus, setHighlightStatus] = useState<HighlightStatus>("none");
  const [handledRequest, setHandledRequest] = useState<number | null>(null);

  // Navigate when a new target (e.g. "View source") arrives — adjusted during render.
  if (target && target.requestId !== handledRequest) {
    setHandledRequest(target.requestId);
    setPage(target.page);
    setPageInput(String(target.page));
    setQuote(target.quote);
    setFocus(target.focus ?? null);
    setHighlightStatus("none");
  }

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setContainerWidth(entry.contentRect.width));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const goTo = useCallback(
    (next: number) => {
      const clamped = Math.min(Math.max(1, next), Math.max(1, pageCount));
      setPage(clamped);
      setPageInput(String(clamped));
      setQuote(null);
      setFocus(null);
      setHighlightStatus("none");
    },
    [pageCount],
  );

  const onTextLoaded = useCallback(
    (textContent: TextContent) => {
      if (!quote) {
        setHighlights(new Map());
        return;
      }
      // Indices must line up with the text layer, so non-text items count as empty.
      const items = textContent.items.map((item) => ("str" in item ? item.str : ""));
      const map = locateQuote(items, quote, focus);
      setHighlights(map);
      setHighlightStatus(map.size > 0 ? "found" : "not-found");
    },
    [quote, focus],
  );

  const textRenderer = useCallback(
    ({ str, itemIndex }: { str: string; itemIndex: number }) =>
      renderItem(str, highlights.get(itemIndex)),
    [highlights],
  );

  const scrollToHighlight = useCallback(() => {
    containerRef.current
      ?.querySelector("mark.clause-highlight")
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, []);

  const pageWidth = useMemo(() => {
    const available = Math.max(0, containerWidth - PAGE_GUTTER_PX);
    return Math.min(available, MAX_PAGE_WIDTH_PX) * ZOOM_STEPS[zoomIndex];
  }, [containerWidth, zoomIndex]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div
        className="flex flex-wrap items-center gap-2 border-b bg-card px-3 py-2"
        role="toolbar"
        aria-label="Document controls"
      >
        <Button
          variant="outline"
          size="icon-sm"
          onClick={() => goTo(page - 1)}
          disabled={page <= 1}
          aria-label="Previous page"
        >
          <ChevronLeft />
        </Button>
        <form
          className="flex items-center gap-1.5 text-sm"
          onSubmit={(event) => {
            event.preventDefault();
            const requested = Number.parseInt(pageInput, 10);
            if (!Number.isNaN(requested)) goTo(requested);
          }}
        >
          <label htmlFor="page-jump" className="sr-only">
            Go to page
          </label>
          <Input
            id="page-jump"
            value={pageInput}
            onChange={(event) => setPageInput(event.target.value)}
            onBlur={() => setPageInput(String(page))}
            inputMode="numeric"
            className="h-7 w-12 text-center"
          />
          <span className="text-muted-foreground">of {pageCount || "…"}</span>
        </form>
        <Button
          variant="outline"
          size="icon-sm"
          onClick={() => goTo(page + 1)}
          disabled={page >= pageCount}
          aria-label="Next page"
        >
          <ChevronRight />
        </Button>
        <div className="ml-auto flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setZoomIndex((z) => Math.max(0, z - 1))}
            disabled={zoomIndex === 0}
            aria-label="Zoom out"
          >
            <ZoomOut />
          </Button>
          <span className="w-12 text-center text-sm tabular-nums text-muted-foreground">
            {Math.round(ZOOM_STEPS[zoomIndex] * 100)}%
          </span>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setZoomIndex((z) => Math.min(ZOOM_STEPS.length - 1, z + 1))}
            disabled={zoomIndex === ZOOM_STEPS.length - 1}
            aria-label="Zoom in"
          >
            <ZoomIn />
          </Button>
        </div>
      </div>

      {quote && highlightStatus !== "none" && (
        <HighlightNotice status={highlightStatus} page={page} />
      )}

      <div ref={containerRef} className="min-h-0 flex-1 overflow-auto bg-muted/60 p-4">
        <Document
          file={fileUrl}
          onLoadSuccess={({ numPages }) => {
            setPageCount(numPages);
            onPageCountKnown?.(numPages);
          }}
          loading={<ViewerMessage icon="loading" text="Opening document…" />}
          error={
            <ViewerMessage
              icon="error"
              text="Unable to display this PDF. The file may be damaged or no longer available."
            />
          }
        >
          {pageWidth > 0 && (
            <Page
              key={page}
              pageNumber={page}
              width={pageWidth}
              className="mx-auto w-fit shadow-md"
              onGetTextSuccess={onTextLoaded}
              customTextRenderer={textRenderer}
              onRenderTextLayerSuccess={scrollToHighlight}
              loading={<ViewerMessage icon="loading" text={`Loading page ${page}…`} />}
            />
          )}
        </Document>
      </div>
    </div>
  );
}

function HighlightNotice({ status, page }: { status: HighlightStatus; page: number }) {
  if (status === "found") {
    return (
      <p
        className="flex items-center gap-2 border-b bg-accent px-3 py-1.5 text-sm text-accent-foreground"
        role="status"
      >
        <Highlighter className="size-4 text-primary" aria-hidden />
        Source highlighted on page {page}.
      </p>
    );
  }
  return (
    <p
      className="flex items-center gap-2 border-b bg-amber-50 px-3 py-1.5 text-sm text-warning"
      role="status"
    >
      <CircleAlert className="size-4" aria-hidden />
      Opened page {page}, but the exact wording couldn&apos;t be pinpointed on the page. Check the
      quoted text in the panel.
    </p>
  );
}

function ViewerMessage({ icon, text }: { icon: "loading" | "error"; text: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
      {icon === "loading" ? (
        <LoaderCircle className="size-4 animate-spin" aria-hidden />
      ) : (
        <CircleAlert className="size-4 text-danger" aria-hidden />
      )}
      <span role={icon === "error" ? "alert" : "status"}>{text}</span>
    </div>
  );
}
