from app.ai.pipelines.factory import PipelineFactory
from app.schemas.chat import ChatData
from app.schemas.chat import ChatRequest
from app.schemas.chat import ChatResponse
from app.services.base_service import BaseService


class ChatService(BaseService):
    def __init__(
        self,
    ) -> None:
        super().__init__()

        self._pipeline = (
            PipelineFactory.get_query_pipeline()
        )

    async def process(
        self,
        request: ChatRequest,
    ) -> ChatResponse:
        response, citations = (
            await self._pipeline.run(
                session_id=request.session_id,
                question=request.message,
            )
        )

        return ChatResponse(
            success=True,
            message="Response generated successfully.",
            data=ChatData(
                response=response,
                citations=citations,
            ),
        )


chat_service = ChatService()