# Document Taxonomy

Version **1.0.0** · Source of truth: [`data/taxonomy/document_types.json`](../data/taxonomy/document_types.json) · 11 categories · 178 document types

The taxonomy tells ClauseLens *what kind of document* it is looking at, so it knows which structure to expect (parties and clauses in a contract, facts and findings in a judgment, eligibility and deadlines in a public notice) and which information to look for.

## 1. File format is not document type

Two independent properties are stored for every document:

| Property | Question it answers | Examples | Stored in |
|---|---|---|---|
| **File format** | How are the bytes stored? | `pdf`, `docx`, `jpg`, `png` | `document.format` |
| **Document type** | What is this document? | `employment.employment_agreement`, `court.judgment` | `document.classification.document_type` |
| **Category** | Which family does it belong to? | `employment`, `court`, `government` | `document.classification.category` |

| File | Format | Document type | Category | OCR |
|---|---|---|---|---|
| `employment_agreement.pdf` | PDF | `employment.employment_agreement` | Employment | Only if scanned |
| `government_notice.docx` | DOCX | `government.notification` / `public_notice.public_notice` | Government / Public notices | No |
| `court_order.jpg` | JPG | `court.order` | Court / Judicial | **Required** |

A document type never implies a format, and a format never implies a type.

## 2. Identifiers

- Every type has a stable id `<category>.<snake_case_name>`, e.g. `government.circular`, `legal.nda`, `court.judgment`.
- Ids are **never renamed or reused**. To retire a type, keep the id and mark it deprecated in a later version.
- A type that belongs to more than one family has **one canonical id** plus `secondary_categories` (an NDA is `legal.nda`, secondary `employment`, `corporate`) — never two ids for the same thing.
- `other.unknown` is the explicit answer when a document cannot be classified with confidence (see [Document_Classification.md](Document_Classification.md)). It is never a silent default.

## 3. Categories

| Id | Name | Description |
|---|---|---|
| `government` | Government | Documents issued by a government, ministry, department or public authority. |
| `legal` | Legal / Contracts | Agreements and contracts between parties, and terms that bind users of a service. |
| `employment` | Employment | Documents about a job: offers, contracts, HR policies, warnings and exit letters. |
| `court` | Court / Judicial | Documents produced by or filed in courts and tribunals. |
| `corporate` | Corporate / Company | Documents of companies: constitution, resolutions, reports, policies and commercial agreements. |
| `public_notice` | Public Notices | Notices addressed to the public: recruitment, exams, admissions, auctions, utilities, advisories. |
| `financial` | Financial | Loans, insurance, invoices, tax and bank documents. |
| `property` | Property | Documents about land and buildings: sale, lease, registration, possession, tax. |
| `education` | Education | Documents of schools and universities: admissions, rules, scholarships, fees, hostels. |
| `policy` | Policy / Regulatory | Policies, rules, regulations, standards and guidelines that set requirements. |
| `other` | Other Official Documents | Official documents that do not fit another category, or cannot be classified with confidence. |

## 4. File formats

| Group | Formats |
|---|---|
| MVP (designed) | pdf, docx, jpg, jpeg, png |
| Secondary (designed) | doc, txt, tiff, xlsx, xls, csv, pptx, html, htm, xml, eml, msg |
| **Implemented today** | pdf (text-based) |

**OCR requirements:** images (JPG, JPEG, PNG, TIFF) always need OCR. PDFs need OCR only when a page has no selectable text (a scanned PDF). Types marked *often scanned* below (court papers, deeds, affidavits, certificates, forms) are frequently received as scans, so the pipeline should expect OCR for them. OCR is not implemented yet; see [AI_Pipeline.md](AI_Pipeline.md).

## 5. Document types by category

### Government (`government`)

Documents issued by a government, ministry, department or public authority.

**Typical structure:** Government / Department → Reference number → Date → Subject → Authority → Background → Purpose → Orders / Provisions → Effective date → Conditions → Responsibilities → Signature / Authority → Annexures

**Expected fields:** `authority`, `reference_number`, `date`, `subject`, `effective_date`, `signatory`

