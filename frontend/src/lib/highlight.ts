/**
 * Locate a quote inside a PDF page's text items so it can be highlighted.
 *
 * PDF.js splits page text into items (roughly lines). The backend's text comes from a
 * different extractor, so whitespace differs; matching ignores whitespace and case.
 * If the quote can't be located, nothing is highlighted — we never pretend.
 */

export type ItemRange = { start: number; end: number }; // character offsets within one item

export type HighlightMap = Map<number, ItemRange>;

type CharRef = { item: number; offset: number };

const MIN_PARTIAL_MATCH = 24;

function isSpace(ch: string): boolean {
  return /\s/.test(ch);
}

function compactWithMap(items: string[]): { text: string; refs: CharRef[] } {
  let text = "";
  const refs: CharRef[] = [];
  items.forEach((item, itemIndex) => {
    for (let offset = 0; offset < item.length; offset += 1) {
      const ch = item[offset];
      if (isSpace(ch)) continue;
      text += ch.toLowerCase();
      refs.push({ item: itemIndex, offset });
    }
  });
  return { text, refs };
}

function compact(text: string): string {
  return text.replace(/\s+/g, "").replace(/…/g, "").toLowerCase();
}

function findRange(haystack: string, needle: string): [number, number] | null {
  if (!needle) return null;
  const exact = haystack.indexOf(needle);
  if (exact >= 0) return [exact, exact + needle.length];
  // The quote may continue onto the next page: try its beginning, then its end.
  if (needle.length > MIN_PARTIAL_MATCH * 2) {
    const head = needle.slice(0, Math.max(MIN_PARTIAL_MATCH, Math.floor(needle.length / 2)));
    const headAt = haystack.indexOf(head);
    if (headAt >= 0) return [headAt, headAt + head.length];
    const tail = needle.slice(-Math.max(MIN_PARTIAL_MATCH, Math.floor(needle.length / 2)));
    const tailAt = haystack.indexOf(tail);
    if (tailAt >= 0) return [tailAt, tailAt + tail.length];
  }
  return null;
}

/**
 * @param focus optional words inside the quote to mark precisely (e.g. the searched term);
 *   the quote itself is used to find the right occurrence on the page.
 */
export function locateQuote(items: string[], quote: string, focus?: string | null): HighlightMap {
  const { text, refs } = compactWithMap(items);
  let range = findRange(text, compact(quote));
  const map: HighlightMap = new Map();
  if (focus) {
    const needle = compact(focus);
    const searchFrom = range ? range[0] : 0;
    const at = needle ? text.indexOf(needle, searchFrom) : -1;
    if (at >= 0 && (!range || at < range[1])) range = [at, at + needle.length];
  }
  if (!range) return map;
  for (let i = range[0]; i < range[1]; i += 1) {
    const { item, offset } = refs[i];
    const current = map.get(item);
    map.set(item, {
      start: current ? Math.min(current.start, offset) : offset,
      end: current ? Math.max(current.end, offset + 1) : offset + 1,
    });
  }
  return map;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Render one text item as HTML, wrapping the highlighted part in <mark>. */
export function renderItem(text: string, range: ItemRange | undefined): string {
  if (!range) return escapeHtml(text);
  return (
    escapeHtml(text.slice(0, range.start)) +
    `<mark class="clause-highlight">${escapeHtml(text.slice(range.start, range.end))}</mark>` +
    escapeHtml(text.slice(range.end))
  );
}
