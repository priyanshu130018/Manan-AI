from app.schemas.base import BaseSchema


class EvaluationSample(BaseSchema):
    question: str
    expected_answer: str