| Id | Name | Also in | Title cues | Often scanned |
|---|---|---|---|---|
| `government.notification` | Notification | — | “notification”, “it is hereby notified” |  |
| `government.order` | Order | — | “government order”, “g.o.”, “it is hereby ordered” |  |
| `government.circular` | Circular | — | “circular” |  |
| `government.office_memorandum` | Office Memorandum | — | “office memorandum”, “o.m.” |  |
| `government.departmental_circular` | Departmental Circular | — | “departmental circular” |  |
| `government.gazette_notification` | Gazette Notification | — | “gazette”, “extraordinary” |  |
| `government.official_notice` | Official Notice | — | “official notice” |  |
| `government.administrative_order` | Administrative Order | — | “administrative order” |  |
| `government.executive_order` | Executive Order | — | “executive order” |  |
| `government.resolution` | Resolution | — | “government resolution”, “resolved that” |  |
| `government.bye_laws` | Bye-laws | policy | “bye-laws”, “byelaws”, “by-laws” |  |
| `government.recruitment_notification` | Recruitment Notification | public_notice, employment | “recruitment”, “vacancies”, “applications are invited” |  |
| `government.tender_notice` | Tender Notice | public_notice, financial | “tender”, “bids are invited”, “e-tender” |  |
| `government.procurement_document` | Procurement Document | financial | “procurement”, “request for proposal”, “rfp”, “bid document” |  |
| `government.corrigendum` | Corrigendum | — | “corrigendum”, “erratum” |  |
| `government.amendment_notification` | Amendment Notification | — | “amendment”, “amended as follows” |  |
| `government.press_release` | Press Release | — | “press release”, “press note” |  |
| `government.public_consultation` | Public Consultation | policy, public_notice | “public consultation”, “comments are invited”, “consultation paper” |  |
| `government.rti_document` | RTI Document | — | “right to information”, “rti”, “public information officer” |  |
| `government.government_form` | Government Form | — | “form no”, “application form” | yes |
| `government.application_guidelines` | Application Guidelines | public_notice | “guidelines for applicants”, “how to apply”, “application guidelines” |  |
| `government.advisory` | Advisory | public_notice | “advisory” |  |

### Legal / Contracts (`legal`)

Agreements and contracts between parties, and terms that bind users of a service.

**Typical structure:** Title → Parties → Recitals / Background → Definitions → Scope → Obligations → Payment → Term → Renewal → Termination → Confidentiality → Intellectual property → Liability → Indemnification → Warranty → Dispute resolution → Governing law → Jurisdiction → Notice → Amendments → Assignment → Signatures → Schedules → Annexures

**Expected fields:** `parties`, `effective_date`, `term`, `payment`, `termination`, `notice_period`, `governing_law`

| Id | Name | Also in | Title cues | Often scanned |
|---|---|---|---|---|
| `legal.service_agreement` | Service Agreement | corporate | “service agreement”, “services agreement” |  |
| `legal.consulting_agreement` | Consulting Agreement | — | “consulting agreement”, “consultancy agreement” |  |
| `legal.vendor_agreement` | Vendor Agreement | corporate | “vendor agreement” |  |
| `legal.partnership_agreement` | Partnership Agreement | corporate | “partnership agreement”, “partnership deed” |  |
| `legal.franchise_agreement` | Franchise Agreement | corporate | “franchise agreement” |  |
| `legal.sale_agreement` | Sale Agreement | property | “agreement for sale”, “sale agreement” |  |
| `legal.purchase_agreement` | Purchase Agreement | corporate | “purchase agreement” |  |
| `legal.distribution_agreement` | Distribution Agreement | corporate | “distribution agreement”, “distributor” |  |
| `legal.nda` | NDA | employment, corporate | “non-disclosure agreement”, “confidentiality agreement”, “nda” |  |
| `legal.non_compete_agreement` | Non-Compete Agreement | employment | “non-compete”, “non-competition” |  |
| `legal.non_solicitation_agreement` | Non-Solicitation Agreement | employment | “non-solicitation” |  |
| `legal.licensing_agreement` | Licensing Agreement | — | “licence agreement”, “license agreement”, “licensing agreement” |  |
| `legal.software_license_agreement` | Software License Agreement | — | “software licence”, “software license”, “end user licence”, “eula” |  |
| `legal.saas_agreement` | SaaS Agreement | corporate | “saas”, “software as a service”, “subscription agreement” |  |
| `legal.master_service_agreement` | Master Service Agreement | corporate | “master service agreement”, “master services agreement”, “msa” |  |
| `legal.statement_of_work` | Statement of Work | corporate | “statement of work”, “sow” |  |
| `legal.memorandum_of_understanding` | Memorandum of Understanding | government, corporate | “memorandum of understanding”, “mou” |  |
| `legal.memorandum_of_agreement` | Memorandum of Agreement | — | “memorandum of agreement”, “moa” |  |
| `legal.settlement_agreement` | Settlement Agreement | court | “settlement agreement”, “full and final settlement” |  |
| `legal.indemnity_agreement` | Indemnity Agreement | — | “indemnity agreement”, “indemnity bond”, “deed of indemnity” |  |
| `legal.joint_venture_agreement` | Joint Venture Agreement | corporate | “joint venture” |  |
| `legal.terms_of_service` | Terms of Service | corporate | “terms of service”, “terms of use” |  |
| `legal.terms_and_conditions` | Terms and Conditions | corporate | “terms and conditions”, “t&c” |  |
| `legal.privacy_policy` | Privacy Policy | corporate | “privacy policy”, “privacy notice” |  |
| `legal.refund_policy` | Refund Policy | corporate | “refund policy” |  |
| `legal.cancellation_policy` | Cancellation Policy | corporate | “cancellation policy” |  |

