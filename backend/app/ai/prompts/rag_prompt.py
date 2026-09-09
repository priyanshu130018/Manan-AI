class RAGPrompt:
    @staticmethod
    def build(
        history: str,
        context: str,
        question: str,
    ) -> str:
        return f"""
You are a helpful AI assistant.

Answer the user's question only using the provided context and the conversation history.

Rules:
- Use the conversation history to resolve references such as "it", "they", or "that".
- Do not invent information.
- If the answer is not present in the context, say:
"I couldn't find that information in the uploaded documents."

Conversation History:
{history}

Context:
{context}

Question:
{question}

Answer:
""".strip()