from difflib import SequenceMatcher


class Metrics:
    @staticmethod
    def answer_similarity(
        expected: str,
        actual: str,
    ) -> float:
        return SequenceMatcher(
            None,
            expected.lower(),
            actual.lower(),
        ).ratio()