### Employment (`employment`)

Documents about a job: offers, contracts, HR policies, warnings and exit letters.

**Typical structure:** Title / Letterhead → Employer and employee → Position → Compensation → Probation → Working hours → Leave → Benefits → Confidentiality → Intellectual property → Termination → Notice period → Restrictive covenants → Dispute resolution → Signatures

**Expected fields:** `employer`, `employee`, `job_title`, `joining_date`, `salary`, `notice_period`

| Id | Name | Also in | Title cues | Often scanned |
|---|---|---|---|---|
| `employment.offer_letter` | Offer Letter | — | “offer letter”, “pleased to offer” |  |
| `employment.appointment_letter` | Appointment Letter | — | “appointment letter”, “letter of appointment”, “pleased to appoint” |  |
| `employment.employment_agreement` | Employment Agreement | legal | “employment agreement”, “contract of employment”, “employment contract” |  |
| `employment.internship_agreement` | Internship Agreement | education | “internship agreement”, “internship offer”, “intern” |  |
| `employment.joining_letter` | Joining Letter | — | “joining letter”, “joining report” |  |
| `employment.promotion_letter` | Promotion Letter | — | “promotion letter”, “pleased to promote” |  |
| `employment.salary_revision_letter` | Salary Revision Letter | — | “salary revision”, “revised compensation”, “increment letter” |  |
| `employment.employee_handbook` | Employee Handbook | corporate | “employee handbook”, “code of conduct” |  |
| `employment.hr_policy` | HR Policy | corporate | “hr policy”, “human resources policy” |  |
| `employment.leave_policy` | Leave Policy | corporate | “leave policy” |  |
| `employment.work_from_home_policy` | Work From Home Policy | corporate | “work from home”, “wfh policy”, “remote work policy” |  |
| `employment.remote_work_agreement` | Remote Work Agreement | — | “remote work agreement”, “telework agreement” |  |
| `employment.termination_letter` | Termination Letter | — | “termination letter”, “termination of employment”, “services are terminated” |  |
| `employment.resignation_acceptance` | Resignation Acceptance | — | “resignation acceptance”, “acceptance of resignation” |  |
| `employment.experience_letter` | Experience Letter | — | “experience letter”, “experience certificate”, “to whom it may concern” |  |
| `employment.relieving_letter` | Relieving Letter | — | “relieving letter”, “relieved from” |  |
| `employment.warning_letter` | Warning Letter | — | “warning letter”, “final warning” |  |
| `employment.show_cause_notice` | Show Cause Notice | government | “show cause notice”, “show cause” |  |
| `employment.performance_improvement_plan` | Performance Improvement Plan | — | “performance improvement plan”, “pip” |  |
| `employment.disciplinary_notice` | Disciplinary Notice | — | “disciplinary notice”, “disciplinary action”, “charge sheet” |  |
| `employment.employee_consent_form` | Employee Consent Form | — | “consent form”, “i hereby consent” |  |

