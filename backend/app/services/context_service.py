from app.models.entities.chunk import DocumentChunk
from app.models.entities.message import MessageEntity
from app.models.entities.enums import GroundingPolicy, AppMode
from app.models.schemas.retrieval import Citation


class ContextService:
    @staticmethod
    def build_citations(chunks: list[DocumentChunk]) -> list[Citation]:
        """Construct deduplicated, page-aware citations from retrieved chunks."""
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
    def format_history(messages: list[MessageEntity], summary: str | None = "") -> str:
        parts = []
        if summary and summary.strip():
            parts.append(f"Previous Conversation Summary:\n{summary.strip()}")
        if messages:
            recent = messages[-8:]
            chat_lines = [f"{m.role.capitalize()}: {m.content}" for m in recent]
            parts.append("Recent Messages:\n" + "\n".join(chat_lines))
        return "\n\n".join(parts) if parts else "No previous conversation history."

    @staticmethod
    def build_prompt(
        question: str,
        mode: AppMode | str = AppMode.CHAT,
        grounding_policy: GroundingPolicy | str = GroundingPolicy.GENERAL_AI,
        chunks: list[DocumentChunk] | None = None,
        history_text: str = "",
        study_context: None = None,
        intent: str | None = None,
        long_term_memories: list[str] | list[dict] | None = None,
    ) -> str:
        sources_text = ContextService.format_sources(chunks or [])
        policy_val = grounding_policy.value if isinstance(grounding_policy, GroundingPolicy) else grounding_policy

        memory_section = ""
        if long_term_memories:
            facts = []
            for m in long_term_memories:
                if isinstance(m, dict):
                    facts.append(f"- {m.get('content', '')}")
                elif isinstance(m, str) and m.strip():
                    facts.append(f"- {m.strip()}")
            if facts:
                memory_section = "\n=== USER LONG-TERM MEMORY (PERSISTENT FACTS & PREFERENCES) ===\n" + "\n".join(facts) + "\n"

        if policy_val == "documents_only":
            instructions = """You are answering strictly from the provided Document Sources below.
If the information is NOT present in the Document Sources, explicitly state:
"I could not find this information in your selected documents."
Do NOT use external knowledge or fabricate facts.
Cite specific document names and page numbers in your answer."""

        elif policy_val == "documents_plus_ai":
            instructions = """Use the provided Document Sources as your primary authority.
You may supplement with general AI explanations or analogies where helpful, but clearly distinguish document facts from general explanations.
Cite document filenames and pages whenever quoting or referencing source points."""

        else:  # general_ai
            instructions = """You are a versatile, intelligent AI assistant. Provide helpful, accurate, well-reasoned answers.
If documents are attached, draw upon them when relevant."""

        return f"""{instructions}
{memory_section}
=== DOCUMENT SOURCES ===
{sources_text}

=== CONVERSATION CONTEXT ===
{history_text}

=== USER QUESTION ===
{question}

Response:"""


# Backward compatibility alias
ContextEngine = ContextService
