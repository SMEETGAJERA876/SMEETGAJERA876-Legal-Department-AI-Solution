"use client";

import { useQuery } from "@tanstack/react-query";
import { CircleAlert, CircleCheck, Info, LoaderCircle, ShieldQuestion } from "lucide-react";
import { fetchAuthenticity, type AuthenticitySignal } from "@/lib/api";
import type { ShowSource } from "./source-quote";

type Props = { documentId: string; onShowSource: ShowSource };

const SEVERITY = {
  high: { icon: CircleAlert, className: "border-danger/30 bg-red-50/70", tone: "text-danger" },
  medium: { icon: CircleAlert, className: "border-warning/30 bg-amber-50/60", tone: "text-warning" },
  info: { icon: Info, className: "border bg-card", tone: "text-muted-foreground" },
} as const;

const VERDICT = {
  concerns: {
    title: "There is evidence this is not an issued document",
    tone: "border-danger/30 bg-red-50/70",
    icon: CircleAlert,
    iconTone: "text-danger",
  },
  check: {
    title: "A few things here are worth checking",
    tone: "border-warning/30 bg-amber-50/60",
    icon: ShieldQuestion,
    iconTone: "text-warning",
  },
  ordinary: {
    title: "Nothing unusual found in how this file was made",
    tone: "border-success/30 bg-green-50/60",
    icon: CircleCheck,
    iconTone: "text-success",
  },
} as const;

/** What the file itself records about how it was made (docs/Authenticity.md). */
export function AuthenticityPanel({ documentId, onShowSource }: Props) {
  const { data, error, isPending } = useQuery({
    queryKey: ["authenticity", documentId],
    queryFn: () => fetchAuthenticity(documentId),
  });

  if (isPending) {
    return (
      <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
        <LoaderCircle className="size-4 animate-spin" aria-hidden />
        Checking where this document came from…
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
  if (!data.available || !data.verdict) {
    return (
      <p className="rounded-lg border bg-card p-3 text-sm text-muted-foreground">
        This document has not been checked for where it came from.
      </p>
    );
  }

  const verdict = VERDICT[data.verdict];
  const Icon = verdict.icon;
  const provenance = Object.entries(data.provenance);

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <h2 className="flex items-center gap-1.5 text-sm font-semibold">
          <ShieldQuestion className="size-4 text-primary" aria-hidden />
          Where this document came from
        </h2>
        <p className="text-xs text-muted-foreground">
          What the file records about itself, and anything in it that an issued document
          would not contain.
        </p>
      </div>

      <div className={`flex gap-2 rounded-lg p-3 ${verdict.tone}`}>
        <Icon className={`mt-0.5 size-4 shrink-0 ${verdict.iconTone}`} aria-hidden />
        <p className="text-sm font-medium">{verdict.title}</p>
      </div>

      {data.signals.length > 0 && (
        <ul className="space-y-2">
          {data.signals.map((signal) => (
            <SignalRow key={signal.id} signal={signal} onShowSource={onShowSource} />
          ))}
        </ul>
      )}

      {provenance.length > 0 && (
        <details className="rounded-lg border bg-muted/40 p-3">
          <summary className="cursor-pointer text-xs font-semibold tracking-wide text-muted-foreground uppercase">
            What the file says about itself
          </summary>
          <dl className="mt-2 space-y-1">
            {provenance.map(([key, value]) => (
              <div key={key} className="flex flex-wrap gap-x-2 text-xs">
                <dt className="font-medium">{key}</dt>
                <dd className="break-all text-muted-foreground">{value}</dd>
              </div>
            ))}
          </dl>
        </details>
      )}

      <p className="rounded-lg border border-dashed bg-muted/40 p-3 text-xs text-muted-foreground">
        ClauseLens reports what it found; it does not decide whether a document is genuine.
        It never judges this from writing style — style tells you nothing reliable about who
        wrote a document, and formal official wording is exactly what such tests get wrong.
        {data.policy === "reject" &&
          " This server refuses documents where the evidence is strong."}
      </p>
    </div>
  );
}

function SignalRow({
  signal,
  onShowSource,
}: {
  signal: AuthenticitySignal;
  onShowSource: ShowSource;
}) {
  const severity = SEVERITY[signal.severity];
  const Icon = severity.icon;
  return (
    <li className={`rounded-lg p-3 ${severity.className}`}>
      <div className="flex gap-2">
        <Icon className={`mt-0.5 size-4 shrink-0 ${severity.tone}`} aria-hidden />
        <div className="min-w-0 space-y-1">
          <p className="text-sm font-medium">{signal.label}</p>
          <p className="text-xs text-muted-foreground">{signal.detail}</p>
          {signal.evidence && (
            <p className="text-xs break-words text-foreground/70 italic">“{signal.evidence}”</p>
          )}
          {signal.page_number !== null && (
            <button
              type="button"
              onClick={() => onShowSource(signal.page_number as number, null)}
              className="text-xs font-medium text-primary underline-offset-2 hover:underline"
            >
              Show page {signal.page_number}
            </button>
          )}
        </div>
      </div>
    </li>
  );
}
