# Is this document what it claims to be?

People are sent forged notices, doctored agreements, and AI-drafted documents passed off as
official ones. The **Verify** tab reports evidence about how a file was made — each finding with
the page and the exact words, so a person can check it themselves.

## The line this feature does not cross

**ClauseLens does not run an AI-text detector, and never will decide anything from writing
style.**

Stylometric detection — perplexity, burstiness, and the commercial services built on them — is
unreliable, and it is worst exactly here. Legal and government writing is formal, templated and
repetitive, which is what those detectors score as machine-written. A citizen whose genuine
municipal notice was refused because a detector disliked its prose has been harmed by this tool,
and has no way to argue with it.

So the question is never *"does this read like AI?"* but *"what can this file be shown to
contain?"* `test_authenticity.py` holds that directly: a page of deliberately uniform, formal,
machine-sounding government prose must pass untouched.

## What it looks at

| Signal | Severity | Evidence |
|---|---|---|
| The PDF's producer names an AI writing tool | **high** | the recorded tool name |
| The assistant's own words left in the text — *"Here is a draft"*, *"I cannot provide legal advice"* | **high** | the sentence, with its page |
| Changed before it was created (impossible dates) | **high** | both timestamps |
| Edited more than a day after it was created | medium | both dates |
| Contains an earlier version of itself (saved again over the original) | medium | number of revisions |
| Template placeholders never filled in — `[Your Name]`, `XXXX` | medium | the placeholder, with its page |
| A few words in a typeface the rest of the document never uses | medium | the words, with the page |
| An official notice with no reference number, authority, date or signature | medium | which are absent |
| The pages are images, so there is no text of its own to check | info | — |

The verdict is **`concerns`**, **`check`** or **`ordinary`** — never "fake" or "genuine". Whether
a document is authentic is for the issuing office or a lawyer to say.

## Rejecting a document

`AUTHENTICITY_POLICY` decides what happens when the evidence is strong:

| Value | Behaviour |
|---|---|
| `warn` *(default)* | The document is accepted and opens with a red banner; the Verify tab shows why |
| `reject` | The document is refused. It is marked **Not accepted** with the reason and the evidence, and none of its content is offered |
| `off` | No check is made |

Only **high** signals can refuse a document, and every one of them is a checkable fact about the
file, not an opinion about its prose. A template with placeholders is *flagged but never
refused* — wanting a template explained is a legitimate thing to do.

## How much it fires on real documents

Every genuine document in this repository — 20 Central Acts from India Code and 5 project
samples — is checked on every test run, and all 25 must come back `ordinary` with zero
rejections. That test is the first one in the file, because a false accusation is the failure
that matters here.

Two false positives were found and fixed while building it, both worth recording:

- the word `NOTICE` matched the reference-number pattern (`NO` + `TICE`), so a notice carrying no
  number at all appeared to have one — a missing `\b`;
- `party a` matched *"giving such party a reasonable time"* in the Arbitration Act, flagging it
  as a `Party A` template placeholder. The rule was removed rather than narrowed.

## API

`GET /documents/{id}/authenticity` — see [API.md](API.md). It works on the public demo documents
without signing in. `documents.authenticity_verdict` also comes back on the document itself, so
the website can show the banner before anything is read.
