"use client";

import { useQuery } from "@tanstack/react-query";
import {
  CircleAlert,
  CircleCheck,
  CircleHelp,
  LoaderCircle,
  PencilLine,
  Scale,
} from "lucide-react";
import { fetchFormatCheck, type FormatPart } from "@/lib/api";
import type { ShowSource } from "./source-quote";

type Props = { documentId: string; onShowSource: ShowSource };

/** Evidence comes back as “…wording…”; the viewer matches the wording, not the ellipses. */
const withoutEllipses = (text: string) => text.replace(/^…|…$/g, "").trim();

const STATUS = {
  missing: {
    icon: CircleAlert,
    label: "Not found in your document",
    className: "border-danger/30 bg-red-50/70",
    tone: "text-danger",
  },
  empty: {
    icon: PencilLine,
    label: "Found, but left blank",
    className: "border-warning/30 bg-amber-50/60",
    tone: "text-warning",
  },
  present: {
    icon: CircleCheck,
    label: "Found",
    className: "border bg-card",
    tone: "text-success",
  },
} as const;

/** Compares the document against the official format for its kind (docs/Formats.md). */
export function FormatPanel({ documentId, onShowSource }: Props) {
  const { data, error, isPending } = useQuery({
    queryKey: ["format-check", documentId],
    queryFn: () => fetchFormatCheck(documentId),
  });

  if (isPending) {
    return (
      <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
        <LoaderCircle className="size-4 animate-spin" aria-hidden />
        Comparing with the official format…
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

  if (!data.available) {
    return (
      <div className="space-y-3">
        <PanelHeading />
        <div className="space-y-2 rounded-lg border bg-card p-3">
          <p className="flex items-start gap-2 text-sm">
            <CircleHelp className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
            <span>
              There is no official format described for{" "}
              <strong>{data.document_type ?? "this kind of document"}</strong> yet, so there is
              nothing to compare it against.
            </span>
          </p>
          {data.covered_formats.length > 0 && (
            <>
              <p className="text-xs font-medium text-muted-foreground">
                Formats ClauseLens can compare against:
              </p>
              <ul className="flex flex-wrap gap-1.5">
                {data.covered_formats.map((name) => (
                  <li key={name} className="rounded-full border bg-background px-2.5 py-0.5 text-xs">
                    {name}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>
    );
  }

  const missing = data.parts.filter((p) => p.required && p.status === "missing");
  const blank = data.parts.filter((p) => p.status === "empty");
  const optionalMissing = data.parts.filter((p) => !p.required && p.status === "missing");
  const present = data.parts.filter((p) => p.status === "present");
  const percent = Math.round(data.score * 100);

  return (
    <div className="space-y-4">
      <PanelHeading />

      <div className="space-y-2 rounded-lg border bg-card p-3">
        <p className="text-sm">
          Compared with the format for a <strong>{data.format_name}</strong>.
        </p>
        <div className="flex items-center gap-2">
          <div
            className="h-2 flex-1 overflow-hidden rounded-full bg-muted"
            role="img"
            aria-label={`${data.required_present} of ${data.required_total} required parts found`}
          >
            <div
              className={`h-full rounded-full ${
                percent === 100 ? "bg-success" : percent >= 70 ? "bg-warning" : "bg-danger"
              }`}
              style={{ width: `${percent}%` }}
            />
          </div>
          <span className="text-xs font-semibold tabular-nums">
            {data.required_present}/{data.required_total}
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          required parts found. Expected by: {data.authority}
        </p>
        {data.note && <p className="text-xs text-muted-foreground">{data.note}</p>}
      </div>

      <Group
        title="Missing — usually required"
        parts={missing}
        onShowSource={onShowSource}
        empty="Nothing required is missing."
      />
      <Group title="Left blank" parts={blank} onShowSource={onShowSource} />
      <Group title="Missing — optional" parts={optionalMissing} onShowSource={onShowSource} />
      <Group title="Found" parts={present} onShowSource={onShowSource} collapsed />

      <p className="rounded-lg border border-dashed bg-muted/40 p-3 text-xs text-muted-foreground">
        This is a checklist, not a ruling. ClauseLens looks for the wording each part usually
        uses, so a part written in unusual words may be reported as missing. A missing part is
        something to ask about — not proof that the document is invalid.
      </p>
    </div>
  );
}

function PanelHeading() {
  return (
    <div className="space-y-1">
      <h2 className="flex items-center gap-1.5 text-sm font-semibold">
        <Scale className="size-4 text-primary" aria-hidden />
        Compare with the official format
      </h2>
      <p className="text-xs text-muted-foreground">
        What a document of this kind is expected to contain, and what yours actually has.
      </p>
    </div>
  );
}

function Group({
  title,
  parts,
  onShowSource,
  empty,
  collapsed = false,
}: {
  title: string;
  parts: FormatPart[];
  onShowSource: ShowSource;
  empty?: string;
  collapsed?: boolean;
}) {
  if (parts.length === 0) {
    return empty ? (
      <p className="flex items-start gap-2 rounded-lg border bg-card p-3 text-sm">
        <CircleCheck className="mt-0.5 size-4 shrink-0 text-success" aria-hidden />
        {empty}
      </p>
    ) : null;
  }

  const list = (
    <ul className="space-y-2">
      {parts.map((part) => (
        <PartRow key={part.id} part={part} onShowSource={onShowSource} />
      ))}
    </ul>
  );

  if (collapsed) {
    return (
      <details className="space-y-2">
        <summary className="cursor-pointer text-xs font-semibold tracking-wide text-muted-foreground uppercase">
          {title} ({parts.length})
        </summary>
        <div className="mt-2">{list}</div>
      </details>
    );
  }

  return (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        {title} ({parts.length})
      </h3>
      {list}
    </div>
  );
}

function PartRow({ part, onShowSource }: { part: FormatPart; onShowSource: ShowSource }) {
  const status = STATUS[part.status];
  const Icon = status.icon;
  return (
    <li className={`rounded-lg p-3 ${status.className}`}>
      <div className="flex gap-2">
        <Icon className={`mt-0.5 size-4 shrink-0 ${status.tone}`} aria-hidden />
        <div className="min-w-0 space-y-1">
          <p className="text-sm font-medium">
            {part.label}
            <span className="sr-only"> — {status.label}</span>
          </p>
          <p className="text-xs text-muted-foreground">{part.why}</p>
          {part.evidence && (
            <p className="truncate text-xs text-foreground/70 italic">“{part.evidence}”</p>
          )}
          {part.page_number !== null && (
            <button
              type="button"
              onClick={() =>
                onShowSource(
                  part.page_number as number,
                  part.evidence ? withoutEllipses(part.evidence) : null,
                )
              }
              className="text-xs font-medium text-primary underline-offset-2 hover:underline"
            >
              Show on page {part.page_number}
            </button>
          )}
        </div>
      </div>
    </li>
  );
}
