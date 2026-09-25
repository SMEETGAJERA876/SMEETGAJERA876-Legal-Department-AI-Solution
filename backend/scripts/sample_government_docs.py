"""Fictional government-style documents for tests, evaluation and demos.

Each page is a list of (style, text) lines: "title", "heading" or "body".
All names, numbers and addresses are invented.
"""

from pathlib import Path

from fpdf import FPDF

Line = tuple[str, str]

# A rental agreement with deliberate mistakes, used to test the document check and repair.
RENTAL_WITH_MISTAKES: list[list[Line]] = [
    [
        ("title", "RENTAL AGREEMENT"),
        (
            "body",
            'This Rental Agreement is made on 1 May 2026 between Ravi Kumar (the "Landlord") '
            'and Meera Nair (the "Tenant").',
        ),
        ("heading", "1. Premises"),
        ("body", "1.1 The Landlord agrees to let the the flat at ______ to the Tenant."),
    ],
    [
        ("heading", "2. Rent and Deposit"),
        (
            "body",
            "2.1 The Tenant shall pay a monthly rent of Rs. 18,000 on or before the 5th day "
            "of each month.",
        ),
        ("body", "2.2 A security deposit of Rs. 36,000 shall be paid before the tenent moves in."),
        ("heading", "3. Term"),
        ("body", "3.1 The term of this agrement shall be eleven (11) months."),
    ],
    [
        ("heading", "4. Termination"),
        (
            "body",
            "4.1 Either party may end this Agreement by giving ninety (60) days written notice.",
        ),
        ("body", "4.2 The deposit shall be refunded within thirty (30) days, subject to Clause 9."),
        ("heading", "6. Maintenance"),
        (
            "body",
            "6.1 The Tenant shall be responsible for minor repairs and the Landlord for "
            "structural repairs (including the roof.",
        ),
    ],
    [
        ("heading", "7. Signatures"),
        ("body", "7.1 Signed on ________ by both parties."),
    ],
]

PUBLIC_NOTICE: list[list[Line]] = [
    [
        ("title", "GOVERNMENT OF EXAMPLE STATE"),
        ("title", "DEPARTMENT OF REVENUE"),
        ("body", "No. REV/2026/114                                        Dated: 10 March 2026"),
        ("title", "PUBLIC NOTICE"),
        ("title", "Property Tax Relief Scheme, 2026"),
        (
            "body",
            "Notice is hereby given that the State Government has introduced the Property "
            "Tax Relief Scheme, 2026 for owners of residential property in Example State.",
        ),
        ("heading", "1. Purpose of the Scheme"),
        (
            "body",
            "1.1 The Scheme allows eligible owners to clear pending property tax without "
            "interest if they apply in time.",
        ),
    ],
    [
        ("heading", "2. Eligibility"),
        ("body", "2.1 An owner is eligible if the property is used only for residence."),
        ("body", "2.2 Owners with a pending court case about the same property are not eligible."),
        ("heading", "3. Documents Required"),
        ("body", "3.1 The following documents must be attached to the application:"),
        ("body", "(a) a self-attested copy of the property tax receipt;"),
        ("body", "(b) proof of ownership, such as a sale deed;"),
        ("body", "(c) a copy of an identity document of the owner."),
    ],
    [
        ("heading", "4. Last Date and Time Limits"),
        ("body", "4.1 Applications must be submitted on or before 30 April 2026."),
        (
            "body",
            "4.2 Objections to the draft list of beneficiaries may be filed within fifteen "
            "(15) days from the date of publication of the list.",
        ),
        (
            "body",
            "4.3 Before any site inspection, the owner shall be given seven (7) days' notice "
            "in writing.",
        ),
    ],
    [
        ("heading", "5. Fees and Penalties"),
        ("body", "5.1 An application fee of Rs. 250 shall be paid online."),
        (
            "body",
            "5.2 If the pending tax is not paid within thirty (30) days of approval, a "
            "penalty of Rs. 5,000 shall be charged and the relief shall be cancelled.",
        ),
        ("title", "IMPORTANT NOTE:"),
        ("body", "Note: Incomplete applications shall be rejected without further intimation."),
    ],
    [
        ("heading", "6. Appeal"),
        (
            "body",
            "6.1 Any person aggrieved by a decision under this Scheme may file an appeal "
            "before the Deputy Commissioner (Revenue) within thirty (30) days of the "
            "decision.",
        ),
        ("heading", "7. Contact"),
        (
            "body",
            "7.1 For help, contact the Revenue Helpline at 1800-000-0000 or write to "
            "help@revenue.example.gov.",
        ),
        ("body", "By order, Secretary to Government, Department of Revenue."),
    ],
]

