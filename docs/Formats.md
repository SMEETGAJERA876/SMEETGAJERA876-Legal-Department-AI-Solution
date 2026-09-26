# Comparing a document against the official format

Someone is handed a rent agreement, an appointment letter or an affidavit and has no way to tell
whether it contains what such a document is *supposed* to contain. The **Format** tab answers
that: what a document of this kind is expected to have, and what this one actually has.

On the demo's rental agreement it reports **6 of 11 required parts found** — no stamp duty
details, no signatures, no witnesses, no maintenance clause, and a property description sitting
next to an unfilled blank.

## What it reports

| | Meaning |
|---|---|
| **Found** | The part is there, with the page and the exact words |
| **Left blank** | The part is there but the words after it are an unfilled blank — `Date: ______` |
| **Missing** | No wording for this part appears anywhere in the document |

Required parts are separated from optional ones, and the score counts only the required ones.

## What it is not

**A checklist, not a ruling.** The comparison is by wording, so it is evidence, not proof:

- a part written in unusual words can be reported as missing when it is really there;
- a matched phrase can belong to a different sentence.

So every finding that is found carries **the page and the exact words**, and the panel says
plainly that a missing part is something to ask about, not proof that the document is invalid.
ClauseLens does not tell anyone their document is void — that is a lawyer's call, and the panel
sends them to the *Questions to ask a legal professional* list.

## The formats

[`data/formats/document_formats.json`](../data/formats/document_formats.json) — authored,
versioned, reviewable JSON, keyed to the taxonomy types in
[`Document_Taxonomy.md`](Document_Taxonomy.md).

| Format | Document types | Expected by |
|---|---|---|
| Rent or lease agreement | `property.rental_agreement`, `property.lease_agreement` | Registration Act 1908, Indian Stamp Act 1899, State tenancy law |
| Employment agreement or appointment letter | `employment.employment_agreement`, `.appointment_letter`, `.offer_letter` | Code on Wages 2019, Shops and Establishments Acts |
| Affidavit | `court.affidavit`, `court.counter_affidavit` | CPC 1908, Order XIX and s. 139 |
| RTI application | `government.rti_document` | Right to Information Act 2005, s. 6 |
| Legal notice | `other.legal_notice`, `employment.show_cause_notice`, `financial.recovery_notice` | General practice; NI Act 1881, s. 138(b) for a cheque bounce |
| Sale deed | `property.sale_deed` | Transfer of Property Act 1882 s. 54, Registration Act 1908 s. 17 |
| Act of Parliament as published | `policy.act` | The form Central Acts are published in |

A document whose type has no format described says so, and lists what *can* be compared.

Each part carries a `why` — one sentence saying what it is for and which provision asks for it —
so the reader learns something rather than being handed a bare cross. For example, on stamp duty:
*"An instrument that is not duly stamped is not admissible as evidence (Indian Stamp Act 1899,
s. 35)."*

## Adding a format

```json
{
  "id": "power_of_attorney",
  "name": "Power of attorney",
  "document_type_ids": ["legal.power_of_attorney"],
  "authority": "Powers-of-Attorney Act 1882; Registration Act 1908",
  "note": "A POA for immovable property must be registered.",
  "parts": [
    {
      "id": "principal",
      "label": "Principal's name and address",
      "required": true,
      "patterns": ["principal", "executant", "i,"],
      "why": "Says who is giving the authority."
    }
  ]
}
```

`tests/test_formats.py` then holds it to the rules automatically: every `document_type_ids` entry
must exist in the taxonomy, no two formats may claim the same type, every part needs an `id`, a
`label`, a `why` and at least one pattern, and every format needs at least one required part.

## API

`GET /documents/{id}/format-check` — see [API.md](API.md). It works on the public demo documents
without signing in.