**Employment Agreement structure:** Title → Parties → Appointment / Position → Commencement → Probation → Duties → Compensation → Working hours and leave → Confidentiality → Intellectual property → Termination → Notice period → Non-compete / Non-solicitation → Governing law → Signatures

### Court / Judicial (`court`)

Documents produced by or filed in courts and tribunals.

**Typical structure:** Court name → Case number → Case type → Parties → Bench / Judge → Date → Background → Facts → Issues → Arguments → Evidence → Law / Precedents → Court's analysis → Findings → Order / Directions → Signature

**Expected fields:** `court_name`, `case_number`, `parties`, `judge`, `date`, `final_order`

| Id | Name | Also in | Title cues | Often scanned |
|---|---|---|---|---|
| `court.judgment` | Judgment | — | “judgment”, “judgement”, “coram”, “delivered by” | yes |
| `court.order` | Order | — | “court order”, “it is ordered”, “order sheet” | yes |
| `court.interim_order` | Interim Order | — | “interim order”, “ad-interim”, “interim relief” | yes |
| `court.final_order` | Final Order | — | “final order” | yes |
| `court.decree` | Decree | — | “decree” | yes |
| `court.petition` | Petition | — | “petition”, “petitioner”, “writ petition” | yes |
| `court.plaint` | Plaint | — | “plaint”, “plaintiff” | yes |
| `court.written_statement` | Written Statement | — | “written statement” | yes |
| `court.affidavit` | Affidavit | legal | “affidavit”, “deponent”, “solemnly affirm” | yes |
| `court.application` | Application | — | “interlocutory application”, “application under section” | yes |
| `court.reply` | Reply | — | “reply on behalf of”, “reply affidavit” | yes |
| `court.rejoinder` | Rejoinder | — | “rejoinder” | yes |
| `court.counter_affidavit` | Counter-Affidavit | — | “counter affidavit”, “counter-affidavit” | yes |
| `court.court_notice` | Court Notice | — | “court notice”, “notice is hereby given that the case” | yes |
| `court.summons` | Summons | — | “summons”, “you are hereby summoned” | yes |
| `court.warrant` | Warrant | — | “warrant of arrest”, “warrant” | yes |
| `court.bail_order` | Bail Order | — | “bail”, “released on bail” | yes |
| `court.appeal` | Appeal | — | “memorandum of appeal”, “appellant” | yes |
| `court.revision_petition` | Revision Petition | — | “revision petition”, “criminal revision”, “civil revision” | yes |
| `court.review_petition` | Review Petition | — | “review petition” | yes |
| `court.evidence_document` | Evidence Document | — | “exhibit”, “evidence” | yes |
| `court.written_submissions` | Written Submissions | — | “written submissions”, “written arguments” |  |
| `court.legal_memorandum` | Legal Memorandum | — | “legal memorandum”, “memo of parties” |  |

**Judgment structure:** Court name → Case number → Parties → Coram / Bench → Date → Facts → Arguments → Issues → Evidence → Applicable law → Court's reasoning → Findings → Final order

### Corporate / Company (`corporate`)

Documents of companies: constitution, resolutions, reports, policies and commercial agreements.

**Typical structure:** Company name → Document number / date → Purpose / Scope → Definitions → Provisions / Policy statements → Responsibilities → Compliance → Approval / Signatures

**Expected fields:** `company`, `effective_date`, `scope`, `responsibilities`, `approver`

