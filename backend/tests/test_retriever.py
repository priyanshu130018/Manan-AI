import asyncio

from app.ai.retrieval.retriever import Retriever


async def main() -> None:
    retriever = Retriever()

    result = await retriever.retrieve(
        "What is this document about?"
    )

    print(result)


asyncio.run(main())