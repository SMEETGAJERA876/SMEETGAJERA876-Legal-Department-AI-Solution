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

// Only letters and digits are compared. Two extractors disagree about more than whitespace:
// brackets, dashes and curly quotes differ between the backend's text and the PDF's own, and
// dropping them also lets a value written one way find the same value written another —
// "6 years" finds "six (6) years", which is how statutes usually write a number.
const SKIPPED = /[^\p{L}\p{N}]/u;

function compactWithMap(items: string[]): { text: string; refs: CharRef[] } {
  let text = "";
  const refs: CharRef[] = [];
  items.forEach((item, itemIndex) => {
    for (let offset = 0; offset < item.length; offset += 1) {
      const ch = item[offset];
      if (SKIPPED.test(ch)) continue;
      text += ch.toLowerCase();
      refs.push({ item: itemIndex, offset });
    }
  });
  return { text, refs };
}

function compact(text: string): string {
  return Array.from(text)
    .filter((ch) => !SKIPPED.test(ch))
    .join("")
    .toLowerCase();
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
 * The numbers in a value, longest first. Two facts often come from one sentence — "a fee of
 * ₹5,000 within 30 days" yields both an amount and a time limit — and the sentence alone
 * cannot tell them apart. The number can.
 */
function numbersIn(value: string): string[] {
  const found = value.match(/\d[\d.,]*/g) ?? [];
  return found
    .map((n) => n.replace(/[.,]+$/, ""))
    .filter(Boolean)
    .sort((a, b) => b.length - a.length);
}

/** Where to mark inside the quote: the focus itself, else the numbers it carries. */
function locateFocus(
  text: string,
  focus: string,
  within: [number, number] | null,
): [number, number] | null {
  const from = within ? within[0] : 0;
  const before = within ? within[1] : text.length;
  for (const candidate of [focus, ...numbersIn(focus)]) {
    const needle = compact(candidate);
    if (!needle) continue;
    const at = text.indexOf(needle, from);
    if (at >= 0 && at < before) return [at, at + needle.length];
  }
  return null;
}

/**
 * @param focus optional words inside the quote to mark precisely — the searched term, or the
 *   value of the fact being shown. The quote finds the right sentence; the focus picks out the
 *   part of it the reader asked about, which is what tells two values in one sentence apart.
 */
export function locateQuote(items: string[], quote: string, focus?: string | null): HighlightMap {
  const { text, refs } = compactWithMap(items);
  let range = findRange(text, compact(quote));
  const map: HighlightMap = new Map();
  if (focus) {
    // A focus that cannot be found leaves the whole quote marked, which is still the right
    // sentence — never nothing.
    range = locateFocus(text, focus, range) ?? range;
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
