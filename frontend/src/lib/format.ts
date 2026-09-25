export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** "12.1" → "Clause 12.1"; "Section 5(1)" and "Rule 7" are already labelled. */
export function formatClause(clause: string): string {
  return /^[A-Z][a-z]/.test(clause) ? clause : `Clause ${clause}`;
}

export function formatSource(page: number, clause: string | null | undefined): string {
  return clause ? `Page ${page} · ${formatClause(clause)}` : `Page ${page}`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
