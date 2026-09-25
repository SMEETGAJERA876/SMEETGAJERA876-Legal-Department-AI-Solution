"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BadgeCheck, CircleHelp, LoaderCircle } from "lucide-react";
import { useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { fetchDocumentTypes, setDocumentType, type DocumentInfo, type DocumentType } from "@/lib/api";

type Props = { document: DocumentInfo };

/** "What is this document?" — shows the classification honestly and lets the user fix it. */
export function ClassificationCard({ document }: Props) {
  const queryClient = useQueryClient();
  const [picking, setPicking] = useState(false);
  const { data: types } = useQuery({
    queryKey: ["document-types"],
    queryFn: fetchDocumentTypes,
    staleTime: Infinity,
  });
  const save = useMutation({
    mutationFn: (typeId: string) => setDocumentType(document.id, typeId),
    onSuccess: () => {
      setPicking(false);
      void queryClient.invalidateQueries({ queryKey: ["overview", document.id] });
      void queryClient.invalidateQueries({ queryKey: ["document", document.id] });
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  const classification = document.classification;
  const status = classification?.status ?? "unknown";
  const level = classification?.confidence_level ?? "low";
  const nameOf = (id: string) => types?.find((t) => t.id === id)?.name ?? id;
  const suggestions = (classification?.alternatives ?? []).map((a) => a.document_type);

  const picker = picking && types && (
    <TypePicker
      types={types}
      initial={document.document_type_id ?? suggestions[0] ?? ""}
      pending={save.isPending}
      onCancel={() => setPicking(false)}
      onSave={(id) => save.mutate(id)}
    />
  );

  return (
    <div className="space-y-2">
      {status === "user_verified" ? (
        <p className="flex items-center gap-1.5 text-sm font-semibold">
          {document.document_type}
          <BadgeCheck className="size-4 text-success" aria-label="confirmed by you" />
        </p>
      ) : level === "high" ? (
        <h2 className="text-sm font-semibold">{document.document_type}</h2>
      ) : level === "medium" ? (
        <div className="space-y-2 rounded-lg border bg-card p-3">
          <p className="text-sm">
            Looks like: <span className="font-semibold">{document.document_type}</span>
          </p>
          <div className="flex gap-2">
            <Button
              size="xs"
              variant="outline"
              disabled={save.isPending || !document.document_type_id}
              onClick={() => document.document_type_id && save.mutate(document.document_type_id)}
            >
              Yes, that&apos;s right
            </Button>
            <Button size="xs" variant="ghost" onClick={() => setPicking(true)}>
              Change
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-2 rounded-lg border border-warning/30 bg-amber-50 p-3" role="status">
          <p className="flex items-start gap-2 text-sm">
            <CircleHelp className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden />
            <span>
              <span className="font-semibold">We&apos;re not sure what kind of document this is.</span>{" "}
              Choosing the type helps ClauseLens look for the right information.
            </span>
          </p>
          {suggestions.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {suggestions.map((id) => (
                <Button
                  key={id}
                  size="xs"
                  variant="outline"
                  className="bg-card"
                  disabled={save.isPending}
                  onClick={() => save.mutate(id)}
                >
                  {nameOf(id)}
                </Button>
              ))}
            </div>
          )}
          {!picking && (
            <Button size="xs" variant="ghost" onClick={() => setPicking(true)}>
              Choose the type…
            </Button>
          )}
        </div>
      )}

      {(level === "high" || status === "user_verified") && !picking && (
        <button
          type="button"
          onClick={() => setPicking(true)}
          className="text-xs font-medium text-primary underline-offset-2 hover:underline"
        >
          Not right? Change the document type
        </button>
      )}
      {picker}
      {save.error && (
        <p className="text-xs text-danger" role="alert">
          {save.error.message}
        </p>
      )}
      {classification && classification.signals.length > 0 && status !== "user_verified" && (
        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer select-none">Why?</summary>
          <ul className="mt-1 list-disc space-y-0.5 pl-4">
            {classification.signals.map((signal) => (
              <li key={signal}>{signal}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function TypePicker({
  types,
  initial,
  pending,
  onCancel,
  onSave,
}: {
  types: DocumentType[];
  initial: string;
  pending: boolean;
  onCancel: () => void;
  onSave: (id: string) => void;
}) {
  const selectId = useId();
  const [value, setValue] = useState(initial);
  const groups = new Map<string, DocumentType[]>();
  for (const type of types) groups.set(type.category_name, [...(groups.get(type.category_name) ?? []), type]);

  return (
    <form
      className="space-y-2 rounded-lg border bg-card p-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (value) onSave(value);
      }}
    >
      <label htmlFor={selectId} className="text-xs font-medium">
        What kind of document is this?
      </label>
      <select
        id={selectId}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        className="h-8 w-full rounded-md border bg-background px-2 text-sm focus-visible:outline-2 focus-visible:outline-ring"
      >
        <option value="" disabled>
          Choose a type…
        </option>
        {[...groups.entries()].map(([category, items]) => (
          <optgroup key={category} label={category}>
            {items.map((type) => (
              <option key={type.id} value={type.id}>
                {type.name}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
      <div className="flex gap-2">
        <Button type="submit" size="xs" disabled={!value || pending}>
          {pending && <LoaderCircle className="animate-spin" />}
          Save
        </Button>
        <Button type="button" size="xs" variant="ghost" onClick={onCancel} disabled={pending}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