| Id | Name | Also in | Title cues | Often scanned |
|---|---|---|---|---|
| `corporate.memorandum_of_association` | Memorandum of Association | — | “memorandum of association” |  |
| `corporate.articles_of_association` | Articles of Association | — | “articles of association” |  |
| `corporate.board_resolution` | Board Resolution | — | “board resolution”, “resolved that the board” |  |
| `corporate.shareholder_resolution` | Shareholder Resolution | — | “shareholders' resolution”, “special resolution”, “ordinary resolution” |  |
| `corporate.shareholder_agreement` | Shareholder Agreement | legal | “shareholders agreement”, “shareholder agreement” |  |
| `corporate.annual_report` | Annual Report | financial | “annual report”, “directors' report” |  |
| `corporate.company_policy` | Company Policy | — | “company policy”, “policy statement” |  |
| `corporate.internal_circular` | Internal Circular | — | “internal circular”, “internal memo” |  |
| `corporate.compliance_notice` | Compliance Notice | — | “compliance notice”, “non-compliance” |  |
| `corporate.customer_agreement` | Customer Agreement | legal | “customer agreement” |  |
| `corporate.supplier_agreement` | Supplier Agreement | legal | “supplier agreement”, “supply agreement” |  |
| `corporate.cookie_policy` | Cookie Policy | legal | “cookie policy”, “cookies” |  |
| `corporate.acceptable_use_policy` | Acceptable Use Policy | legal | “acceptable use” |  |
| `corporate.data_protection_policy` | Data Protection Policy | policy | “data protection”, “personal data” |  |
| `corporate.information_security_policy` | Information Security Policy | policy | “information security”, “infosec” |  |
| `corporate.procurement_policy` | Procurement Policy | — | “procurement policy”, “purchase policy” |  |
| `corporate.compliance_policy` | Compliance Policy | policy | “compliance policy”, “anti-bribery”, “whistleblower” |  |

### Public Notices (`public_notice`)

Notices addressed to the public: recruitment, exams, admissions, auctions, utilities, advisories.

**Typical structure:** Authority → Notice number → Date → Subject → Purpose → Eligibility → Important dates → Deadline → Required documents → Fee → Procedure → Contact information → Authority / Signatory

**Expected fields:** `authority`, `notice_number`, `date`, `deadline`, `eligibility`, `fee`, `contact`

| Id | Name | Also in | Title cues | Often scanned |
|---|---|---|---|---|
| `public_notice.public_notice` | Public Notice | government | “public notice”, “notice is hereby given” |  |
| `public_notice.examination_notice` | Examination Notice | education | “examination notice”, “exam schedule”, “admit card” |  |
| `public_notice.admission_notice` | Admission Notice | education | “admission notice”, “admissions open” |  |
| `public_notice.auction_notice` | Auction Notice | property, financial | “auction notice”, “e-auction”, “sale notice” |  |
| `public_notice.property_notice` | Property Notice | property | “property notice” |  |
| `public_notice.land_acquisition_notice` | Land Acquisition Notice | property, government | “land acquisition” |  |
| `public_notice.tax_notice` | Tax Notice | financial, government | “tax notice”, “demand notice”, “assessment” |  |
| `public_notice.utility_notice` | Utility Notice | — | “electricity”, “water supply”, “power shutdown” |  |
| `public_notice.transport_notice` | Transport Notice | — | “transport notice”, “traffic advisory”, “route diversion” |  |
| `public_notice.railway_notice` | Railway Notice | — | “railway”, “train services” |  |
| `public_notice.municipal_notice` | Municipal Notice | government | “municipal corporation”, “municipality”, “nagar” |  |
| `public_notice.environmental_notice` | Environmental Notice | government | “environmental clearance”, “pollution control” |  |
| `public_notice.health_advisory` | Health Advisory | government | “health advisory”, “public health” |  |
| `public_notice.disaster_management_notice` | Disaster Management Notice | government | “disaster management”, “evacuation”, “cyclone”, “flood warning” |  |
| `public_notice.school_notice` | School Notice | education | “school notice”, “dear parents” |  |
| `public_notice.university_notice` | University Notice | education | “university notice”, “registrar” |  |
| `public_notice.public_announcement` | Public Announcement | — | “public announcement” |  |

**Public Notice structure:** Authority → Notice number and date → Subject → Notice text → Eligibility → Important dates → Documents required → Fee → Procedure → Contact → Signatory

### Financial (`financial`)

Loans, insurance, invoices, tax and bank documents.

**Typical structure:** Parties → Amount → Currency → Interest / Premium → Payment schedule → Due dates → Late fee / Penalty → Default → Security / Collateral → Signatures

**Expected fields:** `amount`, `currency`, `interest_rate`, `due_date`, `late_fee`, `penalty`

