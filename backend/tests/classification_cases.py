"""Classification evaluation cases: short, realistic first pages of many document types.

All text is invented for testing. `expected=None` means the classifier must NOT commit to a
type (it should answer unknown / needs review).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ClassificationCase:
    name: str
    text: str
    expected: str | None
    headings: tuple[str, ...] = ()
    expected_category: str | None = None  # checked when set (e.g. for "no type, but legal")


CASES: list[ClassificationCase] = [
    ClassificationCase(
        "judgment",
        "IN THE HIGH COURT OF EXAMPLE STATE\nW.P. No. 1234 of 2026\nCORAM: HON'BLE JUSTICE A. RAO\n"
        "R. Menon ... Petitioner versus State of Example State ... Respondents\nJUDGMENT\n"
        "The petitioner challenges the termination of his services.",
        "court.judgment",
        ("Facts", "Issues", "Findings", "Order"),
    ),
    ClassificationCase(
        "affidavit",
        "AFFIDAVIT\nI, Suresh Patel, aged 45 years, residing at Example City, do hereby solemnly affirm "
        "and state as under: 1. That I am the deponent herein and know the facts of the case.",
        "court.affidavit",
    ),
    ClassificationCase(
        "bail order",
        "IN THE COURT OF THE SESSIONS JUDGE, EXAMPLE DISTRICT\nBail Application No. 45 of 2026\n"
        "State ... Complainant versus K. Das ... Accused\nORDER\nThe accused is released on bail on "
        "furnishing a personal bond of Rs. 50,000.",
        "court.bail_order",
    ),
    ClassificationCase(
        "appointment letter",
        "Northwind Analytics Private Limited\nLETTER OF APPOINTMENT\nDear Ms. Sharma,\nWe are pleased to "
        "appoint you as Senior Data Analyst with effect from 1 February 2026 on the following terms.",
        "employment.appointment_letter",
    ),
    ClassificationCase(
        "offer letter",
        "OFFER LETTER\nDear Rahul,\nWe are pleased to offer you the position of Software Engineer at "
        "Example Tech Pvt. Ltd. Your annual CTC will be INR 12,00,000.",
        "employment.offer_letter",
    ),
    ClassificationCase(
        "show cause notice",
        "SHOW CAUSE NOTICE\nRef: HR/SCN/2026/07\nTo: Mr. A. Kumar, Employee Code 4431\nYou are hereby "
        "directed to show cause within 7 days why disciplinary action should not be taken against you.",
        "employment.show_cause_notice",
    ),
    ClassificationCase(
        "employment agreement",
        "EMPLOYMENT AGREEMENT\nThis Agreement is made between Example Tech Pvt. Ltd. (the Employer) and "
        "Priya Rao (the Employee).",
        "employment.employment_agreement",
        ("Probation", "Salary", "Termination", "Leave"),
    ),
    ClassificationCase(
        "government notification",
        "GOVERNMENT OF EXAMPLE STATE\nDEPARTMENT OF LABOUR\nNOTIFICATION\nNo. LAB/2026/12 Dated 3 May 2026\n"
        "In exercise of the powers conferred by the Act, it is hereby notified that the minimum wages "
        "shall be revised with effect from 1 June 2026.",
        "government.notification",
    ),
    ClassificationCase(
        "circular",
        "GOVERNMENT OF EXAMPLE STATE\nDEPARTMENT OF EDUCATION\nCIRCULAR\nNo. EDU/C/2026/04\n"
        "All district officers are informed that the summer vacation for schools will begin on 1 May 2026.",
        "government.circular",
    ),
    ClassificationCase(
        "office memorandum",
        "No. 12/4/2026-Estt.\nGovernment of India\nMinistry of Personnel\nOFFICE MEMORANDUM\n"
        "Subject: Revision of daily allowance for official tours.",
        "government.office_memorandum",
    ),
    ClassificationCase(
        "gazette notification",
        "THE GAZETTE OF EXAMPLE STATE\nEXTRAORDINARY\nPUBLISHED BY AUTHORITY\nNotification No. 88\n"
        "The following amendment is made to the Example Municipal Rules.",
        "government.gazette_notification",
    ),
    ClassificationCase(
        "recruitment",
        "EXAMPLE STATE PUBLIC SERVICE COMMISSION\nRECRUITMENT NOTIFICATION No. 5/2026\nOnline applications "
        "are invited from eligible candidates for 120 vacancies of Assistant Engineer.",
        "government.recruitment_notification",
        ("Eligibility", "Important Dates", "How to Apply", "Fee"),
    ),
    ClassificationCase(
        "tender",
        "EXAMPLE MUNICIPAL CORPORATION\nE-TENDER NOTICE\nTender No. EMC/ROADS/2026/19\nSealed bids are "
        "invited from registered contractors for resurfacing of roads in Ward 12.",
        "government.tender_notice",
    ),
    ClassificationCase(
        "public notice",
        "GOVERNMENT OF EXAMPLE STATE\nDEPARTMENT OF REVENUE\nPUBLIC NOTICE\nNotice is hereby given that "
        "the Property Tax Relief Scheme, 2026 has been introduced for owners of residential property.",
        "public_notice.public_notice",
        ("Eligibility", "Documents Required", "Last Date"),
    ),
    ClassificationCase(
        "rules",
        "THE EXAMPLE STATE TENANCY RULES, 2026\nCHAPTER I\nPRELIMINARY\n1. Short title and commencement.\n"
        "(1) These rules may be called the Example State Tenancy Rules, 2026.",
        "policy.rules",
    ),
    ClassificationCase(
        "act",
        "THE EXAMPLE STATE SHOPS AND ESTABLISHMENTS ACT, 2026\nAN ACT to regulate conditions of work in "
        "shops. BE it enacted by the Legislature of Example State as follows.",
        "policy.act",
    ),
    ClassificationCase(
        "nda",
        "MUTUAL NON-DISCLOSURE AGREEMENT\nThis Non-Disclosure Agreement is entered into between Alpha "
        "Pvt. Ltd. and Beta LLP to protect Confidential Information shared for a proposed partnership.",
        "legal.nda",
        ("Definitions", "Confidential Information", "Permitted Use"),
    ),
    ClassificationCase(
        "lease",
        "LEASE DEED\nThis Lease Deed is made between Ravi Kumar (the Lessor) and Example Stores Pvt. Ltd. "
        "(the Lessee) for the premises at 12 Lake Road.",
        "property.lease_agreement",
        ("Premises", "Rent", "Security Deposit", "Maintenance"),
    ),
    ClassificationCase(
        "rental agreement",
        "RENTAL AGREEMENT\nThis Rental Agreement is made between Ravi Kumar (the Landlord) and Meera Nair "
        "(the Tenant).",
        "property.rental_agreement",
        ("Premises", "Rent", "Deposit"),
    ),
    ClassificationCase(
        "sale deed",
        "SALE DEED\nThis Sale Deed is executed on 4 April 2026 by B. Mehta (the Vendor) in favour of "
        "A. Singh (the Purchaser) for the schedule property.",
        "property.sale_deed",
    ),
    ClassificationCase(
        "power of attorney",
        "GENERAL POWER OF ATTORNEY\nKnow all men by these presents that I, S. Iyer, appoint my brother "
        "R. Iyer as my true and lawful attorney.",
        "property.power_of_attorney",
    ),
    ClassificationCase(
        "loan agreement",
        "LOAN AGREEMENT\nThis Loan Agreement is made between Example Bank Limited (the Lender) and "
        "K. Shah (the Borrower) for a term loan of Rs. 5,00,000.",
        "financial.loan_agreement",
    ),
    ClassificationCase(
        "insurance policy",
        "HEALTH INSURANCE POLICY\nPolicy Schedule\nPolicy No. HI-2026-99812\nSum Insured: Rs. 5,00,000\n"
        "Insured: M. Joseph",
        "financial.insurance_policy",
    ),
    ClassificationCase(
        "invoice",
        "TAX INVOICE\nInvoice No. INV-2026-0042\nBill To: Beta LLP\nGSTIN: 29ABCDE1234F1Z5\n"
        "Consulting services, March 2026: Rs. 1,18,000",
        "financial.invoice",
    ),
    ClassificationCase(
        "privacy policy",
        "PRIVACY POLICY\nThis Privacy Policy explains how Example App collects, uses and shares personal "
        "information when you use our services.",
        "legal.privacy_policy",
    ),
    ClassificationCase(
        "terms of service",
        "TERMS OF SERVICE\nBy using Example App you agree to these Terms of Service. Please read them "
        "carefully.",
        "legal.terms_of_service",
    ),
    ClassificationCase(
        "board resolution",
        "EXAMPLE TECH PRIVATE LIMITED\nCERTIFIED TRUE COPY OF THE BOARD RESOLUTION passed at the meeting "
        "of the Board of Directors held on 2 June 2026.\nRESOLVED THAT the Board approves the opening of "
        "a bank account.",
        "corporate.board_resolution",
    ),
    ClassificationCase(
        "scholarship guidelines",
        "EXAMPLE UNIVERSITY\nMERIT SCHOLARSHIP GUIDELINES 2026\nStudents with at least 85% marks may apply "
        "for the merit scholarship.",
        "education.scholarship_guidelines",
    ),
    # --- tricky: body mentions another type; titles that are too generic
    ClassificationCase(
        "judgment discussing an employment agreement",
        "IN THE HIGH COURT OF EXAMPLE STATE\nW.A. No. 77 of 2026\nCORAM: JUSTICE P. NAIR\n"
        "X Ltd ... Appellant versus Y ... Respondent\nJUDGMENT\nThe dispute concerns clause 12 of the "
        "employment agreement dated 1 January 2020 between the employer and the employee.",
        "court.judgment",
    ),
    ClassificationCase(
        "circular mentioning tenders",
        "GOVERNMENT OF EXAMPLE STATE\nFINANCE DEPARTMENT\nCIRCULAR No. FIN/2026/3\nAll departments "
        "shall publish every tender on the e-procurement portal from 1 July 2026.",
        "government.circular",
    ),
    ClassificationCase(
        "letter quoting a lease",
        "Dear Sir,\nWith reference to the lease agreement for the shop at 5 MG Road, we request you to "
        "repair the roof.\nYours faithfully,\nA. Khan",
        "other.letter",
    ),
    ClassificationCase(
        "bare AGREEMENT title",
        "AGREEMENT\nThis agreement is made on 2 March 2026 between A and B.",
        None,
        expected_category="legal",
    ),
    ClassificationCase(
        "no title, no structure",
        "the meeting went well and we discussed several points about the project timeline and next "
        "steps for the team",
        None,
    ),
    ClassificationCase(
        "only a generic word",
        "Please find the details below. Kindly go through the attached document and revert.",
        None,
    ),
]
