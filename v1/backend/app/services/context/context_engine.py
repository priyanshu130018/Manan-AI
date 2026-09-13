from app.domain.entities.chunk import DocumentChunk
from app.domain.entities.message import MessageEntity
from app.domain.entities.study_state import StudySessionContext
from app.domain.enums.grounding_policy import GroundingPolicy
from app.domain.enums.mode import AppMode
from app.schemas.retrieval import Citation

class ContextEngine:
    @staticmethod
    def build_citations(chunks: list[DocumentChunk]) -> list[Citation]:
        citations: list[Citation] = []
        seen = set()
        for c in chunks:
            key = (c.document_id, c.filename, c.page_number, c.chunk_index)
            if key in seen:
                continue
            seen.add(key)
            citations.append(Citation(
                document_id=c.document_id,
                filename=c.filename,
                page=c.page_number,
                chunk=c.chunk_index,
                text=c.text[:200] + ("..." if len(c.text) > 200 else ""),
                score=c.score,
            ))
        return citations

    @staticmethod
    def format_sources(chunks: list[DocumentChunk]) -> str:
        if not chunks:
            return "No document excerpts available."
        blocks = []
        for idx, c in enumerate(chunks, start=1):
            source_header = f"[Source {idx}]: {c.filename} (Page {c.page_number})"
            if c.heading:
                source_header += f" - {c.heading}"
            blocks.append(f"{source_header}\n{c.text}")
        return "\n\n---\n\n".join(blocks)

    @staticmethod
    def format_history(messages: list[MessageEntity], summary: str = "") -> str:
        parts = []
        if summary.strip():
            parts.append(f"Previous Conversation Summary:\n{summary.strip()}")
        if messages:
            recent = messages[-8:]
            chat_lines = [f"{m.role.capitalize()}: {m.content}" for m in recent]
            parts.append("Recent Messages:\n" + "\n".join(chat_lines))
        return "\n\n".join(parts) if parts else "No previous conversation history."

    @staticmethod
    def build_prompt(
        question: str,
        mode: AppMode,
        grounding_policy: GroundingPolicy,
        chunks: list[DocumentChunk],
        history_text: str,
        study_context: StudySessionContext | None = None,
        intent: str | None = None,
    ) -> str:
        sources_text = ContextEngine.format_sources(chunks)
        
        study_guidelines = ""
        if mode == AppMode.STUDY:
            study_guidelines = f"""
You are in STUDY MODE.
Target Topic: {study_context.current_topic if study_context and study_context.current_topic else 'User Study Material'}
Intent: {intent or 'General Study'}
Provide clear, structured, pedagogically sound explanations with definitions, examples, and breakdown of complex concepts.
Always cite the source document and page number when referencing material.
"""

        if grounding_policy == GroundingPolicy.DOCUMENTS_ONLY:
            instructions = """You are answering strictly from the provided Document Sources below.
If the information is NOT present in the Document Sources, explicitly state:
"I could not find this information in your selected documents."
Do NOT use external knowledge or fabricate facts.
Cite specific document names and page numbers in your answer."""

        elif grounding_policy == GroundingPolicy.DOCUMENTS_PLUS_AI:
            instructions = """Use the provided Document Sources as your primary authority.
You may supplement with general AI explanations or analogies where helpful, but clearly distinguish document facts from general explanations.
Cite document filenames and pages whenever quoting or referencing source points."""

        else:  # GENERAL_AI
            instructions = """You are a versatile, intelligent AI assistant. Provide helpful, accurate, well-reasoned answers.
If documents are attached, draw upon them when relevant."""

        return f"""{instructions}
{study_guidelines}

=== DOCUMENT SOURCES ===
{sources_text}

=== CONVERSATION CONTEXT ===
{history_text}

=== USER QUESTION ===
{question}

Response:"""