| Id | Name | Also in | Title cues | Often scanned |
|---|---|---|---|---|
| `financial.loan_agreement` | Loan Agreement | legal | “loan agreement”, “borrower”, “lender” |  |
| `financial.credit_agreement` | Credit Agreement | legal | “credit agreement”, “credit facility” |  |
| `financial.mortgage_agreement` | Mortgage Agreement | property, legal | “mortgage”, “mortgagor” |  |
| `financial.insurance_policy` | Insurance Policy | legal | “insurance policy”, “policy schedule”, “sum insured”, “insured” |  |
| `financial.insurance_claim` | Insurance Claim | — | “claim form”, “claim settlement” | yes |
| `financial.invoice` | Invoice | — | “invoice”, “bill to”, “gstin” |  |
| `financial.purchase_order` | Purchase Order | corporate | “purchase order”, “p.o. no” |  |
| `financial.tax_document` | Tax Document | government | “income tax”, “form 16”, “assessment year” |  |
| `financial.gst_document` | GST Document | government | “gst”, “goods and services tax”, “gstr” |  |
| `financial.financial_statement` | Financial Statement | corporate | “balance sheet”, “profit and loss”, “financial statement” |  |
| `financial.audit_report` | Audit Report | corporate | “audit report”, “auditor's report” |  |
| `financial.bank_notice` | Bank Notice | — | “bank notice”, “dear customer” |  |
| `financial.payment_notice` | Payment Notice | — | “payment notice”, “payment due”, “reminder” |  |
| `financial.recovery_notice` | Recovery Notice | legal | “recovery notice”, “sarfaesi”, “outstanding dues” |  |

### Property (`property`)

Documents about land and buildings: sale, lease, registration, possession, tax.

**Typical structure:** Parties → Property description → Address → Area → Consideration / Rent → Deposit → Term → Possession → Registration → Restrictions → Termination → Signatures / Witnesses

**Expected fields:** `property`, `owner`, `address`, `area`, `rent`, `deposit`, `sale_price`

| Id | Name | Also in | Title cues | Often scanned |
|---|---|---|---|---|
| `property.sale_deed` | Sale Deed | legal | “sale deed”, “conveyance deed” | yes |
| `property.lease_agreement` | Lease Agreement | legal | “lease agreement”, “lease deed”, “lessor”, “lessee” |  |
| `property.rental_agreement` | Rental Agreement | legal | “rental agreement”, “rent agreement”, “leave and licence”, “tenancy agreement” |  |
| `property.property_agreement` | Property Agreement | legal | “property agreement” |  |
| `property.property_tax_notice` | Property Tax Notice | government, financial | “property tax” |  |
| `property.possession_letter` | Possession Letter | — | “possession letter”, “handing over possession” |  |
| `property.allotment_letter` | Allotment Letter | — | “allotment letter”, “allotted” |  |
| `property.registration_document` | Registration Document | government | “registration”, “sub-registrar” | yes |
| `property.power_of_attorney` | Power of Attorney | legal | “power of attorney” | yes |
| `property.development_agreement` | Development Agreement | legal | “development agreement”, “joint development” |  |
| `property.gift_deed` | Gift Deed | legal | “gift deed” | yes |

### Education (`education`)

Documents of schools and universities: admissions, rules, scholarships, fees, hostels.

**Typical structure:** Institution → Reference / Date → Scope → Eligibility → Rules / Regulations → Fees → Deadlines → Discipline → Contact

**Expected fields:** `institution`, `eligibility`, `fee`, `deadline`, `procedure`

| Id | Name | Also in | Title cues | Often scanned |
|---|---|---|---|---|
| `education.admission_agreement` | Admission Agreement | legal | “admission agreement”, “undertaking by the student” |  |
| `education.student_handbook` | Student Handbook | — | “student handbook”, “prospectus” |  |
| `education.university_regulations` | University Regulations | policy | “university regulations”, “ordinance” |  |
| `education.examination_rules` | Examination Rules | — | “examination rules”, “rules for examination”, “unfair means” |  |
| `education.scholarship_guidelines` | Scholarship Guidelines | government | “scholarship” |  |
| `education.fee_policy` | Fee Policy | — | “fee policy”, “fee structure”, “tuition fee” |  |
| `education.hostel_rules` | Hostel Rules | — | “hostel rules”, “hostel” |  |
| `education.academic_regulations` | Academic Regulations | — | “academic regulations”, “credit system” |  |
| `education.student_disciplinary_notice` | Student Disciplinary Notice | — | “disciplinary committee”, “student conduct” |  |

