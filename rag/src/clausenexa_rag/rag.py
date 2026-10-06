from clausenexa_rag.retriever import (
    retrieve_contract_sections
)

from clausenexa_rag.generator import (
    generate_answer
)


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


    if not sections:

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
                    section.get("similarity")
            }
        )


    return {
        "answer": answer,
        "sources": sources
    }