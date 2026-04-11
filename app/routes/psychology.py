from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional

from app.database import get_db
from app.auth.models import User
from app.auth.dependencies import get_current_user
from app.models.history import AssessmentHistory

from ..models.psychology import QuestionnaireResponse, AnswersSubmission, AssessmentResult
from ..services.psychology_service import PsychologyService
from ..services.ai_video_service import AIVideoService

router = APIRouter(prefix="/psychology", tags=["psychology"])


@router.get("", response_model=QuestionnaireResponse)
async def get_psychology_questionnaire(db: AsyncSession = Depends(get_db)):
    """
    Get psychology assessment questionnaire
    
    Returns:
        QuestionnaireResponse: Complete questionnaire with all questions
    """
    return await PsychologyService.get_questionnaire_from_db(db)


@router.post("/submit", response_model=AssessmentResult)
async def submit_psychology_answers(
    submission: AnswersSubmission,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
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
        
        # Save to history
        history_entry = AssessmentHistory(
            user_id=current_user.id,
            assessment_type="psychology",
            input_data={"answers": submission.answers},
            result_data=result.model_dump()
        )
        db.add(history_entry)
        await db.commit()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/generate-video", response_model=Dict[str, Any])
async def generate_psychology_video(
    submission: AnswersSubmission,
    name: str = "Friend",
    model: str = "gen4.5",
    neuro_pattern: Optional[str] = None,
    zodiac_sign: Optional[str] = None,
    avatar: str = "",
    include_video: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI video explaining psychology assessment results
    
    Args:
        submission: User answers
        name: User name for personalization
        model: AI model (gpt4o, gpt4, gpt35)
        voice: Voice model (nova, alloy, shimmer)
    
    Returns:
        Dict with assessment and video generation result
    """
    try:
        assessment = PsychologyService.calculate_assessment(submission.answers)
        
        video_data = {
            "name": name,
            "type": "psychology",
            "score": assessment.score,
            "level": assessment.level,
            "message": assessment.message,
            "supportive_messages": assessment.supportive_messages,
            "answers": submission.answers
        }
        
        video_result = await AIVideoService.generate_full_video(
            video_data,
            "videos/psychology",
            neuro_pattern=neuro_pattern,
            zodiac_sign=zodiac_sign,
            avatar=avatar,
            model=model,
            include_video=include_video
        )
        
        # Save to history
        history_entry = AssessmentHistory(
            user_id=current_user.id,
            assessment_type="psychology",
            input_data={"answers": submission.answers, "name": name},
            result_data={"assessment": assessment.model_dump(), "video": video_result},
            video_url=video_result.get("final_video")
        )
        db.add(history_entry)
        await db.commit()
        
        return {
            "assessment": assessment.model_dump(),
            "video": video_result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video generation failed: {str(e)}")
