"""Evaluation on real Indian statutes downloaded from India Code (scripts/fetch_indiacode.py).

Every question is phrased the way a citizen would ask it, not copied from the section heading.
The expected section was checked by hand against the downloaded text.

Split, to keep the reported numbers honest:
- "dev" Acts were used while improving retrieval (their failures were looked at);
- "test" Acts were held out — only their final scores were looked at.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

DATASET = Path(__file__).resolve().parents[2] / "dataset" / "indiacode"

Split = Literal["dev", "test"]

ACTS: dict[str, Split] = {
    "consumer_protection_act_2019": "dev",
    "right_to_information_act_2005": "dev",
    "indian_contract_act_1872": "dev",
    "real_estate_regulation_and_development_act_2016": "dev",
    "sexual_harassment_of_women_at_workplace_prevention_prohibiti": "test",
    "protection_of_women_from_domestic_violence_act_2005": "test",
    "legal_services_authorities_act_1987": "test",
    "code_on_wages_2019": "test",
}


@dataclass(frozen=True)
class Question:
    act: str
    question: str
    section: str  # the section that answers it
    page: int  # page where that section starts

    @property
    def split(self) -> Split:
        return ACTS[self.act]


@dataclass(frozen=True)
class Unanswerable:
    act: str
    question: str

    @property
    def split(self) -> Split:
        return ACTS[self.act]


CPA, RTI, ICA, RERA = (
    "consumer_protection_act_2019",
    "right_to_information_act_2005",
    "indian_contract_act_1872",
    "real_estate_regulation_and_development_act_2016",
)
POSH, DV, LSA, WAGES = (
    "sexual_harassment_of_women_at_workplace_prevention_prohibiti",
    "protection_of_women_from_domestic_violence_act_2005",
    "legal_services_authorities_act_1987",
    "code_on_wages_2019",
)

QUESTIONS = [
    # ---- dev
    Question(CPA, "How many days do I have to appeal against the District Commission's order?", "41", 25),
    Question(CPA, "What is the time limit for filing a consumer complaint?", "69", 30),
    Question(CPA, "Up to what value of goods can the District Commission hear a complaint?", "34", 20),
    Question(CPA, "What happens if someone does not obey the Commission's order?", "72", 31),
    Question(CPA, "How do I file a consumer complaint?", "35", 21),
    Question(CPA, "Can I appeal a State Commission order to the National Commission?", "51", 27),
    Question(RTI, "How do I ask a government office for information?", "6", 9),
    Question(RTI, "How many days does the officer have to reply to my request?", "7", 9),
    Question(RTI, "What information can the government refuse to give?", "8", 10),
    Question(RTI, "What can I do if I don't get a reply to my RTI?", "19", 17),
    Question(RTI, "What fine is imposed on an officer who refuses information?", "20", 18),
    Question(ICA, "Who can legally enter into a contract?", "11", 13),
    Question(ICA, "Is a non-compete agreement that stops me from working valid?", "27", 18),
    Question(ICA, "What compensation can I claim if the other party breaks the contract?", "73", 29),
    Question(ICA, "What if the contract names a penalty amount for breach?", "74", 31),
    Question(ICA, "When is an agreement a valid contract?", "10", 13),
    Question(RERA, "Does a builder need to register the project before selling flats?", "3", 11),
    Question(RERA, "Will I get my money back if the builder delays possession?", "18", 19),
    Question(RERA, "How much advance can a builder take before signing the sale agreement?", "13", 17),
    Question(RERA, "Where can I complain against a builder?", "31", 23),
    Question(RERA, "What is the penalty if a project is not registered?", "59", 31),
    Question(RERA, "How long do I have to appeal to the Appellate Tribunal?", "44", 27),
    # ---- test (held out)
    Question(POSH, "Which committee must every employer set up?", "4", 7),
    Question(POSH, "How long do I have to file a sexual harassment complaint?", "9", 10),
    Question(POSH, "Within how many days must the inquiry be finished?", "11", 10),
    Question(POSH, "What is the penalty for an employer who does not form the committee?", "26", 15),
    Question(POSH, "Can I appeal against the committee's recommendations?", "18", 13),
    Question(POSH, "What happens after the inquiry is completed?", "13", 11),
    Question(DV, "What counts as domestic violence?", "3", 4),
    Question(DV, "How can a woman apply to the Magistrate for help?", "12", 7),
    Question(DV, "What does a protection order do?", "18", 8),
    Question(DV, "Can the Magistrate order the husband to pay money?", "20", 9),
    Question(DV, "What is the punishment for breaking a protection order?", "31", 11),
    Question(DV, "What does a Protection Officer do?", "9", 6),
    Question(LSA, "Who is eligible for free legal aid?", "12", 9),
    Question(LSA, "Who organises Lok Adalats?", "19", 11),
    Question(LSA, "Is a Lok Adalat decision final?", "21", 13),
    Question(LSA, "What powers does a Lok Adalat have?", "22", 13),
    Question(WAGES, "When must my employer pay my salary?", "17", 12),
    Question(WAGES, "Can my employer pay me less than the minimum wage?", "5", 9),
    Question(WAGES, "What deductions can be made from my wages?", "18", 12),
    Question(WAGES, "Can women be paid less than men for the same work?", "3", 8),
    Question(WAGES, "Who is eligible for bonus?", "26", 15),
    Question(WAGES, "What is the penalty for paying less than the due wages?", "54", 25),
]  # fmt: skip

# Nothing in these Acts answers these; a trustworthy system must say so instead of guessing.
UNANSWERABLE = [
    Unanswerable(CPA, "What is the penalty for drunk driving?"),
    Unanswerable(RTI, "What is the income tax rate for salaried people?"),
    Unanswerable(ICA, "What is the fee for renewing a passport?"),
    Unanswerable(RERA, "What is the speed limit on national highways?"),
    Unanswerable(POSH, "What is the GST rate on restaurant food?"),
    Unanswerable(DV, "How do I register a trademark?"),
    Unanswerable(LSA, "How many days of maternity leave can I take?"),
    Unanswerable(WAGES, "What is the punishment for cybercrime?"),
]
