from app.ai.evaluation.dataset import (
    EvaluationSample,
)
from app.ai.evaluation.evaluator import (
    Evaluator,
)


class Benchmark:
    def __init__(
        self,
    ) -> None:
        self._evaluator = Evaluator()

    async def run(
        self,
        dataset: list[EvaluationSample],
    ) -> list[dict]:
        results = []

        for sample in dataset:
            result = (
                await self._evaluator.evaluate(
                    sample,
                )
            )

            results.append(result)

        return results