### Policy / Regulatory (`policy`)

Policies, rules, regulations, standards and guidelines that set requirements.

**Typical structure:** Title → Objective → Scope → Definitions → Eligibility → Procedure → Responsibilities → Implementation → Timeline → Exceptions → Compliance → Monitoring

**Expected fields:** `objective`, `scope`, `effective_date`, `responsibilities`, `compliance`

| Id | Name | Also in | Title cues | Often scanned |
|---|---|---|---|---|
| `policy.government_policy` | Government Policy | government | “national policy”, “state policy”, “policy document” |  |
| `policy.draft_policy` | Draft Policy | government | “draft policy”, “draft” |  |
| `policy.regulatory_framework` | Regulatory Framework | — | “regulatory framework” |  |
| `policy.guidelines` | Guidelines | — | “guidelines” |  |
| `policy.standards` | Standards | — | “standard”, “specification” |  |
| `policy.rules` | Rules | government | “rules,”, “these rules may be called” |  |
| `policy.regulations` | Regulations | government | “regulations,”, “these regulations may be called” |  |
| `policy.act` | Act | government | “act,”, “be it enacted” |  |
| `policy.framework_document` | Framework Document | — | “framework” |  |
| `policy.implementation_guidelines` | Implementation Guidelines | government | “implementation guidelines”, “standard operating procedure”, “sop” |  |
| `policy.scheme_guidelines` | Scheme Guidelines | government | “scheme”, “yojana”, “operational guidelines” |  |

**Rules structure:** Title and commencement → Definitions → Chapters → Rules and sub-rules → Penalties → Repeal and savings → Schedules

### Other Official Documents (`other`)

Official documents that do not fit another category, or cannot be classified with confidence.

**Typical structure:** Title → Issuer → Date → Body → Signature

**Expected fields:** `issuer`, `date`

| Id | Name | Also in | Title cues | Often scanned |
|---|---|---|---|---|
| `other.certificate` | Certificate | government, education | “certificate”, “this is to certify” | yes |
| `other.licence_permit` | Licence / Permit | government | “licence”, “license”, “permit” |  |
| `other.will` | Will | legal, property | “last will”, “testament”, “testator” | yes |
| `other.first_information_report` | First Information Report | court, government | “first information report”, “fir” | yes |
| `other.legal_notice` | Legal Notice | legal, court | “legal notice”, “under instructions from my client” |  |
| `other.letter` | Letter | — | “dear sir”, “dear madam”, “yours faithfully” |  |
| `other.unknown` | Unknown | — | — |  |

## 6. Judgments: keep the parts apart

For `court.judgment` the sections have different legal weight and must never be merged: **Facts → Arguments → Issues → Evidence → Applicable law → Court's reasoning → Findings → Final order.** An argument is what a party *claimed*; a finding is what the court *decided*. Section `role` values (`facts`, `arguments`, `issues`, `evidence`, `law`, `reasoning`, `findings`, `final_order`) record this (see [Document_Normalization.md](Document_Normalization.md)).

## 7. Extending the taxonomy

1. Add the entry to `data/taxonomy/document_types.json` (id, name, category, secondary categories, title cues, `commonly_scanned`, optional `typical_structure`).
2. Add the row to this file (the test `test_markdown_docs_list_every_type_and_concept` fails if you forget).
3. Add at least one evaluation document for it (see [Training_Dataset_Schema.md](Training_Dataset_Schema.md)).
4. Bump the taxonomy `version` (minor for additions, major for removals).

## 8. Relation to the current code

Today `backend/app/services/concepts.py::detect_document_type` returns a display label (e.g. "Employment agreement") from keyword rules. Phase 5 (classification) replaces it with a classifier that returns these ids with a confidence, as designed in [Document_Classification.md](Document_Classification.md).
