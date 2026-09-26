"""Evaluation on real Indian statutes downloaded from India Code (scripts/fetch_indiacode.py).

Every question is phrased the way a citizen would ask it, not copied from the section heading.
The expected section was checked by hand against the downloaded text.

Split, to keep the reported numbers honest:
- "dev" Acts were used while improving retrieval (their failures were looked at);
- "test" Acts were held out — only their final scores were looked at;
- "test2" Acts (added later) are a second held-out set: their questions were written and their
  sections checked against the text before search or answers were ever run on them, and nothing
  was tuned on their results. Their parsing *was* checked first (the sections had to exist), which
  exposed four general parser bugs that were fixed (docs/Evaluation.md). After their results were
  seen, retrieval was improved — so "test2" is no longer held out;
- "test3" Acts are the third held-out set, written after all of the above and before the system
  was run on them; only their final scores were looked at.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

DATASET = Path(__file__).resolve().parents[2] / "dataset" / "indiacode"

Split = Literal["dev", "test", "test2", "test3"]

ACTS: dict[str, Split] = {
    "consumer_protection_act_2019": "dev",
    "right_to_information_act_2005": "dev",
    "indian_contract_act_1872": "dev",
    "real_estate_regulation_and_development_act_2016": "dev",
    "sexual_harassment_of_women_at_workplace_prevention_prohibiti": "test",
    "protection_of_women_from_domestic_violence_act_2005": "test",
    "legal_services_authorities_act_1987": "test",
    "code_on_wages_2019": "test",
    "maintenance_and_welfare_of_parents_and_senior_citizens_act_2": "test2",
    "digital_personal_data_protection_act_2023": "test2",
    "rights_of_persons_with_disabilities_act_2016": "test2",
    "information_technology_act_2000": "test2",
    "negotiable_instruments_act_1881": "test2",
    "limitation_act_1963": "test2",
    "arbitration_and_conciliation_act_1996": "test2",
    "right_of_children_to_free_and_compulsory_education_act_2009": "test3",
    "dowry_prohibition_act_1961": "test3",
    "transfer_of_property_act_1882": "test3",
    "specific_relief_act_1963": "test3",
    "registration_act_1908": "test3",
    "prevention_of_corruption_act_1988": "test3",
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
SENIOR, DPDP, RPWD, IT, NI, LIMIT, ARB = (
    "maintenance_and_welfare_of_parents_and_senior_citizens_act_2",
    "digital_personal_data_protection_act_2023",
    "rights_of_persons_with_disabilities_act_2016",
    "information_technology_act_2000",
    "negotiable_instruments_act_1881",
    "limitation_act_1963",
    "arbitration_and_conciliation_act_1996",
)
RTE, DOWRY, TPA, SRA, REG, PCA = (
    "right_of_children_to_free_and_compulsory_education_act_2009",
    "dowry_prohibition_act_1961",
    "transfer_of_property_act_1882",
    "specific_relief_act_1963",
    "registration_act_1908",
    "prevention_of_corruption_act_1988",
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
    # ---- test2 (second held-out set)
    Question(SENIOR, "Can elderly parents claim maintenance from their children?", "4", 6),
    Question(SENIOR, "Who can apply to the Tribunal for maintenance?", "5", 6),
    Question(SENIOR, "What is the maximum monthly maintenance the Tribunal can order?", "9", 8),
    Question(SENIOR, "How many days do I have to appeal against the Tribunal's order?", "16", 8),
    Question(SENIOR, "Can a parent cancel a gift of property if the child stops looking after them?", "23", 10),
    Question(SENIOR, "What is the punishment for abandoning a senior citizen?", "24", 10),
    Question(DPDP, "When can a company process my personal data?", "4", 7),
    Question(DPDP, "What must a company tell me before asking for my consent?", "5", 7),
    Question(DPDP, "Can I withdraw my consent later?", "6", 8),
    Question(DPDP, "How is the personal data of children protected?", "9", 11),
    Question(DPDP, "Can I ask for my personal data to be erased?", "12", 13),
    Question(DPDP, "How do I complain if my data is misused?", "13", 13),
    Question(RPWD, "Is it illegal to discriminate against disabled people?", "3", 7),
    Question(RPWD, "Do children with disabilities get free education?", "31", 16),
    Question(RPWD, "What share of government jobs is reserved for persons with disabilities?", "34", 16),
    Question(RPWD, "How do I get a disability certificate?", "58", 21),
    Question(IT, "Are electronic records legally valid?", "4", 11),
    Question(IT, "Is an electronic signature legally recognised?", "5", 11),
    Question(IT, "What is the punishment for hacking a computer?", "66", 26),
    Question(IT, "What is the punishment for identity theft online?", "66C", 26),
    Question(IT, "What is the punishment for cheating someone by pretending to be another person online?", "66D", 26),
    Question(IT, "Is sharing obscene material online a crime?", "67", 27),
    Question(NI, "What is a promissory note?", "4", 8),
    Question(NI, "What is a cheque?", "6", 9),
    Question(NI, "What happens if my cheque bounces because of insufficient funds?", "138", 28),
    Question(NI, "Which court can hear a cheque bounce case?", "142", 29),
    Question(LIMIT, "Can I file a case after the limitation period is over?", "3", 4),
    Question(LIMIT, "Can the court accept an appeal filed after the deadline?", "5", 4),
    Question(LIMIT, "Does the time limit run while I am a minor?", "6", 4),
    Question(LIMIT, "Does admitting a debt in writing extend the limitation period?", "18", 8),
    Question(ARB, "Does an arbitration agreement have to be in writing?", "7", 9),
    Question(ARB, "Can a court send a dispute to arbitration if there is an arbitration agreement?", "8", 10),
    Question(ARB, "How are arbitrators appointed?", "11", 12),
    Question(ARB, "Within what time must the arbitral award be made?", "29A", 19),
    Question(ARB, "How can I challenge an arbitral award?", "34", 23),
    # ---- test3 (third held-out set)
    Question(RTE, "Is education free for children aged six to fourteen?", "3", 6),
    Question(RTE, "What share of seats must private schools keep for children from poor families?", "12", 9),
    Question(RTE, "Can a school charge a capitation fee or hold a screening test for admission?", "13", 10),
    Question(RTE, "Can a child be held back or expelled before finishing elementary education?", "16", 10),
    Question(RTE, "Can a teacher physically punish a child?", "17", 11),
    Question(DOWRY, "What counts as dowry?", "2", 2),
    Question(DOWRY, "What is the punishment for giving or taking dowry?", "3", 3),
    Question(DOWRY, "What is the penalty for demanding dowry?", "4", 3),
    Question(DOWRY, "Is an agreement to give dowry valid?", "5", 4),
    Question(TPA, "What is a sale of immovable property?", "54", 20),
    Question(TPA, "What is a mortgage?", "58", 23),
    Question(TPA, "What is a lease?", "105", 37),
    Question(TPA, "How does a lease come to an end?", "111", 40),
    Question(TPA, "What is a gift of property?", "122", 43),
    Question(SRA, "How can I get back possession of property I was thrown out of?", "6", 4),
    Question(SRA, "Can the court make the other party actually perform the contract?", "10", 5),
    Question(SRA, "When can a contract be cancelled by the court?", "27", 12),
    Question(SRA, "When can the court grant a permanent injunction?", "38", 14),
    Question(REG, "Which documents must be registered compulsorily?", "17", 9),
    Question(REG, "Within how many months must a document be presented for registration?", "23", 17),
    Question(REG, "Where should a document about land be registered?", "28", 18),
    Question(REG, "What happens if a document that must be registered is not registered?", "49", 27),
    Question(PCA, "What is the punishment for a public servant who takes a bribe?", "7", 8),
    Question(PCA, "Is giving a bribe to a public servant an offence?", "8", 9),
    Question(PCA, "What counts as criminal misconduct by a public servant?", "13", 11),
    Question(PCA, "Is sanction needed to prosecute a public servant?", "19", 15),
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
    Unanswerable(SENIOR, "How do I apply for a passport?"),
    Unanswerable(DPDP, "What is the minimum wage for construction workers?"),
    Unanswerable(RPWD, "What is the stamp duty on buying a flat?"),
    Unanswerable(IT, "How many days of maternity leave can I take?"),
    Unanswerable(NI, "What is the punishment for drunk driving?"),
    Unanswerable(LIMIT, "How do I register a trademark?"),
    Unanswerable(ARB, "What is the income tax rate for senior citizens?"),
    Unanswerable(RTE, "What is the punishment for drunk driving?"),
    Unanswerable(DOWRY, "How do I register a company?"),
    Unanswerable(TPA, "What is the minimum wage for factory workers?"),
    Unanswerable(SRA, "How many days of maternity leave can I take?"),
    Unanswerable(REG, "What is the punishment for cybercrime?"),
    Unanswerable(PCA, "What is the GST rate on gold jewellery?"),
]
