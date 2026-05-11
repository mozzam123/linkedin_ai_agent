from pydantic import BaseModel


class PostEvaluation(BaseModel):
    score: float
    feedback: str