from fastapi import APIRouter, HTTPException
from ..models.psychology import QuestionnaireResponse, AnswersSubmission, AssessmentResult
from ..services.psychology_service import PsychologyService

router = APIRouter(prefix="/psychology", tags=["psychology"])


@router.get("", response_model=QuestionnaireResponse)
async def get_psychology_questionnaire():
    """
    Get psychology assessment questionnaire
    
    Returns:
        QuestionnaireResponse: Complete questionnaire with all questions
    """
    return PsychologyService.get_questionnaire()


@router.post("/submit", response_model=AssessmentResult)
async def submit_psychology_answers(submission: AnswersSubmission):
    """
    Submit user answers and calculate result
    
    Args:
        submission: User answers (7 answers, each between 1 and 3)
    
    Returns:
        AssessmentResult: Final result with level and message
    
    Raises:
        HTTPException: If validation fails
    """
    try:
        result = PsychologyService.calculate_assessment(submission.answers)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
