import re

from clausenexa_rag.retriever import (
    retrieve_contract_sections
)

from clausenexa_rag.generator import (
    generate_answer
)


# Below this hybrid score (cosine similarity + keyword overlap) nothing in
# the contract is related to the question, so the language model is not
# called at all. Raw similarity alone is not enough: short questions such as
# "Are pets allowed?" score only ~0.09 but match the clause by keyword.
MIN_RELEVANCE = 0.2


def strip_ungrounded_clause_refs(answer: str, context: str) -> str:
    """
    Remove "Clause 7.4"-style references whose number does not appear in
    the retrieved context. The small generator model sometimes miscopies
    clause numbers; a wrong citation is worse than none.
    """

    def replace(match):
        number = match.group("number")

        if re.search(rf"(?<![\d.]){re.escape(number)}(?![\d])", context):
            return match.group(0)

        return ""

    cleaned = re.sub(
        r"(?:(?:According to|Under|As per|Per|See|In)\s+)?"
        r"Clauses?\s+(?P<number>\d+(?:\.\d+)*)\s*[,:]?\s*",
        replace,
        answer
    )

    # Re-capitalise if the removed phrase started the answer or a sentence
    return re.sub(
        r"(^|[.!?]\s+|\n)([a-z])",
        lambda m: m.group(1) + m.group(2).upper(),
        cleaned
    ).strip()


def ask_contract(
    supabase,
    contract_id: str,
    question: str,
    top_k: int = 5
) -> dict:

    # --------------------------------------------------------
    # STEP 1: RETRIEVE RELEVANT CHUNKS
    # --------------------------------------------------------

    sections = retrieve_contract_sections(
        supabase=supabase,
        contract_id=contract_id,
        question=question,
        top_k=top_k
    )


    best_relevance = max(
        (
            section.get("hybrid_score", section.get("similarity")) or 0.0
            for section in sections
        ),
        default=0.0
    )


    if not sections or best_relevance < MIN_RELEVANCE:

        return {
            "answer": (
                "I could not find relevant information "
                "in this contract."
            ),
            "sources": []
        }


    # --------------------------------------------------------
    # STEP 2: BUILD CONTEXT
    # --------------------------------------------------------

    context_parts = []


    for section in sections:

        chunk_index = section.get(
            "chunk_index"
        )

        section_title = section.get(
            "section_title"
        )

        section_text = section.get(
            "section_text",
            ""
        )


        header = f"Chunk {chunk_index}"


        if section_title:

            header += (
                f" - {section_title}"
            )


        context_parts.append(
            f"{header}\n{section_text}"
        )


    context = "\n\n".join(
        context_parts
    )


    # --------------------------------------------------------
    # STEP 3: GENERATE GROUNDED ANSWER
    # --------------------------------------------------------

    answer = generate_answer(
        question=question,
        context=context
    )


    # --------------------------------------------------------
    # STEP 4: RETURN ANSWER + SOURCES
    # --------------------------------------------------------

    sources = []


    for section in sections:

        sources.append(
            {
                "chunk_index":
                    section.get("chunk_index"),

                "section_title":
                    section.get("section_title"),

                "page_number":
                    section.get("page_number"),

                "similarity":
                    section.get("similarity"),

                "text":
                    section.get("section_text")
            }
        )


    return {
        "answer": strip_ungrounded_clause_refs(answer, context),
        "sources": sources
    }