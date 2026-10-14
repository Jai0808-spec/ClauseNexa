"""
Generates the fictional evaluation contracts (DOCX) used by run_eval.py.

All parties, amounts and dates are invented. Each document is plain numbered
clauses, like the sample contract, so it goes through the normal
upload -> extract -> chunk -> embed pipeline.

    python tests/eval/make_contracts.py
"""

from pathlib import Path

from docx import Document

OUT = Path(__file__).parent / "contracts"

CONTRACTS = {
    "eval_nda.docx": (
        "MUTUAL NON-DISCLOSURE AGREEMENT",
        """This Mutual Non-Disclosure Agreement is made on 12 January 2026 between Harbour Analytics Pty Ltd ("Harbour") and Beacon Retail Pty Ltd ("Beacon"). This is a fictional document for software testing only.

1. DEFINITIONS

1.1 "Confidential Information" means all non-public information disclosed by a Party to the other Party, in any form, that is marked confidential or would reasonably be understood to be confidential, including pricing, customer lists, source code and business plans.

1.2 "Purpose" means evaluating a possible data analytics partnership between the Parties.

2. OBLIGATIONS OF THE RECEIVING PARTY

2.1 The Receiving Party must keep the Disclosing Party's Confidential Information secret and use it only for the Purpose.

2.2 The Receiving Party must protect Confidential Information with at least the same degree of care it uses for its own confidential information, and never less than reasonable care.

2.3 The Receiving Party may share Confidential Information only with employees and advisers who need to know it and who are bound by written confidentiality duties.

3. EXCLUSIONS

3.1 The obligations in this Agreement do not apply to information that is or becomes public without breach by the Receiving Party, was already known to the Receiving Party before disclosure, is independently developed without use of Confidential Information, or is lawfully received from a third party without restriction.

4. TERM AND SURVIVAL

4.1 This Agreement lasts for two years from the date above unless ended earlier by either Party on 30 days' written notice.

4.2 The confidentiality obligations survive for five years after the date each item of Confidential Information is disclosed, even if this Agreement has ended.

5. RETURN AND DESTRUCTION

5.1 Within 14 days of a written request, the Receiving Party must return or permanently delete all Confidential Information and confirm in writing that it has done so.

5.2 The Receiving Party may keep one archival copy where required by law or its automatic backup systems, and that copy remains subject to this Agreement.

6. COMPELLED DISCLOSURE

6.1 If the Receiving Party is legally required to disclose Confidential Information, it must give the Disclosing Party prompt written notice where lawful, and disclose only the minimum information required.

7. NO LICENCE AND NO WARRANTY

7.1 No licence or ownership right in any Confidential Information is granted by this Agreement.

7.2 Confidential Information is provided "as is" and neither Party gives any warranty about its accuracy or completeness.

8. REMEDIES

8.1 The Parties agree that damages may not be an adequate remedy for breach of this Agreement and that the Disclosing Party may seek an injunction or specific performance without proving actual loss.

8.2 Each Party's total liability under this Agreement is limited to AUD 250,000, except for deliberate misuse of Confidential Information.

9. GENERAL

9.1 This Agreement is governed by the laws of Victoria, Australia, and the Parties submit to the non-exclusive jurisdiction of the courts of Victoria.

9.2 Neither Party may assign its rights under this Agreement without the other Party's prior written consent.

9.3 This Agreement is the entire agreement between the Parties about its subject matter and can be changed only in writing signed by both Parties.

9.4 A notice must be in writing and sent by email to the address most recently notified by the other Party, and is taken to be received on the next business day after it is sent.
""",
    ),
    "eval_employment.docx": (
        "EMPLOYMENT AGREEMENT",
        """This Employment Agreement is made on 20 February 2026 between Northwind Logistics Pty Ltd ("the Employer") and Dana Whitfield ("the Employee"). This is a fictional document for software testing only.

1. POSITION AND START DATE

1.1 The Employee is employed as Operations Analyst, reporting to the Head of Operations.

1.2 Employment starts on 3 March 2026 and the usual place of work is the Employer's office in Parramatta, New South Wales.

2. HOURS OF WORK

2.1 The Employee's ordinary hours are 38 hours per week, Monday to Friday, with reasonable additional hours as required.

3. REMUNERATION

3.1 The Employer will pay a base salary of AUD 95,000 per year, paid fortnightly, plus superannuation at the rate required by law.

3.2 The Employee may be paid a discretionary annual bonus of up to 10% of base salary, based on performance. The Employer is not obliged to pay a bonus.

3.3 The Employer will reimburse reasonable work-related expenses approved in advance by the Head of Operations.

4. PROBATION

4.1 The first six months of employment are a probation period, during which either party may end the employment by giving one week's written notice.

5. LEAVE

5.1 The Employee is entitled to 20 days of paid annual leave each year, accruing progressively.

5.2 The Employee is entitled to 10 days of paid personal and carer's leave each year, and to other leave under the National Employment Standards.

6. CONFIDENTIALITY

6.1 The Employee must not use or disclose the Employer's confidential information except as needed for their duties, during employment and after it ends.

7. INTELLECTUAL PROPERTY

7.1 All intellectual property created by the Employee in the course of employment belongs to the Employer, and the Employee assigns those rights to the Employer.

8. RESTRAINT OF TRADE

8.1 For 12 months after employment ends, the Employee must not work for a direct competitor of the Employer within 50 kilometres of the Parramatta office.

8.2 The Employee acknowledges that this restraint is reasonable to protect the Employer's customer relationships.

9. TERMINATION

9.1 After probation, either party may end the employment by giving four weeks' written notice.

9.2 The Employer may end the employment immediately without notice in cases of serious misconduct, including theft, fraud or serious breach of safety rules.

9.3 On termination the Employee must return all property of the Employer, including laptops, access cards and documents.

10. GENERAL

10.1 This Agreement is governed by the laws of New South Wales, Australia.

10.2 This Agreement is the entire agreement between the parties and can be varied only in writing signed by both parties.
""",
    ),
    "eval_lease.docx": (
        "RESIDENTIAL LEASE AGREEMENT",
        """This Residential Lease Agreement is made on 15 October 2026 between Marlowe Property Holdings Pty Ltd ("the Landlord") and Priya Raman ("the Tenant"). This is a fictional document for software testing only.

1. PREMISES AND TERM

1.1 The Landlord leases Unit 12, 45 Harbour Street, Pyrmont NSW to the Tenant for use as a private residence.

1.2 The lease runs for a fixed term of 12 months, starting on 1 November 2026.

2. RENT

2.1 The rent is AUD 650 per week, payable fortnightly in advance by direct debit into the account nominated by the Landlord.

2.2 The Landlord may increase the rent no more than once in any 12-month period and must give the Tenant at least 60 days' written notice of the increase.

3. BOND

3.1 The Tenant must pay a rental bond of AUD 2,600, equal to four weeks' rent, which the Landlord must lodge with the NSW rental bond authority.

4. UTILITIES AND OUTGOINGS

4.1 The Tenant must pay for electricity, gas, internet and water usage charges in the Tenant's own name or as invoiced.

4.2 The Landlord pays council rates and strata levies.

5. USE OF THE PREMISES

5.1 The Tenant must not keep any pet at the premises without the Landlord's prior written consent, which must not be unreasonably withheld.

5.2 Smoking is not permitted inside the premises.

5.3 The Tenant must not sublet or transfer the lease without the Landlord's written consent.

6. ENTRY AND INSPECTIONS

6.1 The Landlord may enter the premises for a routine inspection after giving the Tenant at least seven days' written notice, and no more than four times in any 12-month period.

6.2 In an emergency the Landlord may enter the premises without notice.

7. REPAIRS AND MAINTENANCE

7.1 The Tenant must keep the premises reasonably clean and tell the Landlord promptly about any damage or required repairs.

7.2 The Landlord must arrange urgent repairs, such as a burst water pipe or a gas leak, within 24 hours of being told.

8. ENDING THE LEASE EARLY

8.1 If the Tenant ends the lease before the fixed term expires, the Tenant must pay a re-letting fee equal to two weeks' rent plus rent until a new tenant takes over, up to a maximum of four weeks.

9. RENEWAL

9.1 The Tenant may ask for a further 12-month term by giving the Landlord written notice at least 90 days before the lease ends, and the rent for the new term will be the then market rent.

10. END OF LEASE

10.1 At the end of the lease the Tenant must return the premises in a reasonably clean condition, fair wear and tear excepted, and return all keys.

11. GENERAL

11.1 This lease is governed by the laws of New South Wales, Australia.
""",
    ),
}


def build() -> None:
    OUT.mkdir(exist_ok=True)

    for name, (title, body) in CONTRACTS.items():
        doc = Document()
        doc.add_heading(title, level=1)

        for block in body.strip().split("\n\n"):
            doc.add_paragraph(block.strip())

        doc.save(OUT / name)
        print("wrote", OUT / name)


if __name__ == "__main__":
    build()
