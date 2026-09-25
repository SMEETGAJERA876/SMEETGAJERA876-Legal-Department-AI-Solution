"use client";

import { useMutation } from "@tanstack/react-query";
import { LoaderCircle, Search } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { searchDocument, type Fact, type SearchMode } from "@/lib/api";
import { formatSource } from "@/lib/format";
import type { ShowSource } from "./source-quote";

type Props = {
  documentId: string;
  onShowSource: ShowSource;
  conceptLabel: (key: string) => string;
};

const MODES: { value: SearchMode; label: string; hint: string }[] = [
  {
    value: "hybrid",
    label: "Best match",
    hint: "Finds related wording (e.g. “leaving early”), exact terms and clause numbers",
  },
  { value: "exact", label: "Exact words", hint: "Finds the exact word or phrase you type" },
];

export function SearchPanel({ documentId, onShowSource, conceptLabel }: Props) {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<SearchMode>("hybrid");
  const search = useMutation({
    mutationFn: (variables: { query: string; mode: SearchMode }) =>
      searchDocument(documentId, variables.query, variables.mode),
  });

  const run = (text: string, searchMode: SearchMode = mode) => {
    const trimmed = text.trim();
    if (trimmed) search.mutate({ query: trimmed, mode: searchMode });
  };

  return (
    <section aria-labelledby="search-title" className="space-y-3">
      <h2 id="search-title" className="text-sm font-semibold">
        Search the document
      </h2>
      <form
        role="search"
        className="flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          run(query);
        }}
      >
        <label htmlFor="document-search" className="sr-only">
          Search the document
        </label>
        <Input
          id="document-search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={mode === "exact" ? "e.g. notice" : "e.g. notice period"}
          maxLength={300}
        />
        <Button type="submit" size="icon" aria-label="Search" disabled={search.isPending}>
          {search.isPending ? <LoaderCircle className="animate-spin" /> : <Search />}
        </Button>
      </form>
      <div role="radiogroup" aria-label="Search type" className="flex gap-1.5">
        {MODES.map((option) => (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={mode === option.value}
            title={option.hint}
            onClick={() => {
              setMode(option.value);
              if (search.data) run(query, option.value);
            }}
            className="rounded-full border px-3 py-1 text-xs font-medium text-muted-foreground aria-checked:border-primary aria-checked:bg-accent aria-checked:text-primary focus-visible:outline-2 focus-visible:outline-ring"
          >
            {option.label}
          </button>
        ))}
      </div>

      {search.error && (
        <p className="text-sm text-danger" role="alert">
          {search.error.message}
        </p>
      )}

      {search.data && (
        <div className="space-y-2" aria-live="polite">
          {search.data.corrected_query && (
            <p className="text-xs text-muted-foreground">
              Showing results for{" "}
              <span className="font-semibold text-foreground">“{search.data.corrected_query}”</span>{" "}
              instead of “{search.data.query}”.
            </p>
          )}
          <FactList facts={search.data.facts} onShowSource={onShowSource} />
          <p className="text-xs text-muted-foreground">
            {search.data.results.length === 0
              ? search.data.mode === "exact"
                ? `No exact matches for “${search.data.query}”. Try “Best match” instead.`
                : `Nothing in the document seems related to “${search.data.query}”.`
              : `${search.data.results.length} matching ${search.data.results.length === 1 ? "passage" : "passages"}`}
          </p>
          <ul className="space-y-2">
            {search.data.results.map((result, index) => (
              <li key={`${result.page_number}-${index}`}>
                <button
                  type="button"
                  onClick={() =>
                    search.data.mode === "exact"
                      ? onShowSource(result.page_number, result.snippet, result.highlight)
                      : onShowSource(result.page_number, result.highlight)
                  }
                  className="w-full rounded-lg border bg-card p-3 text-left text-sm hover:border-primary/50 hover:bg-accent/50 focus-visible:outline-2 focus-visible:outline-ring"
                >
                  <span className="mb-1 flex items-center justify-between gap-2 text-xs font-medium text-primary">
                    {formatSource(result.page_number, result.clause_ref)}
                    {result.heading && (
                      <span className="truncate text-muted-foreground">{result.heading}</span>
                    )}
                  </span>
                  <span className="line-clamp-4 text-foreground/90">
                    <Snippet
                      text={result.snippet}
                      term={search.data.mode === "exact" ? result.highlight : null}
                    />
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {search.data.related_concepts.length > 0 && (
            <div className="space-y-1.5 pt-1">
              <p className="text-xs font-medium text-muted-foreground">Related topics</p>
              <div className="flex flex-wrap gap-1.5">
                {search.data.related_concepts.map((key) => (
                  <Badge
                    key={key}
                    variant="secondary"
                    render={
                      <button
                        type="button"
                        onClick={() => {
                          setQuery(conceptLabel(key));
                          setMode("hybrid");
                          run(conceptLabel(key), "hybrid");
                        }}
                      />
                    }
                  >
                    {conceptLabel(key)}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

/** Every fact of the searched kind, e.g. all notice periods, time limits and notes. */
function FactList({ facts, onShowSource }: { facts: Fact[]; onShowSource: ShowSource }) {
  if (facts.length === 0) return null;
  const groups = new Map<string, Fact[]>();
  for (const fact of facts) groups.set(fact.label, [...(groups.get(fact.label) ?? []), fact]);
  return (
    <div className="space-y-2 rounded-lg border border-primary/30 bg-accent/40 p-3">
      <p className="text-xs font-semibold">Found in this document</p>
      {[...groups.entries()].map(([label, items]) => (
        <div key={label} className="space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            {label}
          </p>
          <ul className="space-y-1">
            {items.map((fact, index) => (
              <li key={`${fact.value}-${index}`}>
                <button
                  type="button"
                  onClick={() => onShowSource(fact.source.page_number, fact.source.quote)}
                  aria-label={`${fact.value}, ${formatSource(fact.source.page_number, fact.source.clause_ref)}. Show in document`}
                  className="flex w-full items-start justify-between gap-2 rounded-md px-1.5 py-1 text-left text-sm hover:bg-card focus-visible:outline-2 focus-visible:outline-ring"
                >
                  <span className="line-clamp-2">{fact.value}</span>
                  <Badge variant="outline" className="shrink-0 bg-card">
                    {formatSource(fact.source.page_number, fact.source.clause_ref)}
                  </Badge>
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function Snippet({ text, term }: { text: string; term: string | null }) {
  if (!term) return <>{text}</>;
  const parts = text.split(new RegExp(`(${term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi"));
  return (
    <>
      {parts.map((part, index) =>
        part.toLowerCase() === term.toLowerCase() ? (
          <mark key={index} className="rounded-sm bg-amber-200/70 px-0.5 text-foreground">
            {part}
          </mark>
        ) : (
          <span key={index}>{part}</span>
        ),
      )}
    </>
  );
}
