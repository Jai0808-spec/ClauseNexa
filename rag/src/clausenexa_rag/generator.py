import torch

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM
)


# ============================================================
# MODEL CONFIGURATION
# ============================================================

GENERATION_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"


# ============================================================
# CUSTOM EXCEPTION
# ============================================================

class GenerationError(Exception):
    """Raised when answer generation fails."""
    pass


# ============================================================
# DEVICE
# ============================================================

DEVICE = (
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)


# ============================================================
# LOAD TOKENIZER + MODEL
# ============================================================

try:

    tokenizer = AutoTokenizer.from_pretrained(
        GENERATION_MODEL
    )

    model = AutoModelForCausalLM.from_pretrained(
        GENERATION_MODEL,
        torch_dtype="auto"
    )

    model = model.to(DEVICE)

except Exception as exc:

    raise GenerationError(
        f"Could not load generation model: {exc}"
    ) from exc


# ============================================================
# GENERATE ANSWER
# ============================================================

def generate_answer(
    question: str,
    context: str
) -> str:

    if not question or not question.strip():
        raise GenerationError(
            "Question cannot be empty."
        )

    if not context or not context.strip():
        return (
            "I could not find enough information "
            "in the contract to answer this question."
        )


    system_prompt = """
You are ClauseNexa, a contract analysis assistant.

Answer the user's question using ONLY the contract
context provided to you.

Rules:
1. Do not use outside knowledge.
2. Do not invent contract terms.
3. If the answer is not present in the context,
   say that the contract does not provide enough
   information.
4. Keep the answer clear and concise.
5. Mention relevant clause numbers when available.
"""


    user_prompt = f"""
CONTRACT CONTEXT:

{context}

QUESTION:

{question}
"""


    messages = [
        {
            "role": "system",
            "content": system_prompt.strip()
        },
        {
            "role": "user",
            "content": user_prompt.strip()
        }
    ]


    try:

        formatted_prompt = (
            tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
        )


        inputs = tokenizer(
            formatted_prompt,
            return_tensors="pt"
        ).to(DEVICE)


        with torch.no_grad():

            outputs = model.generate(
                **inputs,
                max_new_tokens=250,
                do_sample=False
            )


        generated_tokens = outputs[
            0,
            inputs["input_ids"].shape[1]:
        ]


        answer = tokenizer.decode(
            generated_tokens,
            skip_special_tokens=True
        )


        return answer.strip()


    except Exception as exc:

        raise GenerationError(
            f"Answer generation failed: {exc}"
        ) from exc