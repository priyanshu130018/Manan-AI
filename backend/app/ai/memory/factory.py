from app.ai.memory.conversation import ConversationMemory



class MemoryFactory:
    _memory: ConversationMemory | None = None

    @classmethod
    def get_memory(
        cls,
    ) -> ConversationMemory:
        if cls._memory is None:
            cls._memory = ConversationMemory()

        return cls._memory