TENANCY_RULES: list[list[Line]] = [
    [
        ("title", "THE EXAMPLE STATE TENANCY RULES, 2026"),
        ("title", "CHAPTER I"),
        ("title", "PRELIMINARY"),
        ("heading", "Rule 1. Short title and commencement"),
        ("body", "(1) These rules may be called the Example State Tenancy Rules, 2026."),
        ("body", "(2) They shall come into force on 1 June 2026."),
        ("heading", "Rule 2. Definitions"),
        ("body", '(a) "landlord" means the person who receives rent for the premises;'),
        ("body", '(b) "tenant" means the person who pays rent for the premises.'),
    ],
    [
        ("title", "CHAPTER II"),
        ("title", "NOTICE AND TERMINATION"),
        ("heading", "Rule 5. Notice to vacate"),
        (
            "body",
            "(1) A landlord shall give the tenant not less than three (3) months' notice in "
            "writing before asking the tenant to vacate the premises.",
        ),
        (
            "body",
            "(2) A tenant may vacate the premises by giving one (1) month's notice to the "
            "landlord.",
        ),
    ],
    [
        ("title", "CHAPTER III"),
        ("title", "RENT AND DEPOSIT"),
        ("heading", "Rule 6. Security deposit"),
        ("body", "(1) The security deposit shall not exceed two months' rent."),
        (
            "body",
            "(2) The landlord shall refund the security deposit within one (1) month of "
            "the tenant vacating the premises, after deducting any unpaid rent.",
        ),
        ("heading", "Rule 7. Revision of rent"),
        ("body", "(1) Rent may be revised only once in a period of twelve (12) months."),
    ],
    [
        ("title", "CHAPTER IV"),
        ("title", "DISPUTES AND PENALTIES"),
        ("heading", "Rule 9. Rent Authority"),
        (
            "body",
            "(1) Any dispute between a landlord and a tenant may be referred to the Rent "
            "Authority of the district.",
        ),
        (
            "body",
            "(2) An appeal against an order of the Rent Authority shall lie to the Rent "
            "Tribunal within thirty (30) days of the order.",
        ),
        ("heading", "Rule 10. Penalty"),
        (
            "body",
            "(1) A landlord who cuts off water or electricity to force a tenant to leave "
            "shall be liable to a fine of up to Rs. 10,000.",
        ),
    ],
]


def build_document(path: Path, pages: list[list[Line]]) -> None:
    pdf = FPDF(format="A4")
    pdf.set_margins(22, 22, 22)
    pdf.set_auto_page_break(auto=False)
    styles = {"title": ("B", 13, 8, "C"), "heading": ("B", 12, 8, "L"), "body": ("", 11, 6, "L")}
    for index, lines in enumerate(pages, start=1):
        pdf.add_page()
        for style, text in lines:
            weight, size, height, align = styles[style]
            pdf.set_font("Helvetica", weight, size)
            pdf.multi_cell(0, height, text, align=align, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2 if style == "body" else 1)
        pdf.set_y(-18)
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, f"Page {index} of {len(pages)}", align="C")
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))
