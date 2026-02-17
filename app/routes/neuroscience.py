from fastapi import APIRouter, HTTPException
from ..models.neuroscience import (
    NeuroscienceQuestionnaireResponse,
    NeuroscienceAnswersSubmission,
    NeuroscienceAssessmentResult
)
from ..services.neuroscience_service import NeuroscienceService

router = APIRouter(prefix="/neuroscience", tags=["neuroscience"])


@router.get("/questions", response_model=NeuroscienceQuestionnaireResponse)
async def get_neuroscience_questionnaire():
    """
    Get neuroscience assessment questionnaire
    
    Returns:
        NeuroscienceQuestionnaireResponse: Complete questionnaire with 9 questions
    """
    return NeuroscienceService.get_questionnaire()


@router.post("/submit", response_model=NeuroscienceAssessmentResult)
async def submit_neuroscience_answers(submission: NeuroscienceAnswersSubmission):
    """
    Submit user answers and calculate neural pattern
    
    Args:
        submission: User answers (9 answers, each A, B, C, or D)
    
    Returns:
        NeuroscienceAssessmentResult: Result with dominant and secondary patterns
    
    Raises:
        HTTPException 422: If validation fails
    """
    try:
        result = NeuroscienceService.calculate_assessment(submission.answers)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
