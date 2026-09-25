# Legal Concepts

Version **1.1.0** · Source of truth: [`data/taxonomy/legal_concepts.json`](../data/taxonomy/legal_concepts.json) · aliases: [`concept_aliases.json`](../data/taxonomy/concept_aliases.json) · 92 concepts

A **concept** is a kind of information people look for in a document (a notice period, a deadline, a penalty, a court's finding). Concepts drive fact extraction, search boosting, the overview, the summary PDF and the questions for a legal professional.

## 1. Concept fields

| Field | Meaning |
|---|---|
| `id` | Stable id `<group>.<name>`, e.g. `contract.notice_period`. Never renamed. |
| `name` | Plain-language name shown to users. |
| `group` | `contract`, `government`, `court`, `employment`, `financial`, `property`, `common`. |
| `description` | What it means, in plain words. |
| `aliases` | Phrases that signal the concept in documents **and** in user questions. |
| `value_type` | Expected shape of the value (see below). |
| `example` | A typical value. |
| `source_locations` | Sections where it is usually found. |
| `applies_to` | Document categories where it is relevant. |
| `engine_key` | Key used by the running extraction engine, when implemented. |

Schema: [`data/schemas/legal_concept.schema.json`](../data/schemas/legal_concept.schema.json).

## 2. Value types

| Value type | Normalized as (legal_fact.normalized_value) | Example |
|---|---|---|
| `duration` | `{kind: duration, number, unit, qualifier?}` | 90 days → `{number: 90, unit: days}` |
| `date` | `{kind: date, date (ISO), qualifier?}` | on or before 30 April 2026 → `{date: 2026-04-30, qualifier: on_or_before}` |
| `date_or_duration` | either of the above | within 15 days / by 30 April 2026 |
| `money` | `{kind: money, amount, currency (ISO 4217), period?}` | INR 1,20,000 per month → `{amount: 120000, currency: INR, period: per_month}` |
| `percentage` | `{kind: percentage, value, period?}` | 10.5% p.a. |
| `party`, `party_list`, `person`, `organization` | entity ids + text | Northwind Analytics Pvt. Ltd. (employer) |
| `identifier`, `reference` | text | W.P. No. 1234 of 2026; Industrial Disputes Act, 1947 |
| `address`, `area`, `contact`, `list`, `text`, `boolean` | `{kind: text}` or text only | — |

Indian number formats (1,20,000; lakh; crore) must be normalized correctly: `INR 1,20,000` → `120000`.

## 3. Concepts

### Contract

| Id | Name | Value type | Description | Aliases | Example | Usually in |
|---|---|---|---|---|---|---|
| `contract.parties` | Parties | party_list | The people or organisations bound by the document and their roles. | parties, between, by and between, hereinafter referred to as | Northwind Analytics Pvt. Ltd. (Employer) and Priya Sharma (Employee) | Title, Parties, Recitals |
| `contract.definitions` | Definitions | text | Terms given a specific meaning in the document. | definitions, means, shall mean, interpretation | "Effective Date" means February 1, 2026 | Definitions |
| `contract.scope` | Scope | text | What the document or service covers. | scope, scope of work, services | Data analysis services for the Company | Scope, Statement of work |
| `contract.term` | Term | duration | How long the agreement lasts. | term, duration, period of, shall remain in force, validity | 2 years | Term, Commencement |
| `contract.renewal` | Renewal | text | Whether and how the agreement continues after its term. | renewal, renew, extension, automatically renew | Renews automatically for 1 year unless 60 days' notice is given | Term, Renewal |
| `contract.termination` | Termination | text | How and when the agreement can be ended. | termination, terminate, end this agreement, cancel the agreement, termination of employment | Either party may terminate with 90 days' written notice | Termination |
| `contract.notice_period` | Notice Period | duration | Time that must be given before ending the agreement or taking an action. | notice period, termination notice, notice requirement, prior notice, written notice | 90 days | Termination, Notice, Probation |
| `contract.payment` | Payment | money | Money one party must pay the other, and when. | payment, pay, consideration, salary, fee | INR 1,20,000 per month | Payment, Compensation, Fees |
| `contract.fee` | Fee | money | A charge for a service, application or action. | fee, fees, charges, application fee | Rs. 250 application fee | Fees, Payment |
| `contract.penalty` | Penalty | money | Money or consequence imposed when something is not done. | penalty, fine, liquidated damages, forfeit, late fee | Rs. 5,000 penalty | Penalty, Default, Termination |
| `contract.obligation` | Obligation | text | Something a party must do. | shall, must, is required to, responsible for, obligations | The Employee shall maintain accurate records | Obligations, Duties, Responsibilities |
| `contract.right` | Right | text | Something a party is entitled to. | right to, entitled to, may request, may apply | The Employee is entitled to 24 days of paid leave | Rights, Benefits |
| `contract.restriction` | Restriction | text | Something a party must not do. | shall not, must not, prohibited, restricted | The tenant shall not sublet the premises | Restrictions, Covenants |
| `contract.confidentiality` | Confidentiality | text | Duty to keep information secret. | confidentiality, confidential information, non-disclosure, trade secret | Keep information confidential for 3 years after exit | Confidentiality |
| `contract.intellectual_property` | Intellectual Property | text | Who owns work, inventions and content. | intellectual property, ip, copyright, work product, ownership | All work product belongs to the Company | Intellectual property |
| `contract.indemnification` | Indemnification | text | Promise to cover another party's losses. | indemnify, indemnification, indemnity, hold harmless | The Vendor shall indemnify the Customer against third-party claims | Indemnity |
| `contract.liability` | Liability | text | Limits and extent of responsibility for losses. | liability, liable, limitation of liability, damages | No liability for indirect damages | Liability |
| `contract.warranty` | Warranty | text | Promises about quality or condition. | warranty, warrants, guarantee | Software will perform materially as described for 90 days | Warranty |
| `contract.representation` | Representation | text | Statements of fact a party confirms are true. | represents, representations, declares | The Seller represents that the property is free of encumbrances | Representations and warranties |
| `contract.dispute_resolution` | Dispute Resolution | text | How disagreements are resolved. | dispute, dispute resolution, mediation, conciliation | Mediation, then arbitration in Bengaluru | Dispute resolution |
| `contract.arbitration` | Arbitration | text | Resolution of disputes by an arbitrator instead of a court. | arbitration, arbitrator, arbitral tribunal | Arbitration in Bengaluru under the Arbitration and Conciliation Act | Dispute resolution |
| `contract.governing_law` | Governing Law | text | Which country's or state's law applies. | governing law, governed by the laws of, applicable law | Laws of India | Governing law |
| `contract.jurisdiction` | Jurisdiction | text | Which courts can hear disputes. | jurisdiction, courts of, exclusive jurisdiction | Courts at Bengaluru | Jurisdiction |
| `contract.force_majeure` | Force Majeure | text | Events outside a party's control that excuse performance. | force majeure, act of god, beyond reasonable control | Floods, war, epidemics | Force majeure |
| `contract.amendment` | Amendment | text | How the document can be changed. | amendment, amended, modification, variation | Changes only in writing signed by both parties | Amendments |
| `contract.assignment` | Assignment | text | Whether rights can be transferred to someone else. | assignment, assign, transfer of rights | No assignment without prior written consent | Assignment |
| `contract.default` | Default | text | What counts as failing to meet obligations. | default, event of default, fails to pay | Non-payment for 60 days is an event of default | Default |
| `contract.breach` | Breach | text | Violation of the agreement and its consequences. | breach, material breach, violation | Material breach allows immediate termination | Termination, Default |
| `contract.cure_period` | Cure Period | duration | Time allowed to fix a breach before consequences apply. | cure period, remedy the breach, rectify within | 30 days | Termination, Default |

### Government

| Id | Name | Value type | Description | Aliases | Example | Usually in |
|---|---|---|---|---|---|---|
| `government.authority` | Authority | organization | The body that issued the document or is responsible for it. | authority, department, ministry, officer, commissioner | Department of Revenue, Government of Example State | Letterhead, Signature / Authority |
| `government.reference_number` | Reference Number | identifier | The official number of the document. | no., reference, ref., file no, order no | REV/2026/114 | Letterhead |
| `government.effective_date` | Effective Date | date | When the document or rule takes effect. | effective date, with effect from, w.e.f., come into force | 2026-06-01 | Effective date, Commencement |
| `government.eligibility` | Eligibility | text | Who qualifies or can apply. | eligibility, eligible, who can apply, criteria, qualification | Owners of residential property | Eligibility |
| `government.deadline` | Deadline | date_or_duration | The last date or time allowed for an action. | deadline, last date, on or before, within, not later than | on or before 30 April 2026 | Important dates, Procedure |
| `government.application_process` | Application Process | text | Steps to apply. | how to apply, application process, procedure for applying, submit online | Apply online with documents | Procedure |
| `government.required_documents` | Required Documents | list | Documents that must be attached or produced. | documents required, attach, enclose, copy of, proof of | Tax receipt; proof of ownership; ID | Documents required |
| `government.exemption` | Exemption | text | Who or what is exempt from a rule. | exemption, exempted, shall not apply to | Senior citizens are exempt from the fee | Exemptions |
| `government.procedure` | Procedure | text | The process to be followed. | procedure, process, steps, manner | Objections to be filed in Form B | Procedure |
| `government.responsibility` | Responsibility | text | Duties assigned to an office or person. | responsible, responsibility, shall ensure, duty of | District Collector shall monitor implementation | Responsibilities |
| `government.compliance` | Compliance | text | Requirements to comply and how compliance is checked. | compliance, comply, adhere | Compliance report within 30 days | Compliance |
| `government.contact` | Contact | contact | Where to get help or send communications. | contact, helpline, email, phone, address for correspondence | Helpline 1800-000-0000 | Contact |

### Court

| Id | Name | Value type | Description | Aliases | Example | Usually in |
|---|---|---|---|---|---|---|
| `court.case_number` | Case Number | identifier | The court's case reference. | case no, w.p., civil appeal no, criminal appeal, o.s. no | W.P. No. 1234 of 2026 | Title |
| `court.court` | Court | organization | The court or tribunal. | in the court of, high court, supreme court, tribunal, district court | High Court of Example State | Title |
| `court.judge` | Judge | person | Judge(s) or bench deciding the case. | coram, hon'ble, justice, bench, before | Hon'ble Justice A. Rao | Coram |
| `court.issue` | Issue | text | Questions the court must decide. | issues, points for determination, question for consideration | Whether the termination was lawful | Issues |
| `court.fact` | Fact | text | Facts of the case as stated by the court or parties. | facts, brief facts, background | The petitioner was employed from 2019 | Facts |
| `court.argument` | Argument | text | Submissions made by a party (not the court's view). | argued, contended, submitted, learned counsel | Counsel for the petitioner contended... | Arguments |
| `court.evidence` | Evidence | text | Evidence relied on. | exhibit, evidence, witness, deposition | Exhibit P-3 (appointment letter) | Evidence |
| `court.law` | Law | text | Legal provisions discussed. | section, article, under the act, provision | Section 25F of the Industrial Disputes Act | Applicable law |
| `court.statute` | Statute | reference | Acts and rules cited. | act, rules, code | Industrial Disputes Act, 1947 | Applicable law |
| `court.precedent` | Precedent | reference | Earlier judgments relied on. | relied on, held in, v., vs. | ABC v. State (2019) | Law / Precedents |
| `court.finding` | Finding | text | What the court concluded on an issue. | we find, it is held, held that, findings | The termination did not follow the notice requirement | Findings |
| `court.direction` | Direction | text | Instructions the court gives to parties or authorities. | directed to, shall, directions | Respondent directed to reinstate within 4 weeks | Order / Directions |
| `court.final_order` | Final Order | text | The operative decision. | petition is allowed, dismissed, disposed of, ordered accordingly | Writ petition allowed; no costs | Final order |

### Employment

| Id | Name | Value type | Description | Aliases | Example | Usually in |
|---|---|---|---|---|---|---|
| `employment.employer` | Employer | organization | The organisation that employs. | employer, the company | Northwind Analytics Pvt. Ltd. | Parties |
| `employment.employee` | Employee | person | The person employed. | employee, the candidate | Priya Sharma | Parties |
| `employment.job_title` | Job Title | text | Position or designation. | designation, position, appointed as, role | Senior Data Analyst | Appointment |
| `employment.joining_date` | Joining Date | date | Date employment starts. | joining date, date of joining, commencement | 2026-02-01 | Commencement |
| `employment.salary` | Salary | money | Fixed pay. | salary, ctc, gross salary, basic pay, wages | INR 1,20,000 per month | Compensation |
| `employment.compensation` | Compensation | money | All pay and payable benefits. | compensation, remuneration, bonus, incentive | Annual bonus up to INR 2,00,000 | Compensation |
| `employment.probation` | Probation | duration | Initial trial period of employment. | probation, probationary period | 6 months | Probation |
| `employment.working_hours` | Working Hours | text | Hours of work. | working hours, hours per week, shift | 40 hours per week | Working hours |
| `employment.leave` | Leave | text | Leave entitlement. | leave, paid leave, sick leave, casual leave | 24 days paid leave per year | Leave |
| `employment.benefits` | Benefits | text | Non-salary benefits. | benefits, insurance, provident fund, gratuity, allowance | Group health insurance | Benefits |
| `employment.non_compete` | Non-Compete | text | Restriction on working for competitors. | non-compete, shall not engage, competing business | No competing work for 12 months | Restrictive covenants |
| `employment.non_solicitation` | Non-Solicitation | text | Restriction on approaching clients or staff. | non-solicitation, shall not solicit | No soliciting clients for 12 months | Restrictive covenants |
| `employment.work_location` | Work Location | address | Where the work is done. | place of work, location, posted at | Bengaluru office | Appointment |
| `employment.transfer` | Transfer | text | Whether the employee can be moved. | transfer, relocate, posted to any | May be transferred to any office in India | Transfer |

### Financial

| Id | Name | Value type | Description | Aliases | Example | Usually in |
|---|---|---|---|---|---|---|
| `financial.amount` | Amount | money | A sum of money. | amount, sum of, rs., inr, ₹ | Rs. 5,00,000 | Payment, Schedule |
| `financial.currency` | Currency | text | Currency of amounts. | inr, rupees, usd, currency | INR | Payment |
| `financial.interest_rate` | Interest Rate | percentage | Interest charged or earned. | interest rate, rate of interest, per annum, % p.a. | 10.5% per annum | Interest |
| `financial.payment_date` | Payment Date | date | When a payment is made. | payment date, paid on, payable on | Last working day of each month | Payment |
| `financial.due_date` | Due Date | date | When a payment is due. | due date, due on, payable by | 2026-04-30 | Payment schedule |
| `financial.late_fee` | Late Fee | money | Charge for paying late. | late fee, late payment charge, delayed payment | Rs. 100 per month | Late payment |
| `financial.collateral` | Collateral | text | Assets pledged to secure a loan. | collateral, pledge, hypothecation | Hypothecation of the vehicle | Security |
| `financial.security` | Security | text | Security deposit or security interest. | security, security deposit, guarantee | Two months' rent as security deposit | Security |

### Property

| Id | Name | Value type | Description | Aliases | Example | Usually in |
|---|---|---|---|---|---|---|
| `property.property` | Property | text | Description of the property. | property, premises, flat, plot, schedule property | Flat No. 12, Example Towers | Property description, Schedule |
| `property.owner` | Owner | party | Owner of the property. | owner, lessor, landlord, licensor | Ravi Kumar | Parties |
| `property.buyer` | Buyer | party | Purchaser. | buyer, purchaser, vendee | A. Singh | Parties |
| `property.seller` | Seller | party | Seller / vendor. | seller, vendor | B. Mehta | Parties |
| `property.tenant` | Tenant | party | Person renting the property. | tenant, lessee, licensee | Meera Nair | Parties |
| `property.landlord` | Landlord | party | Person letting the property. | landlord, lessor, licensor | Ravi Kumar | Parties |
| `property.address` | Address | address | Address of the property. | address, situated at, located at | 12 Lake Road, Example City | Property description |
| `property.area` | Area | area | Size of the property. | area, sq. ft, square feet, sq. m, acres | 1,200 sq. ft | Property description |
| `property.rent` | Rent | money | Periodic rent. | rent, monthly rent, licence fee | Rs. 18,000 per month | Rent |
| `property.deposit` | Deposit | money | Security deposit. | deposit, security deposit, advance | Rs. 36,000 | Deposit |
| `property.sale_price` | Sale Price | money | Price / consideration for a sale. | sale price, consideration, total price | Rs. 75,00,000 | Consideration |
| `property.registration` | Registration | text | Registration details and obligations. | registration, registered, sub-registrar, stamp duty | Registered at Sub-Registrar Office, Example City | Registration |
| `property.possession` | Possession | text | When and how possession is handed over. | possession, handover, vacant possession | Possession on payment of full consideration | Possession |

### Common (all documents)

| Id | Name | Value type | Description | Aliases | Example | Usually in |
|---|---|---|---|---|---|---|
| `common.important_date` | Important Date | date | Any date that matters in the document (issue, effective, signature, event). | date, dated, on, with effect from | 10 March 2026 | Letterhead, Important dates, Signatures |
| `common.important_note` | Important Note | text | Notes, warnings and formal notices written in the document. | note, n.b., please note, important, it is hereby notified | Incomplete applications shall be rejected | Notes, Footnotes |
| `common.appeal` | Appeal | text | How to appeal, object or complain, and to whom. | appeal, appellate authority, grievance, complaint, objection | Appeal to the Deputy Commissioner within 30 days | Appeal, Grievance redressal |

## 4. Example entry

```text
ID:           contract.notice_period
Name:         Notice Period
Group:        contract (applies to legal, employment, property, government)
Description:  Time that must be given before ending the agreement or taking an action.
Aliases:      notice period, termination notice, notice requirement, prior notice, written notice
Value type:   duration
Example:      90 days
Usually in:   Termination, Notice, Probation
```

## 5. Mapping to the current engine

The running engine (`backend/app/services/concepts.py`) uses short keys. Every engine key maps to exactly one taxonomy concept (enforced by `test_every_engine_concept_maps_to_exactly_one_taxonomy_concept`):

| Engine key | Taxonomy concept |
|---|---|
| `parties` | `contract.parties` |
| `duration` | `contract.term` |
| `renewal` | `contract.renewal` |
| `termination` | `contract.termination` |
| `notice_period` | `contract.notice_period` |
| `payment` | `contract.payment` |
| `penalty` | `contract.penalty` |
| `obligations` | `contract.obligation` |
| `rights` | `contract.right` |
| `confidentiality` | `contract.confidentiality` |
| `intellectual_property` | `contract.intellectual_property` |
| `indemnification` | `contract.indemnification` |
| `liability` | `contract.liability` |
| `dispute_resolution` | `contract.dispute_resolution` |
| `arbitration` | `contract.arbitration` |
| `governing_law` | `contract.governing_law` |
| `jurisdiction` | `contract.jurisdiction` |
| `force_majeure` | `contract.force_majeure` |
| `assignment` | `contract.assignment` |
| `cure_period` | `contract.cure_period` |
| `authority` | `government.authority` |
| `reference_number` | `government.reference_number` |
| `effective_date` | `government.effective_date` |
| `eligibility` | `government.eligibility` |
| `time_limits` | `government.deadline` |
| `documents_required` | `government.required_documents` |
| `contact` | `government.contact` |
| `case_number` | `court.case_number` |
| `court_name` | `court.court` |
| `job_title` | `employment.job_title` |
| `salary` | `employment.salary` |
| `probation` | `employment.probation` |
| `working_hours` | `employment.working_hours` |
| `leave` | `employment.leave` |
| `non_compete` | `employment.non_compete` |
| `non_solicitation` | `employment.non_solicitation` |
| `interest_rate` | `financial.interest_rate` |
| `late_fee` | `financial.late_fee` |
| `area` | `property.area` |
| `rent` | `property.rent` |
| `deposit` | `property.deposit` |
| `important_dates` | `common.important_date` |
| `notes` | `common.important_note` |
| `appeal` | `common.appeal` |

Concepts without an engine key are defined but not yet extracted (mostly court-structure concepts such as `court.argument` / `court.finding`, planned with advanced court documents in Phase 12).

Extraction quality is measured on `backend/tests/extraction_cases.py` (31 labelled sentences including traps such as a probation sentence that contains a notice period, or "3rd floor" that is not an area): precision and recall must both stay ≥ 95%. The sentences were written by the developers, so this measures coverage, not real-world accuracy.

## 6. Rules

- A fact is stored only with its evidence: page, clause, exact source text and character offsets ([`legal_fact.schema.json`](../data/schemas/legal_fact.schema.json)).
- Never infer a value that is not written (no "usual" notice period, no assumed currency).
- When words and digits disagree ("ninety (60) days"), store the fact with low confidence and raise a review item; never pick one silently.
- Court concepts `argument` and `finding` must never be merged: a party's claim is not the court's decision.
