"""Generate sample PDFs used for tests and the demo.

Usage (from backend/):  uv run python scripts/make_sample_pdf.py
Writes ../samples/employment_agreement.pdf (the notice clause is on page 7, Clause 12).
"""

from pathlib import Path

from fpdf import FPDF

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "samples"

TITLE = "EMPLOYMENT AGREEMENT"
INTRO = (
    'This Employment Agreement (the "Agreement") is made on January 15, 2026 between '
    'Northwind Analytics Private Limited (the "Company") and Priya Sharma (the "Employee").'
)

# One inner list per page: (clause number, heading, body paragraphs)
PAGES: list[list[tuple[str, str, list[str]]]] = [
    [
        (
            "1",
            "Definitions",
            [
                'In this Agreement, "Confidential Information" means all non-public business, '
                "technical and financial information of the Company.",
                '"Effective Date" means February 1, 2026.',
            ],
        ),
        (
            "2",
            "Appointment",
            [
                "The Company appoints the Employee as Senior Data Analyst, and the Employee accepts "
                "the appointment on the terms of this Agreement.",
            ],
        ),
    ],
    [
        (
            "3",
            "Term of Employment",
            [
                "The term of this Agreement shall be two (2) years starting on the Effective Date, "
                "unless ended earlier in accordance with Clause 12.",
            ],
        ),
        (
            "4",
            "Probation",
            [
                "The first six (6) months of employment are a probation period. During probation, "
                "either party may end the employment by giving fourteen (14) days written notice.",
            ],
        ),
    ],
    [
        (
            "5",
            "Duties",
            [
                "The Employee shall perform the duties reasonably assigned by the Company and shall "
                "be responsible for maintaining accurate records of all work performed.",
                "The Employee agrees to follow all lawful Company policies.",
            ],
        ),
    ],
    [
        (
            "6",
            "Salary and Payment",
            [
                "The Company shall pay the Employee a gross salary of INR 1,20,000 per month, paid "
                "on the last working day of each month.",
                "The Employee is eligible for an annual performance bonus of up to INR 2,00,000 at "
                "the Company's discretion.",
            ],
        ),
        (
            "7",
            "Expenses",
            [
                "The Company shall reimburse reasonable business expenses on submission of receipts "
                "within thirty (30) days of the expense.",
            ],
        ),
    ],
    [
        (
            "8",
            "Working Hours and Leave",
            [
                "Normal working hours are 40 hours per week. The Employee is entitled to 24 days of "
                "paid leave per year.",
            ],
        ),
        (
            "9",
            "Confidentiality",
            [
                "The Employee shall keep all Confidential Information strictly confidential during "
                "employment and for three (3) years after it ends, and shall not disclose it to any "
                "third party.",
            ],
        ),
    ],
    [
        (
            "10",
            "Intellectual Property",
            [
                "All work product created by the Employee in the course of employment belongs to the "
                "Company.",
            ],
        ),
        (
            "11",
            "Non-Solicitation",
            [
                "For twelve (12) months after employment ends, the Employee shall not solicit any "
                "Company client with whom the Employee worked.",
            ],
        ),
    ],
    [
        (
            "12",
            "Termination",
            [
                "Either party may terminate this Agreement by providing ninety (90) days written "
                "notice to the other party.",
                "The Company may instead pay the Employee salary in lieu of the notice period.",
                "The Company may terminate this Agreement immediately for gross misconduct.",
            ],
        ),
    ],
    [
        (
            "13",
            "Early Exit Penalty",
            [
                "If the Employee leaves without serving the full notice period, the Employee shall "
                "pay the Company an amount equal to the salary for the unserved part of the notice "
                "period, which may be deducted from the final settlement.",
                "A penalty of INR 50,000 applies if the Employee leaves within the first twelve (12) "
                "months, to recover training costs.",
            ],
        ),
    ],
    [
        (
            "14",
            "Renewal",
            [
                "This Agreement shall renew automatically for further periods of one (1) year unless "
                "either party gives written notice of non-renewal at least sixty (60) days before the "
                "end of the current term.",
            ],
        ),
        (
            "15",
            "Limitation of Liability",
            [
                "Neither party shall be liable for indirect or consequential damages arising out of "
                "this Agreement.",
            ],
        ),
    ],
    [
        (
            "16",
            "Governing Law and Disputes",
            [
                "This Agreement is governed by the laws of India. Any dispute shall first be referred "
                "to mediation, and if unresolved within thirty (30) days, to arbitration in Bengaluru.",
            ],
        ),
        (
            "17",
            "Entire Agreement",
            [
                "This Agreement is the entire agreement between the parties about its subject matter.",
                "Signed by the Company and the Employee on January 15, 2026.",
            ],
        ),
    ],
]


def build_employment_agreement(path: Path) -> None:
    pdf = FPDF(format="A4")
    pdf.set_margins(22, 22, 22)
    pdf.set_auto_page_break(auto=False)
    for page_index, clauses in enumerate(PAGES):
        pdf.add_page()
        if page_index == 0:
            pdf.set_font("Helvetica", "B", 16)
            pdf.multi_cell(0, 10, TITLE, align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 6, INTRO, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)
        for number, heading, paragraphs in clauses:
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 8, f"{number}. {heading}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 11)
            for i, paragraph in enumerate(paragraphs, start=1):
                pdf.multi_cell(0, 6, f"{number}.{i} {paragraph}", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)
            pdf.ln(3)
        pdf.set_y(-18)
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, f"Page {page_index + 1} of {len(PAGES)}", align="C")
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))


def build_all_samples() -> dict[str, Path]:
    from scripts.sample_government_docs import (
        PUBLIC_NOTICE,
        RENTAL_WITH_MISTAKES,
        TENANCY_RULES,
        build_document,
    )

    paths = {
        "employment": OUTPUT_DIR / "employment_agreement.pdf",
        "public_notice": OUTPUT_DIR / "government_public_notice.pdf",
        "tenancy_rules": OUTPUT_DIR / "tenancy_rules.pdf",
        "rental_with_mistakes": OUTPUT_DIR / "rental_agreement_with_mistakes.pdf",
    }
    build_employment_agreement(paths["employment"])
    build_document(paths["public_notice"], PUBLIC_NOTICE)
    build_document(paths["tenancy_rules"], TENANCY_RULES)
    build_document(paths["rental_with_mistakes"], RENTAL_WITH_MISTAKES)
    return paths


if __name__ == "__main__":
    for written in build_all_samples().values():
        print(f"Wrote {written}")
