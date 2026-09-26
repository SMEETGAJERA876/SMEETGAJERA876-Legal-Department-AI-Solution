# Plain language: both directions

Official documents are written in a language most of the people bound by them do not speak.
ClauseLens translates in both directions, and both are needed:

| Direction | Where it is used | Example |
|---|---|---|
| **Everyday → formal**, to *find* the right passage | search and Q&A | you type "builder"; the Act says **promoter**, so that is what is searched for |
| **Formal → everyday**, to *understand* it | answers, and any quoted passage | the Act says "person aggrieved"; you read **person affected** |

## The rule that makes this safe

The plain version is **always shown beside the original, never instead of it**, and the website
labels which is which: *"A simplified version. The original wording above is what counts."*

The rewriter (`backend/app/services/simplify.py`) is a dictionary plus a few structural changes.
That is a deliberate limit. A rewriter that *understood* a clause could also misunderstand it, so
this one only does things that cannot change the meaning:

- replace a formal word or phrase with an everyday one — `lessee` → `tenant`;
- also write a number given in words as digits — `forty-five days` → `45 days`;
- split a very long sentence at a semicolon;
- drop the enumerator and heading that the website already shows separately.

It never drops a number, a date, an amount, a party, a condition or a negation, never reorders
clauses and never adds a fact. `tests/test_simplify.py` holds that property directly: every
amount, date and negation in the input must still appear in the output.

### It says nothing rather than something useless

A passage that is already in everyday words is not shown twice. Only a rewrite that actually
replaced formal wording or a number in words is `worth_showing`; stripping `(b) ` is tidying, not
translation. Likewise "you said X, the document says Y" is only shown when the two words are
genuinely different — `complain` → `complaint` is suppressed, `builder` → `promoter` is not.

## Where it appears

- **In an answer** — an *In simple words* section, plus *Your words in this document's language*
  when an everyday word in the question mapped to different formal wording that the quoted
  passage actually uses.
- **On any quoted passage** — a **Simple words** button, which also lists the formal terms in
  that passage and what each one means.

## Working with an AI key

With `AI_PROVIDER=anthropic` the model writes the explanation instead, and the local rewriter
stays as the fallback. With no key — which is how the public demo runs — everything above still
works, because none of it needs one.

## The dictionaries

| File | Direction | Used by |
|---|---|---|
| [`data/taxonomy/plain_language.json`](../data/taxonomy/plain_language.json) | everyday → formal | search expansion, the re-ranker, the answerability guard |
| [`data/taxonomy/legal_to_plain.json`](../data/taxonomy/legal_to_plain.json) | formal → everyday | the rewriter |

Both are plain JSON and reviewable: a wrong mapping in a legal tool is a real harm, so they are
data a person can read and correct, not weights. Rules are applied longest phrase first, so
`notwithstanding anything contained in` wins over `notwithstanding`.

Adding a term is one line in `legal_to_plain.json`:

```json
{"legal": ["ejectment"], "plain": "eviction"}
```
