"""Concept-extraction evaluation cases (invented sentences).

`expected` lists EVERY scored fact the sentence contains (so precision can be measured);
`absent` lists concepts that must not be extracted (traps).
"""

from dataclasses import dataclass, field

# Concepts whose values are fully annotated in every case (precision is measured on these).
SCORED = {
    "notice_period", "probation", "salary", "rent", "deposit", "late_fee", "interest_rate",
    "working_hours", "leave", "job_title", "area", "governing_law", "jurisdiction", "arbitration",
    "cure_period", "reference_number", "effective_date", "contact", "court_name", "case_number",
    "payment", "duration",
}  # fmt: skip


@dataclass(frozen=True)
class ExtractionCase:
    text: str
    expected: frozenset[tuple[str, str]] = field(default_factory=frozenset)
    absent: frozenset[str] = field(default_factory=frozenset)
    keywords: frozenset[str] = field(default_factory=frozenset)  # keyword-only concepts expected
    chunk_index: int = 5  # > early chunks unless a letterhead case


def case(text: str, *expected: tuple[str, str], absent: tuple[str, ...] = (),
         keywords: tuple[str, ...] = (), chunk_index: int = 5) -> ExtractionCase:  # fmt: skip
    return ExtractionCase(
        text, frozenset(expected), frozenset(absent), frozenset(keywords), chunk_index
    )


CASES: list[ExtractionCase] = [
    # --- time
    case(
        "Either party may terminate this Agreement by providing ninety (90) days written notice.",
        ("notice_period", "90 days"),
    ),
    case(
        "During probation, either party may end the employment by giving fourteen (14) days written notice.",
        ("notice_period", "14 days"),
        absent=("probation",),
    ),
    case(
        "The first six (6) months of employment are a probation period.", ("probation", "6 months")
    ),
    case(
        "The probationary period shall be three months from the date of joining.",
        ("probation", "3 months"),
    ),
    case("The term of this Agreement shall be two (2) years.", ("duration", "2 years")),
    case(
        "The defaulting party may cure the breach within thirty (30) days.",
        ("cure_period", "30 days"),
    ),
    case("These rules shall come into force on 1 June 2026.", ("effective_date", "1 June 2026")),
    # --- money
    case(
        "The Company shall pay the Employee a gross salary of INR 1,20,000 per month.",
        ("salary", "INR 1,20,000"),
        absent=("payment",),
    ),
    case(
        "The Tenant shall pay a monthly rent of Rs. 18,000 and a security deposit of Rs. 36,000.",
        ("rent", "Rs. 18,000"),
        ("deposit", "Rs. 36,000"),
        absent=("payment",),
    ),
    case(
        "A late fee of Rs. 100 per day will be charged for delayed payment.",
        ("late_fee", "Rs. 100"),
    ),
    case(
        "Interest at the rate of 18% per annum shall be charged on overdue amounts.",
        ("interest_rate", "18% per annum"),
    ),
    case(
        "Mr. Sharma paid Rs. 5,000 as a token amount.",
        ("payment", "Rs. 5,000"),
        absent=("salary", "rent", "deposit"),
    ),
    # --- employment
    case("Normal working hours are 40 hours per week.", ("working_hours", "40 hours per week")),
    case(
        "Employees must be reachable during core hours of 11:00 to 16:00.",
        ("working_hours", "11:00 to 16:00"),
    ),
    case(
        "The Employee is entitled to 24 days of paid leave per year.",
        ("leave", "24 days of paid leave"),
    ),
    case(
        "We are pleased to appoint you as Senior Data Analyst with effect from 1 February 2026.",
        ("job_title", "Senior Data Analyst"),
        ("effective_date", "1 February 2026"),
    ),
    case(
        "The Employee shall not solicit any client of the Company for twelve (12) months.",
        keywords=("non_solicitation",),
    ),
    case(
        "All work product belongs to the Company and all intellectual property rights vest in the Company.",
        keywords=("intellectual_property",),
    ),
    # --- property, disputes
    case("The flat has a carpet area of 1,200 sq. ft.", ("area", "1,200 sq. ft")),
    case("This Agreement is governed by the laws of India.", ("governing_law", "Laws of India")),
    case(
        "The courts at Mumbai shall have exclusive jurisdiction.",
        ("jurisdiction", "Courts at Mumbai"),
    ),
    case(
        "Disputes shall be referred to arbitration in Bengaluru.",
        ("arbitration", "Arbitration in Bengaluru"),
    ),
    case(
        "Neither party shall be liable for delays caused by force majeure events.",
        keywords=("force_majeure",),
    ),
    # --- letterhead / government / court (first chunks)
    case(
        "No. REV/2026/114 Dated: 10 March 2026", ("reference_number", "REV/2026/114"), chunk_index=0
    ),
    case(
        "IN THE HIGH COURT OF EXAMPLE STATE W.P. No. 1234 of 2026",
        ("court_name", "High Court of Example State"),
        ("case_number", "W.P. No. 1234 of 2026"),
        chunk_index=0,
    ),
    case(
        "For help, contact the Revenue Helpline at 1800-000-0000 or write to help@revenue.example.gov.",
        ("contact", "1800-000-0000"),
        ("contact", "help@revenue.example.gov"),
    ),
    # --- traps: nothing scored should be extracted
    case("The meeting was held in the conference room with 12 attendees."),
    case(
        "Salary slips are issued on the last working day of each month.",
        absent=("salary", "working_hours"),
    ),
    case("The flat is on the 3rd floor of Tower B.", absent=("area",)),
    case(
        "The company was founded in 1998 and has 40 employees.",
        absent=("working_hours", "interest_rate"),
    ),
    case("Please refer to Section 5.2 of the policy for details."),
]
