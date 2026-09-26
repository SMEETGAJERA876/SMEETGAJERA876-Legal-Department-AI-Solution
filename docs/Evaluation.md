# Evaluation

How well ClauseLens works, measured — including where it doesn't. Every number here comes from
an automated test that runs with `uv run pytest` (backend), so it can be reproduced.

## 1. Real statutes from India Code (main benchmark)

**Data.** 8 central Acts downloaded from https://indiacode.gov.in (`scripts/fetch_indiacode.py`),
241 pages: Consumer Protection Act 2019, Right to Information Act 2005, Indian Contract Act 1872,
Real Estate (Regulation and Development) Act 2016, Sexual Harassment of Women at Workplace Act
2013, Protection of Women from Domestic Violence Act 2005, Legal Services Authorities Act 1987,
Code on Wages 2019. Source URL and retrieval date per file in `dataset/indiacode/*.json`.

**Questions.** 44 questions phrased the way a citizen would ask ("Will I get my money back if the
builder delays possession?"), not copied from headings. The expected section of each was checked
by hand against the downloaded text. Plus 8 questions the Acts do **not** answer ("What is the
penalty for drunk driving?" asked of the Consumer Protection Act). `tests/real_document_cases.py`.

**Split — to keep the numbers honest.**
- *dev* (4 Acts, 22 questions): used while improving the system; their failures were inspected.
- *held-out test* (4 Acts, 22 questions): not used for tuning; only final scores were looked at.
  One exception is disclosed below.

**Metrics.** Recall@k — the right section is among the first k results; MRR — mean of 1/rank;
answer correct — the answer is given *and* cites the right section; refusals — unanswerable
questions answered "not found" (the rest would be hallucinated answers).

### Results

| | Recall@1 | Recall@3 | MRR | Right page first | Answer cites right section | Unanswerable refused |
|---|---|---|---|---|---|---|
| Baseline (dev), before this work | 0.59 | 0.82 | 0.700 | 0.59 | 0.73 | 1 / 4 |
| **Final, dev** | **0.91** | **1.00** | **0.947** | 0.91 | **0.95** | **4 / 4** |
| **Final, held-out test** | **0.86** | **1.00** | **0.924** | 0.95 | **1.00** | **4 / 4** |

Document type: all 8 Acts recognised as *Act* with **high** confidence (baseline: 6 of 8 correct,
none high — the RTI Act was taken for an RTI application, the Code on Wages was not recognised).

**Disclosure.** The first held-out run refused 3 of 4 unanswerable questions: "What is the
punishment for cybercrime?" (Code on Wages) was answered because the generic word "punishment"
counted as half the question's subject. The fix (generic words never count as subject, through
any path) is general and has a unit test, but it was made after seeing a held-out result, so the
honest held-out figure for refusals is **3/4 before the fix, 4/4 after**. Held-out retrieval on the
first run was Recall@1 0.82, Recall@3 1.00, MRR 0.902, answer 1.00.

### What made the difference

| Change | Why it was needed (found on real Acts) |
|---|---|
| Statute structure: `12. Heading.—(1) …` headings, sections ≥ 100, `73.Compensation` without a space | headings were dropped; the Contract Act's sections 100–238 were invisible |
| Table of contents, amendment footnotes, schedules and Statement of Objects kept apart | "Arrangement of Sections" and footnotes (`1. Subs. by Act …`) posed as duplicate sections |
| Diagonal watermark removal | India Code's "IndiaCode" watermark was spliced into sentences ("IndiaCodeupon") |
| Act number signal for classification | "(ACT NO. 22 OF 2005)" is the most reliable marker of an Act |
| Cross-encoder re-ranking (MiniLM-L-6) | Recall@1 0.59 → 0.77 on dev |
| Plain-language glossary given to the re-ranker | Recall@1 0.77 → 0.91 on dev ("builder" ↔ promoter, "salary" ↔ wages) |
| Answerability guard | refusals 1/4 → 4/4 on dev without refusing any answerable question |

Models compared on dev: `BAAI/bge-reranker-base` reached Recall@1 0.64 at ~3 s/question;
`ms-marco-MiniLM-L-12` 0.77 at ~1 s; **`ms-marco-MiniLM-L-6` 0.77 at ~0.4 s (chosen)**.

### Three faults this evaluation found, and what they were

Each was a real defect in the system, found by the suite rather than by reading the code, and
each was fixed at the cause rather than by relaxing the test.

| Symptom | Cause |
|---|---|
| "What is my notice period?" answered **14 days** (probation) instead of **90 days** (termination) | The one-passage-per-section diversity pass demoted *every* sibling of a top hit regardless of relevance. The clause carrying "ninety (90) days" had the 2nd-best score and 4th-best re-ranker relevance in the document and was pushed to rank 11 — outside the retrieval window. Diversity may now reorder results but never evict one. |
| The Registration Act 1908 recognised as an Act with only **medium** confidence | Its Act number sits on page 4, behind a multi-page arrangement of sections, outside the 2-page classification window — and is printed `ACT NO. 16 OF 1908` without the brackets the pattern required. The number is now looked for across the front matter, anchored to a line start so a cross-reference inside a sentence does not make every document quoting a statute look like one. |
| "What is the minimum wage for factory workers?" **answered** by the Transfer of Property Act | Subject words are matched by stem so that "children" finds "child". Trimming to four characters was too much: "factory" became "fact" and "workers" became "work", both of which occur in almost any statute, so an Act about land scored 2/3 coverage on factory wages. The stem floor is now five characters — every one of the 105 answerable evaluation questions keeps its coverage, and two more unanswerable ones are correctly seen as uncovered. Separately, a strong cross-encoder score no longer bypasses the subject check when *nothing* in the subject appears in the document: confidence can bridge different wording for the same thing, it cannot supply a subject that is absent. |

### Remaining misses (all shown by the test with `-s`)

- dev: "What can I do if I don't get a reply to my RTI?" — the appeal section (19) ranks 3rd and
  the answer cites section 7 (time limit for replying), which is related but not the remedy.
- dev: RERA appeal time limit — right section ranked 2nd.
- held-out: three questions with the right section ranked 2nd–3rd (answers still cite it).

## 2. Synthetic samples (regression suite)

Three project-made documents (employment agreement, government notice, tenancy Act/Rules) and a
rental agreement with deliberate mistakes.

| Test file | What it checks | Result |
|---|---|---|
| `test_evaluation.py` | 25 end-to-end questions: right answer, page, typo tolerance, "not found", "why use this?" | 25/25 |
| `test_retrieval.py` | 27 retrieval queries, hybrid vs meaning-only | hybrid ≥ meaning-only; Recall@3 ≥ 0.95, MRR ≥ 0.9 |
| `test_extraction.py` | 31 extraction cases for 44 concepts | precision ≥ 0.95, recall ≥ 0.95 |
| `test_classification.py` | 34 documents across categories | all correct; low-confidence never names a type |
| `test_document_check.py` | mistakes found with page + suggestion; auto-repair verified in the new PDF | pass |
| `test_ocr.py` | image-only (scanned) copy of the agreement: text read, answers cite the right page | pass |
| `test_simplify.py` | plain-language rewriting keeps every amount, date, party and negation | pass |
| `test_formats.py` | comparison against the official format, on complete and incomplete documents | pass |
| `test_authenticity.py` | forged / AI-drafted documents caught; **all 25 real documents pass with zero rejections** | pass |
| `test_demo.py` | the public demo is readable by anyone and writable by nobody | pass |

These were written by the developers and are easier than real documents — which is why §1 exists.

## 3. Security and reliability tests

`test_auth.py` (sign-in required; other users get 404 on all 13 document routes; non-Google
tokens refused), `test_security.py` (files encrypted on disk and byte-identical when downloaded;
tampering detected; headers; rate limits with `429`; insecure production settings refused; audit
log; delete-all; retention; interrupted processing resumed), `test_answerability.py`.

**Total: 280 automated tests, all passing.** Lint (ruff), type checks (mypy strict, `tsc`), ESLint
and the production build are clean.

## Performance

`uv run python -m scripts.benchmark` — one API process, laptop CPU, no GPU, all models local:

| Measure | Result |
|---|---|
| Processing (upload → ready) | 1.3 pages/s — a 42-page Act in 34 s, a 12-page Act in 7 s |
| OCR of a scanned page | ~3 s per page |
| Question, one user | p50 1.0 s, p95 1.6 s |
| 10 users asking at once (50 questions) | p50 3.5 s, p95 6.8 s, **2.6 questions/s** |

Batching sentence embeddings and a 12-passage re-ranking pool (same accuracy as 20) took
single-user latency from ~1.4 s to 1.0 s and doubled throughput (1.3 → 2.6 questions/s). The
models are CPU-bound, so capacity grows with workers and replicas
([Architecture.md § Scaling](Architecture.md#scaling)); the production image runs 2 workers.

## Limitations

- English only (Hindi and regional-language documents are not supported yet).
- The evaluation questions were written by the developers (on real documents); no study with
  real users yet.
- OCR quality depends on the scan; answers from OCR'd pages carry a warning, and highlighting in
  the PDF is not available for scanned pages (they have no text layer).
- Answers without an AI key are quotes and extracted values, not explanations; the optional
  Claude provider adds plain-language explanations but was not part of these measurements.
