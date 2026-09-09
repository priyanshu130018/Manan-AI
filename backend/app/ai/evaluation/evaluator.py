from app.ai.pipelines.factory import PipelineFactory
from app.ai.evaluation.metrics import Metrics
from app.ai.evaluation.dataset import EvaluationSample


class Evaluator:
    def __init__(
        self,
    ) -> None:
        self._pipeline = (
            PipelineFactory.get_query_pipeline()
        )

    async def evaluate(
        self,
        sample: EvaluationSample,
    ) -> dict:
        answer, citations = (
            await self._pipeline.run(
                session_id="evaluation",
                question=sample.question,
            )
        )

        score = Metrics.answer_similarity(
            sample.expected_answer,
            answer,
        )

        return {
            "question": sample.question,
            "expected": sample.expected_answer,
            "answer": answer,
            "score": score,
            "citations": citations,
        }