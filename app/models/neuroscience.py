from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Literal


class NeuroscienceQuestion(BaseModel):
    """Question model for neuroscience assessment"""
    id: int
    text: str
    options: List[str] = Field(..., min_length=4, max_length=4)
    options_text: Dict[str, str]


class NeuroscienceQuestionnaireResponse(BaseModel):
    """Complete questionnaire response model for neuroscience"""
    title: str
    description: str
    questions: List[NeuroscienceQuestion]


class NeuroscienceAnswersSubmission(BaseModel):
    """Answers submission model for neuroscience"""
    answers: List[Literal["A", "B", "C", "D"]] = Field(..., min_length=1)
    
    @field_validator('answers')
    @classmethod
    def validate_answers(cls, v: List[str]) -> List[str]:
        """Validate that all answers are A, B, C, or D"""
        valid_options = {"A", "B", "C", "D"}
        for i, answer in enumerate(v, 1):
            if answer not in valid_options:
                raise ValueError(f'Answer {i} must be A, B, C, or D, got: {answer}')
        return v


class NeuroscienceScores(BaseModel):
    """Neural pattern scores model"""
    A: int = Field(..., description="Fight score")
    B: int = Field(..., description="Flight score")
    C: int = Field(..., description="Freeze score")
    D: int = Field(..., description="Fawn score")


class NeuroscienceAssessmentResult(BaseModel):
    """Neuroscience assessment result model"""
    scores: NeuroscienceScores
    dominant: str
    secondary: str
    strong_secondary: bool = False
    description: str
