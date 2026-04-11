from pydantic import BaseModel, Field, field_validator
from typing import List


class Question(BaseModel):
    """Question model for psychology assessment"""
    id: int
    text: str
    options: List[str] = Field(..., min_length=3, max_length=3)


class QuestionnaireResponse(BaseModel):
    """Complete questionnaire response model"""
    title: str
    description: str
    questions: List[Question]


class AnswersSubmission(BaseModel):
    """Answers submission model"""
    answers: List[int] = Field(..., min_length=1)
    
    @field_validator('answers')
    @classmethod
    def validate_answers(cls, v: List[int]) -> List[int]:
        """Validate that all answers are between 1 and 3"""
        for i, answer in enumerate(v, 1):
            if answer < 1 or answer > 3:
                raise ValueError(f'Answer {i} must be between 1 and 3, got: {answer}')
        return v


class AssessmentResult(BaseModel):
    """Assessment result model"""
    score: int
    level: str
    message: str
    supportive_messages: list = []
