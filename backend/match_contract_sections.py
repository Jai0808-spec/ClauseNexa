from app.database import supabase
from clausenexa_rag.retriever import retrieve_contract_sections

results = retrieve_contract_sections(
    supabase=supabase,
    contract_id="068b523c-5936-4186-b290-d012760eda4d",
    question="What are the termination conditions?",
    top_k=3
)

for result in results:
    print("Similarity:", result["similarity"])
    print("Chunk:", result["chunk_index"])
    print("Text:", result["section_text"][:300])
    print("-" * 50)